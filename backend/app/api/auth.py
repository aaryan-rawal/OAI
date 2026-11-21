from datetime import datetime, timedelta, timezone
import hashlib, logging, secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models import User, RegistrationOTP, Organization, InPortalNotification
from app.schemas import RegisterStartIn, RegisterVerifyIn, LoginIn
from app.authentication.security import hash_password, verify_password, create_access_token
from app.authentication.dependencies import current_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger("optifreight.auth.otp")

def user_payload(user: User) -> dict:
    return {"id": user.id, "email": user.email, "phone": user.phone, "phone_verified": user.phone_verified,
            "name": user.name, "role": user.role, "tier": user.tier,
            "organization_id": user.organization_id, "organization_name": user.organization_name}

def session_payload(user: User) -> dict:
    return {"token": create_access_token(user.id), "user": user_payload(user)}

@router.post("/register/start", status_code=202)
async def register_start(payload: RegisterStartIn, db: AsyncSession = Depends(get_db)):
    email = str(payload.email).lower().strip()
    phone = payload.phone
    if await db.scalar(select(User).where(or_(User.email == email, User.phone == phone))):
        raise HTTPException(409, "An account with this email or phone number already exists.")
    # Basic per-phone issuance throttle to limit OTP abuse.
    recent_count = await db.scalar(select(func.count(RegistrationOTP.id)).where(
        RegistrationOTP.phone == phone,
        RegistrationOTP.created_at >= datetime.now(timezone.utc) - timedelta(minutes=15)))
    if (recent_count or 0) >= 3:
        raise HTTPException(429, "Too many verification codes requested. Try again in 15 minutes.")
    # Invalidate earlier active challenges for this phone.
    old = (await db.scalars(select(RegistrationOTP).where(RegistrationOTP.phone == phone, RegistrationOTP.consumed.is_(False)))).all()
    for item in old: item.consumed = True
    otp = f"{secrets.randbelow(1_000_000):06d}"
    challenge = RegistrationOTP(phone=phone, otp_hash=hashlib.sha256(otp.encode()).hexdigest(),
        registration_payload={"name":payload.name.strip(), "email":email, "phone":phone,
          "password_hash":hash_password(payload.password), "account_type":payload.account_type,
          "organization_name":payload.organization_name.strip() if payload.organization_name else None, "organization_id":payload.organization_id},
        expires_at=datetime.now(timezone.utc)+timedelta(minutes=settings.REGISTRATION_OTP_TTL_MINUTES))
    db.add(challenge)
    await db.commit()
    from app.services.integrations.sms import send_sms, configured as sms_configured, SMSNotConfigured
    if sms_configured():
        try:
            await send_sms(phone, f"Your OptiFreight AI registration OTP is {otp}. It expires in {settings.REGISTRATION_OTP_TTL_MINUTES} minutes. Do not share it.")
        except Exception as exc:
            await db.rollback()
            logger.exception("Registration OTP delivery failed")
            raise HTTPException(502, "OTP delivery failed. Check the configured SMS provider and try again.") from exc
        return {"challenge_id":challenge.id, "expires_in_seconds":settings.REGISTRATION_OTP_TTL_MINUTES*60, "delivery":"sms"}
    if settings.APP_ENV.lower() == "production":
        await db.rollback()
        raise HTTPException(503, "Phone OTP delivery is not configured. Set SMS_PROVIDER and the provider credentials in .env.")
    logger.warning("LOCAL DEVELOPMENT OTP for %s: %s", phone, otp)
    return {"challenge_id":challenge.id, "expires_in_seconds":settings.REGISTRATION_OTP_TTL_MINUTES*60,
            "development_otp":otp, "delivery":"development_console"}

@router.post("/register/verify", status_code=201)
async def register_verify(payload: RegisterVerifyIn, db: AsyncSession = Depends(get_db)):
    challenge = await db.get(RegistrationOTP, payload.challenge_id)
    now = datetime.now(timezone.utc)
    if not challenge or challenge.consumed or challenge.expires_at <= now:
        raise HTTPException(400, "OTP challenge is invalid or expired. Start registration again.")
    if challenge.attempts >= settings.REGISTRATION_OTP_MAX_ATTEMPTS:
        challenge.consumed = True; await db.commit()
        raise HTTPException(429, "Too many incorrect OTP attempts. Start registration again.")
    challenge.attempts += 1
    if not secrets.compare_digest(challenge.otp_hash, hashlib.sha256(payload.otp.encode()).hexdigest()):
        await db.commit()
        raise HTTPException(400, "Incorrect OTP.")
    data = challenge.registration_payload
    if await db.scalar(select(User).where(or_(User.email == data["email"], User.phone == challenge.phone))):
        challenge.consumed = True; await db.commit()
        raise HTTPException(409, "An account with this email or phone number already exists.")
    from uuid import uuid4
    organization_id = str(uuid4()) if data["account_type"] == "organization_owner" else data.get("organization_id")
    if data["account_type"] in {"organization_admin", "driver"}:
        org = await db.get(Organization, organization_id)
        if not org or org.status != "active":
            challenge.consumed = True; await db.commit()
            raise HTTPException(403, "The selected company is not approved for operations.")
    user = User(email=data["email"], phone=challenge.phone, phone_verified=True, name=data["name"],
      password_hash=data["password_hash"], role=data["account_type"], organization_id=organization_id,
      organization_name=data["organization_name"])
    db.add(user); challenge.consumed = True
    try:
        await db.flush()
        if data["account_type"] == "organization_owner":
            db.add(Organization(id=organization_id, name=data["organization_name"], owner_user_id=user.id, status="pending_owner_approval"))
            for owner_email in settings.platform_owner_email_list:
                platform_user = await db.scalar(select(User).where(User.email == owner_email))
                if platform_user:
                    db.add(InPortalNotification(recipient_user_id=platform_user.id, organization_id=organization_id, kind="company_registration", title="New company registration", message=f"{data['organization_name']} is awaiting initial approval.", payload={"organization_id":organization_id}))
        result = session_payload(user); await db.commit(); return result
    except IntegrityError as exc:
        await db.rollback(); raise HTTPException(409, "An account with this email or phone number already exists.") from exc

@router.post("/register", status_code=410)
async def legacy_register():
    raise HTTPException(410, "Registration now requires phone OTP. Use /auth/register/start followed by /auth/register/verify.")

@router.post("/login")
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    identifier = payload.identifier.strip()
    # Accept email, verified phone, or exact account name. Name login is disabled if ambiguous.
    if "@" in identifier:
        user = await db.scalar(select(User).where(User.email == identifier.lower()))
    else:
        digits = "".join(ch for ch in identifier if ch.isdigit())
        if len(digits) >= 10:
            normalized = ("+91" + digits) if len(digits) == 10 else ("+" + digits)
            user = await db.scalar(select(User).where(User.phone == normalized, User.phone_verified.is_(True)))
        else:
            matches = (await db.scalars(select(User).where(User.name.ilike(identifier)))).all()
            user = matches[0] if len(matches) == 1 else None
            if len(matches) > 1:
                raise HTTPException(400, "More than one account uses that name. Sign in with your phone number or email instead.")
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, detail="Name, phone number or email and password do not match.")
    if user.phone and not user.phone_verified:
        raise HTTPException(403, "Complete phone verification before signing in.")
    if user.role in {"organization_admin", "driver"} and user.organization_id:
        org = await db.get(Organization, user.organization_id)
        if not org or org.status != "active":
            raise HTTPException(403, "Your company is not currently approved for operations.")
    try: return session_payload(user)
    except RuntimeError as exc: raise HTTPException(503, detail=str(exc)) from exc

@router.get("/me")
async def me(user: User = Depends(current_user)):
    return user_payload(user)

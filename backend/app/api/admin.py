from fastapi import APIRouter, Depends, HTTPException
from app.authentication.dependencies import current_user
from app.models import User
from app.api.auth import user_payload
router=APIRouter(prefix="/admin",tags=["admin"])
@router.get("/profile")
async def admin_profile(user:User=Depends(current_user)):
    if user.role not in {"platform_admin","admin"}: raise HTTPException(403,"Administrator access required.")
    return user_payload(user)

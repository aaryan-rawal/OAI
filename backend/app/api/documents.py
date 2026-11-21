"""Private document upload endpoints for fleet compliance records.

Uploads are private local files. Production deployments should replace local storage with a
private object store, malware scanning and retention controls before public launch.
"""
from __future__ import annotations
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.authentication.dependencies import current_user, organization_owner
from app.config import PROJECT_ROOT, settings
from app.db import get_db
from app.models import FleetContainer, FleetDriver, User, ManualCargo

router = APIRouter(prefix="/documents", tags=["private documents"])
ALLOWED = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_BYTES = settings.MAX_DOCUMENT_UPLOAD_MB * 1024 * 1024

def _storage() -> Path:
    path = (PROJECT_ROOT / settings.DOCUMENT_STORAGE_DIR).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path

async def _save(upload: UploadFile, prefix: str) -> dict:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(415, "Only PDF, JPG, JPEG and PNG files are accepted.")
    content = await upload.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413, f"File must be between 1 byte and {settings.MAX_DOCUMENT_UPLOAD_MB} MB.")
    # Verify actual file signature, not just the filename/MIME supplied by the browser.
    signatures = {".pdf": content.startswith(b"%PDF-"), ".jpg": content.startswith(b"\xff\xd8\xff"),
                  ".jpeg": content.startswith(b"\xff\xd8\xff"), ".png": content.startswith(b"\x89PNG\r\n\x1a\n")}
    if not signatures[suffix]:
        raise HTTPException(415, "File content does not match its extension.")
    key = f"{prefix}_{uuid4().hex}{suffix}"
    target = _storage() / key
    target.write_bytes(content)
    return {"storage_key": key, "original_filename": Path(upload.filename or "document").name,
            "extension": suffix, "size_bytes": len(content), "verification_status": "uploaded_unverified"}

@router.post("/vehicles/{container_id}/{document_type}")
async def upload_vehicle_document(container_id: str, document_type: str, file: UploadFile = File(...),
    user: User = Depends(organization_owner), db: AsyncSession = Depends(get_db)):
    allowed_types = {"rc", "transport_permit", "over_dimensional_permit"}
    if document_type not in allowed_types: raise HTTPException(400, "Unsupported vehicle document type.")
    row = await db.scalar(select(FleetContainer).where(FleetContainer.id == container_id,
        FleetContainer.organization_id == (user.organization_id or user.id)))
    if not row: raise HTTPException(404, "Vehicle not found.")
    meta = await _save(file, f"vehicle_{document_type}")
    docs = dict(row.documents or {}); docs[document_type] = meta; row.documents = docs
    await db.commit()
    return {"document_type": document_type, **meta}

@router.post("/drivers/{driver_id}/{document_type}")
async def upload_driver_document(driver_id: str, document_type: str, file: UploadFile = File(...),
    user: User = Depends(organization_owner), db: AsyncSession = Depends(get_db)):
    if document_type not in {"driving_license", "pan", "aadhaar"}: raise HTTPException(400, "Unsupported driver document type.")
    row = await db.scalar(select(FleetDriver).where(FleetDriver.id == driver_id,
        FleetDriver.organization_id == (user.organization_id or user.id)))
    if not row: raise HTTPException(404, "Driver not found.")
    meta = await _save(file, f"driver_{document_type}")
    result = dict(row.verification_result or {}); docs = dict(result.get("documents", {})); docs[document_type] = meta
    result["documents"] = docs; row.verification_result = result
    if row.verification_status == "not_submitted": row.verification_status = "documents_uploaded_pending_verification"
    await db.commit()
    return {"document_type": document_type, **meta, "verification_status": row.verification_status}


@router.post("/cargo/{cargo_id}/hazardous-safety")
async def upload_hazardous_safety_evidence(cargo_id: str, file: UploadFile = File(...),
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = await db.scalar(select(ManualCargo).where(ManualCargo.id == cargo_id, ManualCargo.owner_id == user.id))
    if not row: raise HTTPException(404, "Cargo listing not found.")
    if not row.hazardous: raise HTTPException(400, "Safety evidence is accepted only for hazardous cargo listings.")
    meta = await _save(file, "hazardous_cargo_safety")
    details = dict(row.hazardous_details or {}); details["vehicle_securement_evidence"] = meta
    details["evidence_status"] = "uploaded_unverified"; row.hazardous_details = details
    await db.commit()
    return meta

@router.post("/ocr/preview")
async def preview_document_ocr(file: UploadFile = File(...), user: User = Depends(organization_owner)):
    """Extract candidate fields locally; never auto-approve identity or licence documents."""
    content = await file.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413, f"File must be between 1 byte and {settings.MAX_DOCUMENT_UPLOAD_MB} MB.")
    from app.services.ocr.engine import extract_document, OCRUnavailable
    try:
        return extract_document(content, file.filename or "document")
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    except OCRUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc

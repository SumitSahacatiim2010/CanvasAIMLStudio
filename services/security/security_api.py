"""Security REST API — endpoints for encryption, PII masking, and audit config."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from services.gateway.app.auth import CurrentUser, Role, get_current_user, require_roles
from services.security.encryption import EncryptionService, HAS_CRYPTO
from services.security.pii import PIIScanner

router = APIRouter(prefix="/api/v1/security", tags=["Security & Compliance"])

_crypto = EncryptionService()
_scanner = PIIScanner()

class EncryptRequest(BaseModel):
    plaintext: str

class DecryptRequest(BaseModel):
    ciphertext: str

class PIIScanRequest(BaseModel):
    text: str
    mask: bool = False

@router.post("/encrypt")
async def encrypt_data(
    req: EncryptRequest,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.DATA_ENGINEER)),
) -> dict[str, str]:
    if not HAS_CRYPTO:
        return {"ciphertext": _crypto.encrypt(req.plaintext), "warning": "Cryptography package missing. Using stub."}
    return {"ciphertext": _crypto.encrypt(req.plaintext)}

@router.post("/decrypt")
async def decrypt_data(
    req: DecryptRequest,
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN)),
) -> dict[str, str]:
    try:
        return {"plaintext": _crypto.decrypt(req.ciphertext)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/pii/scan")
async def scan_pii(
    req: PIIScanRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    findings = _scanner.detect(req.text)
    result: dict[str, Any] = {
        "has_pii": len(findings) > 0,
        "findings": findings,
    }
    if req.mask:
        result["masked_text"] = _scanner.mask(req.text)
    return result

@router.get("/status")
async def security_status(
    user: CurrentUser = Depends(require_roles(Role.PLATFORM_ADMIN, Role.AUDITOR)),
) -> dict[str, Any]:
    return {
        "encryption_engine": "AES-GCM" if HAS_CRYPTO else "STUB",
        "crypto_library_available": HAS_CRYPTO,
        "pii_patterns_loaded": len(_scanner.patterns),
        "audit_logging_active": True,
    }

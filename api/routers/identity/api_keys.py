import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from core.auth import decrypt_secret, encrypt_secret
from core.db.models import User, UserApiKey

router = APIRouter(prefix="/keys", tags=["api-keys"])

ALLOWED_SERVICES = {
    "openai",
    "dataforseo_login", "dataforseo_password",
    "wp_url", "wp_app_password",
    "gsc_credentials", "ga4_credentials",
    "copyscape_user", "copyscape_key",
    "semrush_key",
    "ahrefs_key",
    "moz_access_id", "moz_secret_key",
    # Phase 3 — OAuth tokens (§17)
    "google_refresh_token",   # per-subscriber; covers GSC + GA4 via single Google OAuth flow
}


class StoreKeyRequest(BaseModel):
    value: str


class KeyStatus(BaseModel):
    service: str
    connected: bool


@router.get("", response_model=list[KeyStatus])
def list_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return which services have a stored key. Never returns decrypted values."""
    rows = db.query(UserApiKey).filter(UserApiKey.user_id == current_user.id).all()
    stored = {row.service for row in rows}
    return [KeyStatus(service=svc, connected=svc in stored) for svc in sorted(ALLOWED_SERVICES)]


@router.put("/{service}", status_code=204)
def store_key(
    service: str,
    body: StoreKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Encrypt and store (or replace) a key for the given service."""
    if service not in ALLOWED_SERVICES:
        raise HTTPException(400, f"Unknown service '{service}'. Valid: {sorted(ALLOWED_SERVICES)}")

    if not body.value.strip():
        raise HTTPException(422, "Value must not be empty")

    try:
        _save_key(db, current_user.id, service, body.value.strip())
    except IntegrityError:
        raise HTTPException(500, "Failed to store key — database error")


@router.delete("/{service}", status_code=204)
def delete_key(
    service: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if service not in ALLOWED_SERVICES:
        raise HTTPException(400, f"Unknown service '{service}'")

    deleted = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == current_user.id, UserApiKey.service == service)
        .delete()
    )
    db.commit()

    if not deleted:
        raise HTTPException(404, f"No stored key for service '{service}'")


class TestKeyRequest(BaseModel):
    service: str
    value: str


@router.post("/test", status_code=200)
def test_key(body: TestKeyRequest, _: User = Depends(get_current_user)):
    """Test a key before saving it. Does NOT persist."""
    if body.service == "openai":
        try:
            with httpx.Client(timeout=30) as client:
                r = client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {body.value.strip()}"},
                )
            if r.status_code == 401:
                raise HTTPException(400, "Invalid OpenAI API key — check and try again")
            if r.status_code != 200:
                raise HTTPException(400, f"OpenAI returned {r.status_code}")
        except httpx.RequestError as e:
            raise HTTPException(502, f"Could not reach OpenAI: {e}")

    else:
        raise HTTPException(400, f"No test available for service '{body.service}'")

    return {"ok": True, "service": body.service}


def _save_key(db: Session, user_id: int, service: str, value: str) -> None:
    """Encrypt and upsert a service key. Re-raises IntegrityError on concurrent writes."""
    encrypted = encrypt_secret(value)
    existing = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id, UserApiKey.service == service)
        .first()
    )
    if existing:
        existing.encrypted_value = encrypted
    else:
        db.add(UserApiKey(user_id=user_id, service=service, encrypted_value=encrypted))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise


def get_user_secret(service: str, user_id: int, db: Session) -> str:
    """Internal helper — retrieve and decrypt a key for use in other routers."""
    row = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id, UserApiKey.service == service)
        .first()
    )
    if not row:
        raise HTTPException(
            422,
            f"No {service} key stored. Connect it first at PUT /api/keys/{service}",
        )
    return decrypt_secret(row.encrypted_value)

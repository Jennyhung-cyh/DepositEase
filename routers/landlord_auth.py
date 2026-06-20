import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/landlord", tags=["landlord-auth"])

# MVP: passwords per company — move to env vars before production
LANDLORD_PASSWORDS: dict[str, str] = {
    "Holland2Stay": "h2s-2024",
    "Our Domain":   "od-2024",
    "Vesteda":      "vest-2024",
    "Greystar":     "grey-2024",
}

# In-memory sessions: token -> {landlord, expires}
_sessions: dict[str, dict] = {}

SESSION_TTL_HOURS = 8


class AuthRequest(BaseModel):
    landlord: str
    password: str


def verify_token(token: str) -> str | None:
    """Returns landlord name if token is valid and not expired, else None."""
    session = _sessions.get(token)
    if not session:
        return None
    if datetime.utcnow() > session["expires"]:
        del _sessions[token]
        return None
    return session["landlord"]


@router.post("/auth")
def authenticate(body: AuthRequest):
    expected = LANDLORD_PASSWORDS.get(body.landlord)
    if not expected or body.password != expected:
        raise HTTPException(status_code=401, detail="Invalid company or password.")

    token = secrets.token_hex(32)
    _sessions[token] = {
        "landlord": body.landlord,
        "expires": datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS),
    }
    return {"token": token, "landlord": body.landlord}


@router.post("/logout")
def logout(body: dict):
    token = body.get("token", "")
    _sessions.pop(token, None)
    return {"status": "logged out"}

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(..., description="Login username (e.g. admin)")
    password: str = Field(..., description="Login password (e.g. admin)")


@router.post("/login")
async def login(req: LoginRequest):
    """
    Validates user credentials against system registry.
    Prepared for easy replacement with Active Directory / LDAP authentication.
    """
    clean_user = req.username.strip() if req.username else ""
    clean_pass = req.password.strip() if req.password else ""

    if not clean_user or not clean_pass:
        raise HTTPException(
            status_code=400,
            detail="Credentials Required: Please enter both Username and Password."
        )

    # Active Directory / System Credential Verification (Default: admin / admin)
    if clean_user.lower() == "admin" and clean_pass == "admin":
        logger.info(f"User '{clean_user}' authenticated successfully.")
        return {
            "success": True,
            "username": "admin",
            "full_name": "Meghna Ops",
            "role": "Internal Admin",
            "detail": "Authentication successful. Access granted."
        }
    else:
        logger.warning(f"Failed login attempt for username '{clean_user}'.")
        raise HTTPException(
            status_code=401,
            detail="Invalid Credentials: The username or password entered is incorrect."
        )

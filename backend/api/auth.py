# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Authentication API — passwordless magic link flow.

POST  /auth/request-link     → request a magic login link
POST  /auth/verify            → verify magic link token, return JWT
GET   /auth/me                → get current authenticated user
"""

import uuid
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import resend
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.auth import User, MagicLink

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


# ─── PII Redaction ────────────────────────────────────────────────────────────

def redact_email(email: str) -> str:
    """Redact email for safe logging. e.g. 'spy@seanyoung.biz' → 's**@s***.biz'"""
    if not email or "@" not in email:
        return "[redacted]"
    local, domain = email.split("@", 1)
    domain_parts = domain.rsplit(".", 1)
    redacted_local = local[0] + "**" if local else "**"
    if len(domain_parts) == 2:
        redacted_domain = domain_parts[0][0] + "***." + domain_parts[1]
    else:
        redacted_domain = "***"
    return f"{redacted_local}@{redacted_domain}"


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RequestLinkPayload(BaseModel):
    """Payload to request a magic link."""
    email: EmailStr


class RequestLinkResponse(BaseModel):
    """Response after requesting a magic link."""
    message: str
    # In dev mode, we return the magic link directly so you can click it
    magic_link: str | None = None
    token: str | None = None


class VerifyTokenPayload(BaseModel):
    """Payload to verify a magic link token."""
    token: str


class AuthResponse(BaseModel):
    """Response with JWT access token."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    is_onboarded: bool


class UserResponse(BaseModel):
    """Current user info."""
    id: str
    email: str
    name: str | None
    is_onboarded: bool
    candidate_id: str | None
    created_at: str


# ─── JWT Helpers ─────────────────────────────────────────────────────────────

def create_jwt(user_id: uuid.UUID, email: str) -> str:
    """Create a JWT access token for an authenticated user."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ─── Resend Email ─────────────────────────────────────────────────────────────

async def send_magic_link_email(email: str, magic_link_url: str) -> bool:
    """
    Send magic link email via Resend.

    Returns True if email was sent successfully, False otherwise.
    Falls back gracefully if Resend is not configured.
    """
    if not settings.resend_api_key:
        logger.warning(
            "auth.resend_not_configured",
            email_redacted=redact_email(email),
            message="Resend API key not set, email not sent",
        )
        return False

    resend.api_key = settings.resend_api_key

    try:
        resend.Emails.send({
            "from": settings.resend_from_email,
            "to": email,
            "subject": "Your Talent Agent Login Link",
            "html": f"""
            <div style="font-family: 'DM Sans', -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px; background-color: #0A0A0A; color: #FAFAFA;">
                <h1 style="font-family: 'Playfair Display', Georgia, serif; color: #C9A227; font-size: 28px; margin-bottom: 24px;">
                    Talent Agent
                </h1>
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
                    Click the button below to sign in to your account. This link expires in {settings.magic_link_expiry_minutes} minutes.
                </p>
                <a href="{magic_link_url}" style="display: inline-block; background-color: #C9A227; color: #0A0A0A; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px;">
                    Sign In
                </a>
                <p style="font-size: 14px; color: #737373; margin-top: 32px; line-height: 1.6;">
                    If you didn't request this link, you can safely ignore this email.
                </p>
                <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 32px 0;">
                <p style="font-size: 12px; color: #737373;">
                    VibeSpace LLC · The Dot Connects
                </p>
            </div>
            """,
        })
        logger.info(
            "auth.email_sent",
            email_redacted=redact_email(email),
        )
        return True
    except Exception as e:
        logger.error(
            "auth.email_send_failed",
            email_redacted=redact_email(email),
            error=str(e),
        )
        return False


# ─── Auth Dependency ─────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency that returns the current authenticated user."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_jwt(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/request-link", response_model=RequestLinkResponse)
async def request_magic_link(
    payload: RequestLinkPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a magic login link. Creates user if they don't exist.

    In dev mode (DEBUG=true), returns the magic link directly in the response
    so you can click it without needing email infrastructure.
    In production, sends the link via Resend email service.
    """
    email = payload.email.lower().strip()
    email_redacted = redact_email(email)

    # Find or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email)
        db.add(user)
        await db.flush()
        logger.info(
            "auth.user_created",
            email_redacted=email_redacted,
            user_id=str(user.id),
        )

    # Generate magic link token
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_expiry_minutes)

    magic_link_record = MagicLink(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
    )
    db.add(magic_link_record)
    await db.commit()

    # Build the magic link URL using frontend origin
    origin = request.headers.get("origin", "http://localhost:5173")
    magic_link_url = f"{origin}/auth/verify?token={token}"

    logger.info(
        "auth.magic_link_created",
        email_redacted=email_redacted,
        expires_at=expires_at.isoformat(),
    )

    if settings.debug:
        # Dev mode: return link directly for easy testing
        return RequestLinkResponse(
            message="Magic link created. Click to log in.",
            magic_link=magic_link_url,
            token=token,
        )
    else:
        # Production: send email via Resend
        email_sent = await send_magic_link_email(email, magic_link_url)
        if email_sent:
            return RequestLinkResponse(
                message="Check your email for a login link.",
            )
        else:
            # Graceful degradation if email fails
            logger.warning(
                "auth.email_fallback",
                email_redacted=email_redacted,
                message="Email service unavailable",
            )
            return RequestLinkResponse(
                message="Check your email for a login link.",
            )


@router.post("/verify", response_model=AuthResponse)
async def verify_magic_link(
    payload: VerifyTokenPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a magic link token and return a JWT access token.

    The magic link token is single-use and time-limited.
    """
    result = await db.execute(
        select(MagicLink).where(MagicLink.token == payload.token)
    )
    magic_link = result.scalar_one_or_none()

    if not magic_link:
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    if magic_link.is_used:
        raise HTTPException(status_code=401, detail="This link has already been used")

    if magic_link.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="This link has expired")

    # Mark as used
    magic_link.is_used = True

    # Get the user
    user_result = await db.execute(
        select(User).where(User.id == magic_link.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Issue JWT
    access_token = create_jwt(user.id, user.email)

    logger.info(
        "auth.login_success",
        email_redacted=redact_email(user.email),
        user_id=str(user.id),
    )

    return AuthResponse(
        access_token=access_token,
        user_id=str(user.id),
        email=user.email,
        is_onboarded=user.is_onboarded,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get the current authenticated user's info."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        is_onboarded=current_user.is_onboarded,
        candidate_id=str(current_user.candidate_id) if current_user.candidate_id else None,
        created_at=current_user.created_at.isoformat(),
    )

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    LogoutResponse,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    RegisterResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from app.auth.service import (
    AuthFlowError,
    complete_password_reset,
    get_current_user_profile,
    login_user,
    logout_user,
    register_tenant_admin,
    refresh_user_tokens,
    initiate_password_reset,
)
from app.commercial.routes import _to_plan_out, _to_subscription_out
from app.core.security.deps import get_current_principal
from app.db_deps import get_auth_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request) -> TokenResponse:
    try:
        result = await login_user(
            tenant_id=payload.tenant_id,
            email=str(payload.email),
            password=payload.password,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            request_id=getattr(request.state, "request_id", None),
        )
    except AuthFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        tenant_id=result.tenant_id,
        access_token_expires_at=result.access_token_expires_at,
        refresh_token_expires_at=result.refresh_token_expires_at,
    )


@router.post("/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest, request: Request) -> RegisterResponse:
    try:
        result = await register_tenant_admin(
            company_name=payload.company_name,
            full_name=payload.full_name,
            email=str(payload.email),
            password=payload.password,
            plan_code=payload.plan_code,
            provider=payload.provider,
            start_trial=payload.start_trial,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            request_id=getattr(request.state, "request_id", None),
        )
    except AuthFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    commercial_status = result.commercial_status
    return RegisterResponse(
        access_token=result.token_pair.access_token,
        refresh_token=result.token_pair.refresh_token,
        tenant_id=result.token_pair.tenant_id,
        access_token_expires_at=result.token_pair.access_token_expires_at,
        refresh_token_expires_at=result.token_pair.refresh_token_expires_at,
        tenant_name=result.tenant_name,
        commercial_status={
            "current_plan": (
                _to_plan_out(commercial_status.current_plan)
                if commercial_status.current_plan
                else None
            ),
            "subscription": (
                _to_subscription_out(commercial_status.subscription)
                if commercial_status.subscription
                else None
            ),
            "subscription_status": commercial_status.subscription_status,
            "trial_status": commercial_status.trial_status,
            "next_billing_at": commercial_status.next_billing_at,
            "renewal_at": commercial_status.renewal_at,
            "provider": commercial_status.provider,
            "provider_name": commercial_status.provider_name,
            "provider_customer_id": commercial_status.provider_customer_id,
            "provider_subscription_id": commercial_status.provider_subscription_id,
            "commercially_active": commercial_status.commercially_active,
        },
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest, request: Request) -> TokenResponse:
    try:
        result = await refresh_user_tokens(
            refresh_token=payload.refresh_token,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            request_id=getattr(request.state, "request_id", None),
        )
    except AuthFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        tenant_id=result.tenant_id,
        access_token_expires_at=result.access_token_expires_at,
        refresh_token_expires_at=result.refresh_token_expires_at,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    payload: LogoutRequest,
    request: Request,
    principal: dict = Depends(get_current_principal),
    db: AsyncSession = Depends(get_auth_db),
) -> LogoutResponse:
    _ensure_tenant_header_matches_principal(request, principal)

    try:
        await logout_user(
            db=db,
            principal_user_id=str(principal["sub"]),
            principal_tenant_id=str(principal["tenant_id"]),
            principal_access_jti=str(principal.get("jti")) if principal.get("jti") else None,
            refresh_token=payload.refresh_token,
            revoke_family=payload.revoke_family,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            request_id=getattr(request.state, "request_id", None),
        )
    except AuthFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return LogoutResponse(success=True)


@router.get("/whoami", response_model=CurrentUserResponse)
async def whoami(
    request: Request,
    principal: dict = Depends(get_current_principal),
    db: AsyncSession = Depends(get_auth_db),
) -> CurrentUserResponse:
    _ensure_tenant_header_matches_principal(request, principal)

    try:
        profile = await get_current_user_profile(
            db=db,
            tenant_id=str(principal["tenant_id"]),
            user_id=str(principal["sub"]),
        )
    except AuthFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return CurrentUserResponse(
        user_id=profile.user_id,
        tenant_id=profile.tenant_id,
        email=profile.email,
        full_name=profile.full_name,
        roles=profile.roles,
        is_owner=profile.is_owner,
        user_is_active=profile.user_is_active,
        membership_is_active=profile.membership_is_active,
        tenant_is_active=profile.tenant_is_active,
    )


@router.post("/password-reset/request", response_model=PasswordResetResponse)
async def password_reset_request(
    payload: PasswordResetRequest,
    request: Request,
) -> PasswordResetResponse:
    try:
        message = await initiate_password_reset(
            tenant_id=payload.tenant_id,
            email=str(payload.email),
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            request_id=getattr(request.state, "request_id", None),
        )
    except AuthFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return PasswordResetResponse(message=message)


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    request: Request,
) -> MessageResponse:
    try:
        await complete_password_reset(
            token=payload.token,
            new_password=payload.new_password,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            request_id=getattr(request.state, "request_id", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return MessageResponse(message="Password updated successfully.")


def _ensure_tenant_header_matches_principal(request: Request, principal: dict) -> None:
    header_tenant_id = getattr(request.state, "header_tenant_id", None)
    principal_tenant_id = str(principal.get("tenant_id", ""))

    if not header_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required tenant header: X-Tenant-Id",
        )
    if str(header_tenant_id) != principal_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant mismatch (header tenant does not match token tenant)",
        )


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None

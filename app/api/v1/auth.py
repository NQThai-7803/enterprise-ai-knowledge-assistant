from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.auth import (
    AuthenticatedUserDataResponse,
    AuthenticatedUserResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenPairData,
    TokenPairResponse,
)
from app.services.auth_service import AuthService, AuthTokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPairResponse)
async def login(
    request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenPairResponse:
    token_pair = await AuthService(session).login(
        email=str(request.email),
        password=request.password.get_secret_value(),
    )
    return _token_pair_response(token_pair)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    request: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenPairResponse:
    token_pair = await AuthService(session).refresh(
        refresh_token=request.refresh_token.get_secret_value(),
    )
    return _token_pair_response(token_pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: LogoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await AuthService(session).logout(
        refresh_token=request.refresh_token.get_secret_value(),
        current_user=current_user,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AuthenticatedUserDataResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AuthenticatedUserDataResponse:
    return AuthenticatedUserDataResponse(
        data=AuthenticatedUserResponse.from_user(current_user),
        meta=None,
    )


def _token_pair_response(token_pair: AuthTokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        data=TokenPairData(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
            user=AuthenticatedUserResponse.from_user(token_pair.user),
        ),
        meta=None,
    )

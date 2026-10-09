from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ianua.api.dependencies import get_db, get_current_user, require_roles
from ianua.models import User, Role
from ianua.schemas import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    ErrorResponse,
    ChangePasswordRequest,
)
from ianua.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post(
    "/register",
    response_model=UserResponse,
    responses={
        409: {
            "model": ErrorResponse,
            "description": "User already exists",
        }
    }
)
def register(
    data: UserCreate,
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    return service.register(data)

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Invalid credentials",
        }
    }
)
def login(
    data: UserLogin,
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    access_token, refresh_token = service.login(data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )

@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Invalid refresh token",
        }
    }
)
def refresh(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    service = AuthService(db)

    access_token, new_refresh_token = service.refresh(data.refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )

@router.post(
    "/logout",
    status_code=204,
    responses={
        204: {
            "description": "Refresh token revoked",
        }
    }
)
def logout(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    service.logout(data.refresh_token)

@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Authentication required or invalid credentials",
        }
    }
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get(
    "/admin",
    response_model=UserResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Authentication required or invalid credentials",
        },
        403: {
            "model": ErrorResponse,
            "description": "Insufficient permissions",
        },
    },
)
def admin_only(current_user: User = Depends(require_roles(Role.ADMIN))):
    return current_user

@router.post(
    "/logout-all",
    status_code=204
)
def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    service.revoke_all_sessions(current_user)

@router.post(
    "/change-password",
    status_code=204,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Invalid credentials",
        },
    },
)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    service.change_password(
        current_user,
        data.current_password,
        data.new_password,
    )
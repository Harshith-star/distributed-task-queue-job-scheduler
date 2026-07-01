"""Auth router."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.redis import get_redis
from app.schemas.auth import (
    ChangePasswordRequest, LoginRequest, RefreshRequest,
    RegisterRequest, TokenResponse, UpdateProfileRequest, UserOut,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

def _ip(request: Request) -> str:
    return request.client.host if request.client else ""

@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    return await AuthService(db, redis).register(payload.email, payload.full_name, payload.password, _ip(request))

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    return await AuthService(db, redis).login(payload.email, payload.password, _ip(request))

@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    return await AuthService(db, redis).refresh(payload.refresh_token)

@router.post("/logout", status_code=204)
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    await AuthService(db, redis).logout(payload.refresh_token)

@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserOut)
async def update_profile(payload: UpdateProfileRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    return await AuthService(db, redis).update_profile(current_user.id, payload.full_name, payload.avatar_url)

@router.post("/change-password", status_code=204)
async def change_password(payload: ChangePasswordRequest, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    await AuthService(db, redis).change_password(current_user.id, payload.current_password, payload.new_password)

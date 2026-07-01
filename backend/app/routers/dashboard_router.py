"""Dashboard router."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.redis import get_redis
from app.schemas.schemas import DashboardStats
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    return await DashboardService(db, redis).get_stats(current_user.id)

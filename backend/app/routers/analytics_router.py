"""Analytics router."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.schemas import AnalyticsResponse
from app.services.dashboard_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("", response_model=AnalyticsResponse)
async def get_analytics(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db), days: int = Query(14, ge=1, le=90)):
    return await AnalyticsService(db).get_analytics(current_user.id, days)

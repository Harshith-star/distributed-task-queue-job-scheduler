"""Generic async base repository — shared CRUD operations."""
from typing import Any, Generic, Type, TypeVar
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository providing common async DB operations.

    Subclass and set `model` to the SQLAlchemy ORM class.
    All methods accept an AsyncSession injected via Depends().
    """

    model: Type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, pk: int) -> ModelT | None:
        return await self._db.get(self.model, pk)

    async def list_all(
        self,
        *filters: Any,
        skip: int = 0,
        limit: int = 20,
        order_by: Any = None,
    ) -> tuple[list[ModelT], int]:
        """Return (items, total_count) with optional filtering and pagination."""
        count_q = select(func.count()).select_from(self.model)
        query   = select(self.model)
        if filters:
            count_q = count_q.where(*filters)
            query   = query.where(*filters)
        if order_by is not None:
            query = query.order_by(order_by)
        total = (await self._db.execute(count_q)).scalar_one()
        items = (await self._db.execute(query.offset(skip).limit(limit))).scalars().all()
        return list(items), total

    async def create(self, **kwargs: Any) -> ModelT:
        obj = self.model(**kwargs)
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def update(self, obj: ModelT, **kwargs: Any) -> ModelT:
        for key, val in kwargs.items():
            if val is not None or key in kwargs:
                setattr(obj, key, val)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self._db.delete(obj)
        await self._db.flush()

    async def save(self) -> None:
        await self._db.commit()

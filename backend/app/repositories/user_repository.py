"""User repository."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._db.get(User, user_id)

    async def exists_by_email(self, email: str) -> bool:
        result = await self._db.execute(
            select(User.id).where(User.email == email).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def create_user(
        self, email: str, full_name: str, hashed_password: str, role: UserRole = UserRole.USER
    ) -> User:
        user = User(email=email, full_name=full_name, hashed_password=hashed_password, role=role)
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def update_password(self, user: User, hashed_password: str) -> None:
        user.hashed_password = hashed_password
        await self._db.commit()

    async def list_users(self, skip: int = 0, limit: int = 20) -> tuple[list[User], int]:
        return await self.list_all(skip=skip, limit=limit)

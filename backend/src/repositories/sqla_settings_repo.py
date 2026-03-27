from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db.models.system import AppSetting
from repositories.base import BaseRepository


class SqlAlchemySettingsRepository(BaseRepository[AppSetting]):
    def __init__(self, session: AsyncSession):
        super().__init__(AppSetting, session)

    async def get(self, key: str) -> Optional[str]:
        stmt = select(AppSetting).where(AppSetting.setting_key == key)
        setting = await self.session.scalar(stmt)
        return setting.setting_value if setting else None

    async def set(self, key: str, value: str) -> None:
        stmt = select(AppSetting).where(AppSetting.setting_key == key)
        setting = await self.session.scalar(stmt)
        if setting:
            setting.setting_value = value
        else:
            setting = AppSetting(setting_key=key, setting_value=value)
            self.session.add(setting)
        await self.session.flush()

    async def get_bulk(self, prefix: str) -> dict[str, str]:
        stmt = select(AppSetting).where(AppSetting.setting_key.like(f"{prefix}%"))
        settings = (await self.session.scalars(stmt)).all()
        return {s.setting_key: s.setting_value for s in settings if s.setting_value is not None}

    async def delete(self, key: str) -> None:
        stmt = delete(AppSetting).where(AppSetting.setting_key == key)
        await self.session.execute(stmt)
        await self.session.flush()

    async def delete_bulk(self, prefix: str) -> None:
        stmt = delete(AppSetting).where(AppSetting.setting_key.like(f"{prefix}%"))
        await self.session.execute(stmt)
        await self.session.flush()

    async def exists(self, key: str) -> bool:
        stmt = select(AppSetting).where(AppSetting.setting_key == key)
        return await self.session.scalar(stmt) is not None

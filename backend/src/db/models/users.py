from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from db.models.tenants import TenantMembership

class User(Base):
    """Primary User Account (Global Identity — not tenant-scoped)"""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Household Profiles associated with this login
    profiles: Mapped[list["UserProfile"]] = relationship(back_populates="user")
    memberships: Mapped[list["TenantMembership"]] = relationship(
        back_populates="user", primaryjoin="User.id == TenantMembership.user_id"
    )


class UserProfile(Base):
    """Household Sub-Profiles (Spouse, Dependents, etc.) — global, not tenant-scoped"""
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile_name: Mapped[str] = mapped_column(String)
    relationship_type: Mapped[str] = mapped_column(String)  # e.g., 'Primary', 'Spouse', 'Dependent'
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="profiles")

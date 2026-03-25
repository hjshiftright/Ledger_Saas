from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base

class User(Base):
    """Primary User Account (Authentication Level)"""
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Household Profiles associated with this login
    profiles: Mapped[list["UserProfile"]] = relationship(back_populates="user")

class UserProfile(Base):
    """Household Sub-Profiles (Spouse, Dependents, etc.)"""
    __tablename__ = "user_profiles"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    profile_name: Mapped[str] = mapped_column(String)
    relationship_type: Mapped[str] = mapped_column(String) # e.g., 'Primary', 'Spouse', 'Dependent'
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    user: Mapped["User"] = relationship(back_populates="profiles")

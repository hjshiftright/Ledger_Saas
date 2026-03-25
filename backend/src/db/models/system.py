from sqlalchemy import String, Integer, Boolean, DateTime, Date, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base
from datetime import datetime, date
class Profile(Base):
    __tablename__ = "profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String, index=True)
    base_currency: Mapped[str] = mapped_column(String, default="INR")
    financial_year_start_month: Mapped[int] = mapped_column(Integer, default=4)
    tax_regime: Mapped[str] = mapped_column(String, default="NEW")
    date_format: Mapped[str] = mapped_column(String, default="DD/MM/YYYY")
    number_format: Mapped[str] = mapped_column(String, default="INDIAN")
    # New fields for financial profile
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    monthly_expenses: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class AppSetting(Base):
    __tablename__ = "app_settings"
    setting_key: Mapped[str] = mapped_column(String, unique=True)
    setting_value: Mapped[str | None] = mapped_column(String, nullable=True)
    setting_type: Mapped[str] = mapped_column(String, default="STRING")
    category: Mapped[str] = mapped_column(String, default="GENERAL")
    description: Mapped[str | None] = mapped_column(String, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String)
    changes_json: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default="USER")
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)

class Notification(Base):
    __tablename__ = "notifications"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    notification_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    related_entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    related_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="MEDIUM")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    action_url: Mapped[str | None] = mapped_column(String, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class BackupHistory(Base):
    __tablename__ = "backup_history"
    backup_type: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    record_counts_json: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="COMPLETED")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


class LlmProvider(Base):
    __tablename__ = "llm_providers"
    user_id: Mapped[str] = mapped_column(String, index=True)
    provider_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    provider_name: Mapped[str] = mapped_column(String)       # gemini | openai | anthropic
    api_key: Mapped[str] = mapped_column(String)             # plain text (encrypt later)
    display_name: Mapped[str] = mapped_column(String, default="")
    text_model: Mapped[str] = mapped_column(String, default="")
    vision_model: Mapped[str] = mapped_column(String, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

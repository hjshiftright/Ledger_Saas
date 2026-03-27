from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, Integer, DateTime, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


class Profile(Base):
    """Global user profile — linked to users.id, not tenant-scoped."""
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    base_currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    financial_year_start_month: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    tax_regime: Mapped[str] = mapped_column(String, nullable=False, default="NEW")
    date_format: Mapped[str] = mapped_column(String, nullable=False, default="DD/MM/YYYY")
    number_format: Mapped[str] = mapped_column(String, nullable=False, default="INDIAN")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LlmProvider(TenantScopedMixin, Base):
    """Per-tenant LLM provider configuration. Replaces the old user_id (str) pattern."""
    __tablename__ = "llm_providers"

    provider_id: Mapped[str] = mapped_column(String, nullable=False)
    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AppSetting(TenantScopedMixin, Base):
    """Per-tenant application settings key-value store."""
    __tablename__ = "app_settings"

    setting_key: Mapped[str] = mapped_column(String, nullable=False)
    setting_value: Mapped[str | None] = mapped_column(String, nullable=True)
    setting_type: Mapped[str] = mapped_column(String, nullable=False, default="STRING")
    category: Mapped[str] = mapped_column(String, nullable=False, default="GENERAL")
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "setting_key", name="uq_setting_tenant_key"),
        CheckConstraint(
            "setting_type IN ('STRING','INTEGER','REAL','BOOLEAN','DATE','JSON')",
            name="ck_setting_type",
        ),
    )


class AuditLog(TenantScopedMixin, Base):
    """Append-only audit trail per tenant. RLS allows INSERT + SELECT only."""
    __tablename__ = "audit_log"

    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    old_values_json: Mapped[str | None] = mapped_column(String, nullable=True)
    new_values_json: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)


class Notification(TenantScopedMixin, Base):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    notification_type: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

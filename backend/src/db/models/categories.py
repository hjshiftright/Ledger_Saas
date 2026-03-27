from sqlalchemy import String, Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


class Payee(TenantScopedMixin, Base):
    __tablename__ = "payees"

    name: Mapped[str] = mapped_column(String, nullable=False)
    category_hint: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_payee_tenant_name"),
    )


class Tag(TenantScopedMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, nullable=False)
    color_hex: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tag_tenant_name"),
    )


class TransactionTag(TenantScopedMixin, Base):
    __tablename__ = "transaction_tags"

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "transaction_id", "tag_id", name="uq_txn_tag"),
    )


class UserCategoryRule(TenantScopedMixin, Base):
    """Categorisation rules — tenant-scoped, replacing the old user_id (str) pattern."""
    __tablename__ = "user_category_rules"

    pattern: Mapped[str] = mapped_column(String, nullable=False)
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    match_type: Mapped[str] = mapped_column(String, nullable=False, default="CONTAINS")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

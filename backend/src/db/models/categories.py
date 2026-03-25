from sqlalchemy import String, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base

class UserCategoryRule(Base):
    """User-defined categorization rules (learned from corrections — R2.4)."""
    __tablename__ = "user_category_rules"
    user_id: Mapped[str] = mapped_column(String, index=True)
    pattern: Mapped[str] = mapped_column(String)        # regex (case-insensitive)
    category_code: Mapped[str] = mapped_column(String)
    priority: Mapped[int] = mapped_column(Integer, default=100)


class Payee(Base):
    __tablename__ = "payees"
    name: Mapped[str] = mapped_column(String)
    default_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    payee_type: Mapped[str] = mapped_column(String, default="OTHER")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Tag(Base):
    __tablename__ = "tags"
    name: Mapped[str] = mapped_column(String, unique=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class TransactionTag(Base):
    __tablename__ = "transaction_tags"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"))
    __table_args__ = (UniqueConstraint("transaction_id", "tag_id"),)

from sqlalchemy import String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal
from datetime import date, datetime
from db.models.base import TenantScopedMixin


class Transaction(TenantScopedMixin, Base):
    __tablename__ = "transactions"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    transaction_number: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    payee_id: Mapped[int | None] = mapped_column(ForeignKey("payees.id"), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="CONFIRMED")
    is_void: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    void_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_of_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    recurring_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_transactions.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    # Dedup fingerprint — SHA-256 hash stored at import time; prevents double-posting
    txn_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    __table_args__ = (
        # Unique constraints are per-tenant, not global
        UniqueConstraint("tenant_id", "transaction_number", name="uq_txn_tenant_number"),
        UniqueConstraint("tenant_id", "txn_hash", name="uq_txn_tenant_hash"),
        CheckConstraint(
            "status IN ('PENDING','CONFIRMED','VOID','RECONCILED')",
            name="ck_transaction_status",
        ),
    )

    # Cascade relationships
    lines: Mapped[list["TransactionLine"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    charges: Mapped[list["TransactionCharge"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan", lazy="selectin"
    )


class TransactionLine(TenantScopedMixin, Base):
    __tablename__ = "transaction_lines"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    line_type: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    security_id: Mapped[int | None] = mapped_column(ForeignKey("securities.id"), nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_lot_id: Mapped[int | None] = mapped_column(ForeignKey("tax_lots.id"), nullable=True)
    currency_code: Mapped[str] = mapped_column(String, default="INR")
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=1)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    transaction: Mapped["Transaction"] = relationship(back_populates="lines")


class TransactionCharge(TenantScopedMixin, Base):
    __tablename__ = "transaction_charges"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    charge_type: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="charges")


class Attachment(TenantScopedMixin, Base):
    __tablename__ = "attachments"
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    file_name: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="attachments")

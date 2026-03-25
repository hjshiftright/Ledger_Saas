from sqlalchemy import String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal
from datetime import date, datetime

class ImportProfile(Base):
    __tablename__ = "import_profiles"
    name: Mapped[str] = mapped_column(String)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("financial_institutions.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String)
    file_format: Mapped[str] = mapped_column(String)
    column_mapping_json: Mapped[str | None] = mapped_column(String, nullable=True)
    date_format: Mapped[str | None] = mapped_column(String, default="DD/MM/YYYY")
    delimiter: Mapped[str | None] = mapped_column(String, default=",")
    skip_header_rows: Mapped[int | None] = mapped_column(Integer, default=1)
    skip_footer_rows: Mapped[int | None] = mapped_column(Integer, default=0)
    encoding: Mapped[str | None] = mapped_column(String, default="UTF-8")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class ImportBatch(Base):
    __tablename__ = "import_batches"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    import_profile_id: Mapped[int | None] = mapped_column(ForeignKey("import_profiles.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String)
    import_started_at: Mapped[datetime] = mapped_column(DateTime)
    import_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="IN_PROGRESS")
    total_records: Mapped[int | None] = mapped_column(Integer, default=0)
    imported_count: Mapped[int | None] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int | None] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int | None] = mapped_column(Integer, default=0)
    error_count: Mapped[int | None] = mapped_column(Integer, default=0)
    error_log: Mapped[str | None] = mapped_column(String, nullable=True)
    target_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    # UUID from the Pydantic ImportBatch; used to link the in-memory pipeline batch to the DB record
    batch_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)

    reconciliation_records: Mapped[list["ReconciliationRecord"]] = relationship(
        back_populates="import_batch", cascade="all, delete-orphan", lazy="selectin"
    )

class ReconciliationRecord(Base):
    __tablename__ = "reconciliation_records"
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"))
    external_date: Mapped[date] = mapped_column(Date)
    external_description: Mapped[str] = mapped_column(String)
    external_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    external_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    external_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    match_status: Mapped[str] = mapped_column(String, default="UNMATCHED")
    matched_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    created_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    user_action: Mapped[str | None] = mapped_column(String, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    import_batch: Mapped["ImportBatch"] = relationship(back_populates="reconciliation_records")

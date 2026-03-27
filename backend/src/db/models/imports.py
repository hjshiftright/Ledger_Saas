from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin


class ImportBatch(TenantScopedMixin, Base):
    __tablename__ = "import_batches"

    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    # UUID from the Pydantic ImportBatch; used to link the in-memory pipeline batch to the DB record
    batch_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','COMPLETED','FAILED','CANCELLED')",
            name="ck_import_batch_status",
        ),
    )

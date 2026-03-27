from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from db.models.base import Base
import uuid


class Tenant(Base):
    """A financial account/entity (e.g., Ravi's Personal Account).

    Global table — no tenant_id. One user can own many tenants;
    one tenant can have many users (M:N via TenantMembership).
    """
    __tablename__ = "tenants"

    # Override Base.id with UUID primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False, default="PERSONAL")
    # PERSONAL, SOLE_PROPRIETOR, PARTNERSHIP, PRIVATE_LIMITED, LLP, TRUST, HUF, OTHER
    pan_number: Mapped[str | None] = mapped_column(String, nullable=True)
    plan: Mapped[str] = mapped_column(String, nullable=False, default="FREE")
    # FREE, BASIC, PRO, ENTERPRISE
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")
    # ACTIVE, SUSPENDED, DELETED
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('PERSONAL','SOLE_PROPRIETOR','PARTNERSHIP','PRIVATE_LIMITED','LLP','TRUST','HUF','OTHER')",
            name="ck_tenant_entity_type",
        ),
        CheckConstraint(
            "plan IN ('FREE','BASIC','PRO','ENTERPRISE')",
            name="ck_tenant_plan",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','SUSPENDED','DELETED')",
            name="ck_tenant_status",
        ),
    )

    # Relationships
    memberships: Mapped[list["TenantMembership"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class TenantMembership(Base):
    """M:N junction table: links Users to Tenants with per-tenant roles.

    Global table — no tenant_id. Governs access, not financial data.
    """
    __tablename__ = "tenant_memberships"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String, nullable=False, default="MEMBER")
    # OWNER, ADMIN, MEMBER, VIEWER, ADVISOR, ACCOUNTANT
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    invited_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    invited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
        CheckConstraint(
            "role IN ('OWNER','ADMIN','MEMBER','VIEWER','ADVISOR','ACCOUNTANT')",
            name="ck_membership_role",
        ),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(
        back_populates="memberships", foreign_keys=[user_id]
    )
    invited_by: Mapped["User | None"] = relationship(foreign_keys=[invited_by_user_id])

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.models.users import User
from db.models.tenants import Tenant, TenantMembership

@pytest.mark.asyncio
async def test_provision_user_and_tenant(db_session: AsyncSession):
    # This test verifies that we can create a user, a tenant, 
    # and a membership joining them.
    
    # 1. Create a user
    new_user = User(
        email="ravi@example.com",
        hashed_password="hashed_pass",
        is_active=True
    )
    db_session.add(new_user)
    await db_session.flush()
    
    # 2. Create a tenant
    new_tenant = Tenant(
        name="Ravi Personal",
        entity_type="PERSONAL",
        created_by_user_id=new_user.id
    )
    db_session.add(new_tenant)
    await db_session.flush()
    
    # 3. Create a membership
    membership = TenantMembership(
        tenant_id=new_tenant.id,
        user_id=new_user.id,
        role="OWNER"
    )
    db_session.add(membership)
    await db_session.flush()
    
    assert new_user.id is not None
    assert new_tenant.id is not None
    assert membership.id is not None

from db.models.transactions import Transaction
from datetime import date
import uuid

@pytest.mark.asyncio
async def test_rls_isolation(db_session: AsyncSession):
    # Setup Tenant A and Tenant B
    tenant_A_id = uuid.uuid4()
    tenant_B_id = uuid.uuid4()
    
    # Needs a user for FK
    new_user = User(email="test_rls@example.com", hashed_password="pw")
    db_session.add(new_user)
    await db_session.flush()

    # Insert transactions into both as SUPERUSER (bypassing RLS)
    txn_A = Transaction(
        tenant_id=tenant_A_id,
        user_id=new_user.id,
        transaction_date=date(2026, 1, 1),
        transaction_type="DEBIT",
        description="Tenant A Expense"
    )
    
    txn_B = Transaction(
        tenant_id=tenant_B_id,
        user_id=new_user.id,
        transaction_date=date(2026, 1, 1),
        transaction_type="DEBIT",
        description="Tenant B Expense"
    )
    db_session.add_all([txn_A, txn_B])
    await db_session.flush()
    # Commit to ensure rows are accessible if we launch another transaction
    await db_session.commit()

    # Create a new connection to test the restrictive RLS constraints 
    # instead of inside the same transaction block where we just inserted 
    # using superuser.
    async with db_session.bind.connect() as conn:
        # Act as app_service and switch to Tenant A context
        await conn.execute(text("SET ROLE app_service"))
        await conn.execute(text("SELECT set_config('app.tenant_id', :tid, TRUE)"), {"tid": str(tenant_A_id)})

        from sqlalchemy import select
        res = await conn.execute(select(Transaction.description))
        rows = res.scalars().all()
        
        # Isolation: As app_service under Tenant A, we should ONLY see Tenant A's txns
        assert len(rows) == 1
        assert rows[0] == "Tenant A Expense"
        
        # Test 2: Try to insert data for Tenant B while logged in as Tenant A
        from sqlalchemy.exc import DBAPIError
        import pytest
        
        with pytest.raises(DBAPIError, match="row violates row-level security policy"):
            await conn.execute(text(
                "INSERT INTO transactions (tenant_id, user_id, transaction_date, transaction_type, description) "
                "VALUES (:tid, :uid, '2026-01-01', 'DEBIT', 'Hacked Tenant B')"
            ), {"tid": str(tenant_B_id), "uid": new_user.id})

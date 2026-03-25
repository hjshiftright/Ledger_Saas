"""
Migration script for Onboarding V2 tables

Creates:
- onboarding_profiles
- financial_goals
- user_assets
- user_liabilities
- city_data
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from ..config import get_settings
from ..onboarding_v2.models import Base, CityData


def migrate_onboarding_v2():
    """Create onboarding v2 tables"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    # Create all tables from models
    print("Creating onboarding v2 tables...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("✓ Tables created successfully")
    
    # Seed city data
    print("Seeding city data...")
    seed_cities(engine)
    print("✓ City data seeded successfully")
    
    print("Onboarding V2 migration complete!")


def seed_cities(engine):
    """Seed Indian cities with tier and COL index"""
    cities_data = [
        # Tier 1 Metro Cities
        {"city_name": "Mumbai", "tier": 1, "col_index": 2.0, "avg_1bhk_rent": 35000, "avg_2bhk_rent": 60000},
        {"city_name": "Delhi", "tier": 1, "col_index": 1.7, "avg_1bhk_rent": 30000, "avg_2bhk_rent": 50000},
        {"city_name": "Bangalore", "tier": 1, "col_index": 1.5, "avg_1bhk_rent": 25000, "avg_2bhk_rent": 45000},
        {"city_name": "Hyderabad", "tier": 1, "col_index": 1.3, "avg_1bhk_rent": 20000, "avg_2bhk_rent": 35000},
        {"city_name": "Pune", "tier": 1, "col_index": 1.4, "avg_1bhk_rent": 22000, "avg_2bhk_rent": 38000},
        {"city_name": "Chennai", "tier": 1, "col_index": 1.2, "avg_1bhk_rent": 18000, "avg_2bhk_rent": 32000},
        {"city_name": "Kolkata", "tier": 1, "col_index": 1.1, "avg_1bhk_rent": 15000, "avg_2bhk_rent": 28000},
        {"city_name": "Ahmedabad", "tier": 1, "col_index": 1.0, "avg_1bhk_rent": 15000, "avg_2bhk_rent": 25000},
        
        # Tier 2 Cities
        {"city_name": "Jaipur", "tier": 2, "col_index": 0.9, "avg_1bhk_rent": 12000, "avg_2bhk_rent": 20000},
        {"city_name": "Lucknow", "tier": 2, "col_index": 0.85, "avg_1bhk_rent": 10000, "avg_2bhk_rent": 18000},
        {"city_name": "Kanpur", "tier": 2, "col_index": 0.8, "avg_1bhk_rent": 9000, "avg_2bhk_rent": 15000},
        {"city_name": "Nagpur", "tier": 2, "col_index": 0.85, "avg_1bhk_rent": 10000, "avg_2bhk_rent": 18000},
        {"city_name": "Indore", "tier": 2, "col_index": 0.9, "avg_1bhk_rent": 11000, "avg_2bhk_rent": 19000},
        {"city_name": "Bhopal", "tier": 2, "col_index": 0.85, "avg_1bhk_rent": 10000, "avg_2bhk_rent": 17000},
        {"city_name": "Visakhapatnam", "tier": 2, "col_index": 0.85, "avg_1bhk_rent": 10000, "avg_2bhk_rent": 18000},
        {"city_name": "Patna", "tier": 2, "col_index": 0.8, "avg_1bhk_rent": 9000, "avg_2bhk_rent": 15000},
        {"city_name": "Vadodara", "tier": 2, "col_index": 0.9, "avg_1bhk_rent": 11000, "avg_2bhk_rent": 18000},
        {"city_name": "Surat", "tier": 2, "col_index": 0.9, "avg_1bhk_rent": 11000, "avg_2bhk_rent": 19000},
        {"city_name": "Coimbatore", "tier": 2, "col_index": 0.85, "avg_1bhk_rent": 10000, "avg_2bhk_rent": 17000},
        {"city_name": "Kochi", "tier": 2, "col_index": 0.9, "avg_1bhk_rent": 12000, "avg_2bhk_rent": 20000},
        {"city_name": "Chandigarh", "tier": 2, "col_index": 1.2, "avg_1bhk_rent": 18000, "avg_2bhk_rent": 30000},
        
        # Tier 3 / Other
        {"city_name": "Other", "tier": 3, "col_index": 0.75, "avg_1bhk_rent": 8000, "avg_2bhk_rent": 12000},
    ]
    
    with Session(engine) as session:
        # Check if already seeded
        existing = session.query(CityData).count()
        if existing > 0:
            print(f"  City data already seeded ({existing} cities found)")
            return
        
        # Insert cities
        for city_data in cities_data:
            city = CityData(**city_data)
            session.add(city)
        
        session.commit()
        print(f"  Seeded {len(cities_data)} cities")


def rollback_onboarding_v2():
    """Drop onboarding v2 tables (USE WITH CAUTION!)"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    tables_to_drop = [
        "user_liabilities",
        "user_assets",
        "financial_goals",
        "onboarding_profiles",
        "city_data"
    ]
    
    print("WARNING: About to drop onboarding v2 tables!")
    confirm = input("Type 'DROP ALL TABLES' to confirm: ")
    if confirm != "DROP ALL TABLES":
        print("Rollback cancelled.")
        return
    
    with engine.connect() as conn:
        for table in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                print(f"✓ Dropped table: {table}")
            except Exception as e:
                print(f"✗ Error dropping {table}: {e}")
        conn.commit()
    
    print("Rollback complete.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_onboarding_v2()
    else:
        migrate_onboarding_v2()

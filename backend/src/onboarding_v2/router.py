"""
Onboarding V2 - API Router

REST API endpoints for profile-based onboarding flow
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..api.deps import get_db, get_current_user
from .service import OnboardingService
from .schemas import (
    ProfileCreateRequest,
    ProfileResponse,
    GoalsCreateRequest,
    GoalsSummaryResponse,
    AssetsCreateRequest,
    LiabilitiesCreateRequest,
    NetWorthResponse,
    OnboardingCompleteResponse,
    OnboardingResumeResponse,
    CityResponse,
    ErrorResponse
)
from .models import CityData


router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding-v2"])


@router.post(
    "/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    }
)
def create_profile(
    data: ProfileCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create onboarding profile with user context
    
    - **name**: User's full name
    - **age**: User's age (18-100)
    - **profile_type**: salaried_employee, business_owner, or early_investor
    - **city**: City of residence
    - **marital_status**: single, married, or divorced
    - **monthly_income_range**: Income range code (e.g., "1l_2l")
    
    Returns created profile with auto-applied defaults based on profile type.
    """
    try:
        service = OnboardingService(db)
        profile = service.create_profile(
            user_id=current_user["user_id"],
            data=data
        )
        
        return ProfileResponse(
            profile_id=profile.profile_id,
            name=profile.name,
            age=profile.age,
            profile_type=profile.profile_type.value,
            city=profile.city,
            city_tier=profile.city_tier,
            col_index=profile.col_index,
            marital_status=profile.marital_status,
            children_count=profile.children_count,
            monthly_income_range=profile.monthly_income_range,
            risk_tolerance=profile.risk_tolerance,
            investment_experience=profile.investment_experience,
            is_complete=profile.is_complete
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {str(e)}"
        )


@router.post(
    "/goals",
    response_model=GoalsSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid goal data"},
        404: {"model": ErrorResponse, "description": "Profile not found"}
    }
)
def create_goals(
    data: GoalsCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create financial goals with auto-calculations
    
    Accepts list of goals with type and basic parameters.
    Automatically calculates:
    - Target corpus with inflation
    - Monthly SIP required
    - Feasibility based on income
    
    Supported goal types:
    - retirement: 25x rule with inflation
    - child_education: Education corpus with 8% inflation
    - home_purchase: Down payment with property appreciation
    - car_purchase: Car down payment
    - marriage: Wedding fund
    - vacation: Annual + special trip fund
    """
    try:
        service = OnboardingService(db)
        
        # Create goals
        goals = service.create_goals(
            profile_id=data.profile_id,
            goals_data=data.goals
        )
        
        # Get summary with feasibility
        summary = service.get_goals_summary(data.profile_id)
        
        return GoalsSummaryResponse(
            profile_id=data.profile_id,
            goals=[
                {
                    "goal_id": g["goal_id"],
                    "goal_type": g["goal_type"],
                    "target_amount": g["target_amount"],
                    "monthly_saving_required": g["monthly_saving_required"],
                    "years_to_goal": g["years_to_goal"],
                    "details": g["details"]
                }
                for g in summary["goals"]
            ],
            total_monthly_required=summary["total_monthly_required"],
            feasibility=summary["feasibility"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create goals: {str(e)}"
        )


@router.post(
    "/assets",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid asset data"},
        404: {"model": ErrorResponse, "description": "Profile not found"}
    }
)
def create_assets(
    data: AssetsCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Record user assets
    
    Accepts list of assets with type, value, and institution.
    Supported asset types:
    - bank_account: Savings/current accounts
    - epf: Employee Provident Fund
    - ppf: Public Provident Fund
    - mutual_fund: Mutual fund investments
    - stocks: Stock holdings
    - fixed_deposit: Fixed deposits
    - gold: Physical/digital gold
    - real_estate: Property
    - vehicle: Cars, bikes
    - other: Other assets
    """
    try:
        service = OnboardingService(db)
        assets = service.create_assets(
            profile_id=data.profile_id,
            assets_data=data.assets
        )
        
        return {
            "message": f"Successfully created {len(assets)} assets",
            "asset_count": len(assets)
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create assets: {str(e)}"
        )


@router.post(
    "/liabilities",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid liability data"},
        404: {"model": ErrorResponse, "description": "Profile not found"}
    }
)
def create_liabilities(
    data: LiabilitiesCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Record user liabilities
    
    Accepts list of liabilities with type, outstanding, EMI, and interest rate.
    Supported liability types:
    - home_loan: Housing loan
    - vehicle_loan: Car/bike loan
    - education_loan: Education loan
    - personal_loan: Personal loan
    - credit_card: Credit card outstanding
    - other: Other debts
    """
    try:
        service = OnboardingService(db)
        liabilities = service.create_liabilities(
            profile_id=data.profile_id,
            liabilities_data=data.liabilities
        )
        
        return {
            "message": f"Successfully created {len(liabilities)} liabilities",
            "liability_count": len(liabilities)
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create liabilities: {str(e)}"
        )


@router.get(
    "/net-worth",
    response_model=NetWorthResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Profile not found"}
    }
)
def get_net_worth(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate net worth from assets and liabilities
    
    Returns:
    - Total assets broken down by type
    - Total liabilities broken down by type
    - Net worth (assets - liabilities)
    - Total monthly EMI burden
    """
    try:
        service = OnboardingService(db)
        net_worth_data = service.calculate_net_worth(profile_id)
        
        return NetWorthResponse(
            profile_id=profile_id,
            total_assets=net_worth_data["total_assets"],
            total_liabilities=net_worth_data["total_liabilities"],
            net_worth=net_worth_data["net_worth"],
            total_monthly_emi=net_worth_data["total_monthly_emi"],
            asset_breakdown=net_worth_data["asset_breakdown"],
            liability_breakdown=net_worth_data["liability_breakdown"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate net worth: {str(e)}"
        )


@router.post(
    "/complete",
    response_model=OnboardingCompleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Profile not found"}
    }
)
def complete_onboarding(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Mark onboarding as complete and return summary
    
    Returns:
    - Profile summary
    - Goals summary with feasibility
    - Net worth breakdown
    - Recommended chart of accounts based on profile type
    - Next steps for user
    """
    try:
        service = OnboardingService(db)
        summary = service.complete_onboarding(profile_id)
        
        return OnboardingCompleteResponse(
            profile=summary["profile"],
            goals_summary=summary["goals_summary"],
            net_worth=summary["net_worth"],
            chart_of_accounts_template=summary["chart_of_accounts_template"],
            next_steps=summary["next_steps"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete onboarding: {str(e)}"
        )


@router.get(
    "/resume",
    response_model=OnboardingResumeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No onboarding found"}
    }
)
def resume_onboarding(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Resume incomplete onboarding session
    
    Returns current onboarding state:
    - Profile exists? (screen 1 complete)
    - Goals exist? (screen 2 complete)
    - Assets/liabilities exist? (screen 3 complete)
    - Is complete? (screen 4 complete)
    
    Allows user to continue from where they left off.
    """
    try:
        from .models import OnboardingProfile, FinancialGoal, UserAsset, UserLiability
        
        # Find latest profile for user
        profile = db.query(OnboardingProfile).filter_by(
            user_id=current_user["user_id"]
        ).order_by(OnboardingProfile.created_at.desc()).first()
        
        if not profile:
            return OnboardingResumeResponse(
                has_profile=False,
                has_goals=False,
                has_financials=False,
                is_complete=False,
                next_screen=1,
                profile_id=None
            )
        
        # Check what's completed
        has_goals = db.query(FinancialGoal).filter_by(profile_id=profile.profile_id).count() > 0
        has_assets = db.query(UserAsset).filter_by(profile_id=profile.profile_id).count() > 0
        has_liabilities = db.query(UserLiability).filter_by(profile_id=profile.profile_id).count() > 0
        has_financials = has_assets or has_liabilities
        
        # Determine next screen
        if profile.is_complete:
            next_screen = 4  # Review
        elif has_financials:
            next_screen = 4  # Review
        elif has_goals:
            next_screen = 3  # Finances
        else:
            next_screen = 2  # Goals
        
        return OnboardingResumeResponse(
            has_profile=True,
            has_goals=has_goals,
            has_financials=has_financials,
            is_complete=profile.is_complete,
            next_screen=next_screen,
            profile_id=profile.profile_id,
            profile_data={
                "name": profile.name,
                "age": profile.age,
                "profile_type": profile.profile_type.value,
                "city": profile.city
            } if profile else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume onboarding: {str(e)}"
        )


@router.get(
    "/cities",
    response_model=List[CityResponse],
    responses={
        500: {"model": ErrorResponse, "description": "Failed to fetch cities"}
    }
)
def get_cities(
    db: Session = Depends(get_db)
):
    """
    Get list of supported Indian cities with tier and COL index
    
    Returns cities sorted by tier (1→2→3) then alphabetically.
    Each city includes:
    - City name
    - Tier (1: Metro, 2: Tier-2, 3: Tier-3)
    - Cost of Living Index (Mumbai = 2.0 baseline)
    """
    try:
        # Try to get from database
        cities = db.query(CityData).order_by(
            CityData.tier,
            CityData.city_name
        ).all()
        
        if cities:
            return [
                CityResponse(
                    city_name=city.city_name,
                    tier=city.tier,
                    col_index=city.col_index
                )
                for city in cities
            ]
        
        # Fallback: Return hardcoded list if database not seeded
        hardcoded_cities = [
            # Tier 1
            {"city_name": "Mumbai", "tier": 1, "col_index": 2.0},
            {"city_name": "Delhi", "tier": 1, "col_index": 1.7},
            {"city_name": "Bangalore", "tier": 1, "col_index": 1.5},
            {"city_name": "Hyderabad", "tier": 1, "col_index": 1.3},
            {"city_name": "Pune", "tier": 1, "col_index": 1.4},
            {"city_name": "Chennai", "tier": 1, "col_index": 1.2},
            {"city_name": "Kolkata", "tier": 1, "col_index": 1.1},
            {"city_name": "Ahmedabad", "tier": 1, "col_index": 1.0},
            # Tier 2
            {"city_name": "Jaipur", "tier": 2, "col_index": 0.9},
            {"city_name": "Lucknow", "tier": 2, "col_index": 0.85},
            {"city_name": "Kanpur", "tier": 2, "col_index": 0.8},
            {"city_name": "Nagpur", "tier": 2, "col_index": 0.85},
            {"city_name": "Indore", "tier": 2, "col_index": 0.9},
            {"city_name": "Bhopal", "tier": 2, "col_index": 0.85},
            {"city_name": "Visakhapatnam", "tier": 2, "col_index": 0.85},
            {"city_name": "Patna", "tier": 2, "col_index": 0.8},
            # Tier 3
            {"city_name": "Other", "tier": 3, "col_index": 0.75}
        ]
        
        return [CityResponse(**city) for city in hardcoded_cities]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch cities: {str(e)}"
        )

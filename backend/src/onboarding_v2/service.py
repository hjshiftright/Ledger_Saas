"""
Onboarding V2 - Service Layer

Orchestrates onboarding workflow, applies defaults, and generates financial plans
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .models import (
    OnboardingProfile,
    FinancialGoal,
    UserAsset,
    UserLiability,
    ProfileType,
    GoalType,
    AssetType,
    LiabilityType
)
from .schemas import (
    ProfileCreateRequest,
    GoalCreateRequest,
    AssetCreateRequest,
    LiabilityCreateRequest
)
from .calculators import (
    calculate_retirement_corpus,
    calculate_education_corpus,
    calculate_home_down_payment,
    calculate_car_down_payment,
    calculate_vacation_fund,
    calculate_goal_feasibility,
    get_city_property_price,
    get_income_range_values
)


class OnboardingService:
    """Service for onboarding workflow operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_profile(self, user_id: str, data: ProfileCreateRequest) -> OnboardingProfile:
        """
        Create onboarding profile with intelligent defaults
        
        Args:
            user_id: User ID
            data: Profile creation request
        
        Returns:
            Created OnboardingProfile
        """
        # Apply defaults based on profile type
        defaults = self._get_profile_defaults(data.profile_type)
        
        profile = OnboardingProfile(
            user_id=user_id,
            name=data.name,
            age=data.age,
            profile_type=data.profile_type,
            city=data.city,
            city_tier=data.city_tier or self._get_city_tier(data.city),
            col_index=data.col_index or self._get_col_index(data.city),
            marital_status=data.marital_status,
            children_count=data.children_count or 0,
            monthly_income_range=data.monthly_income_range,
            risk_tolerance=data.risk_tolerance or defaults["risk_tolerance"],
            investment_experience=data.investment_experience or defaults["investment_experience"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        return profile
    
    def create_goals(
        self,
        profile_id: int,
        goals_data: List[GoalCreateRequest]
    ) -> List[FinancialGoal]:
        """
        Create financial goals with auto-calculations
        
        Args:
            profile_id: Onboarding profile ID
            goals_data: List of goal creation requests
        
        Returns:
            List of created FinancialGoal objects
        """
        profile = self.db.query(OnboardingProfile).filter_by(profile_id=profile_id).first()
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        created_goals = []
        
        for goal_data in goals_data:
            # Calculate goal details based on type
            calculation = self._calculate_goal_details(
                goal_type=goal_data.goal_type,
                profile=profile,
                goal_data=goal_data
            )
            
            goal = FinancialGoal(
                profile_id=profile_id,
                goal_type=goal_data.goal_type,
                target_amount_paise=calculation["target_amount"] * 100,
                monthly_saving_required_paise=calculation["monthly_sip"] * 100,
                years_to_goal=calculation["years_to_goal"],
                inflation_rate=calculation.get("inflation_rate", 0.06),
                return_rate=calculation.get("return_rate", 0.12),
                details=calculation,  # Store full calculation as JSON
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(goal)
            created_goals.append(goal)
        
        self.db.commit()
        
        for goal in created_goals:
            self.db.refresh(goal)
        
        return created_goals
    
    def create_assets(
        self,
        profile_id: int,
        assets_data: List[AssetCreateRequest]
    ) -> List[UserAsset]:
        """
        Create user assets
        
        Args:
            profile_id: Onboarding profile ID
            assets_data: List of asset creation requests
        
        Returns:
            List of created UserAsset objects
        """
        created_assets = []
        
        for asset_data in assets_data:
            asset = UserAsset(
                profile_id=profile_id,
                asset_type=asset_data.asset_type,
                name=asset_data.name,
                current_value_paise=asset_data.current_value * 100,
                institution=asset_data.institution,
                account_number_last4=asset_data.account_number_last4,
                details=asset_data.details or {},
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(asset)
            created_assets.append(asset)
        
        self.db.commit()
        
        for asset in created_assets:
            self.db.refresh(asset)
        
        return created_assets
    
    def create_liabilities(
        self,
        profile_id: int,
        liabilities_data: List[LiabilityCreateRequest]
    ) -> List[UserLiability]:
        """
        Create user liabilities
        
        Args:
            profile_id: Onboarding profile ID
            liabilities_data: List of liability creation requests
        
        Returns:
            List of created UserLiability objects
        """
        created_liabilities = []
        
        for liability_data in liabilities_data:
            liability = UserLiability(
                profile_id=profile_id,
                liability_type=liability_data.liability_type,
                name=liability_data.name,
                outstanding_amount_paise=liability_data.outstanding_amount * 100,
                monthly_emi_paise=liability_data.monthly_emi * 100,
                interest_rate=liability_data.interest_rate,
                institution=liability_data.institution,
                details=liability_data.details or {},
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(liability)
            created_liabilities.append(liability)
        
        self.db.commit()
        
        for liability in created_liabilities:
            self.db.refresh(liability)
        
        return created_liabilities
    
    def calculate_net_worth(self, profile_id: int) -> Dict[str, Any]:
        """
        Calculate net worth from assets and liabilities
        
        Args:
            profile_id: Onboarding profile ID
        
        Returns:
            Dictionary with asset breakdown, liability breakdown, and net worth
        """
        assets = self.db.query(UserAsset).filter_by(profile_id=profile_id).all()
        liabilities = self.db.query(UserLiability).filter_by(profile_id=profile_id).all()
        
        # Aggregate assets by type
        asset_breakdown = {}
        total_assets = 0
        
        for asset in assets:
            asset_type_name = asset.asset_type.value
            if asset_type_name not in asset_breakdown:
                asset_breakdown[asset_type_name] = {
                    "count": 0,
                    "total_value": 0,
                    "items": []
                }
            
            asset_breakdown[asset_type_name]["count"] += 1
            asset_breakdown[asset_type_name]["total_value"] += asset.current_value_rupees
            asset_breakdown[asset_type_name]["items"].append({
                "name": asset.name,
                "value": asset.current_value_rupees,
                "institution": asset.institution
            })
            
            total_assets += asset.current_value_rupees
        
        # Aggregate liabilities by type
        liability_breakdown = {}
        total_liabilities = 0
        total_monthly_emi = 0
        
        for liability in liabilities:
            liability_type_name = liability.liability_type.value
            if liability_type_name not in liability_breakdown:
                liability_breakdown[liability_type_name] = {
                    "count": 0,
                    "total_outstanding": 0,
                    "total_emi": 0,
                    "items": []
                }
            
            liability_breakdown[liability_type_name]["count"] += 1
            liability_breakdown[liability_type_name]["total_outstanding"] += liability.outstanding_amount_rupees
            liability_breakdown[liability_type_name]["total_emi"] += liability.monthly_emi_rupees
            liability_breakdown[liability_type_name]["items"].append({
                "name": liability.name,
                "outstanding": liability.outstanding_amount_rupees,
                "emi": liability.monthly_emi_rupees,
                "interest_rate": liability.interest_rate
            })
            
            total_liabilities += liability.outstanding_amount_rupees
            total_monthly_emi += liability.monthly_emi_rupees
        
        net_worth = total_assets - total_liabilities
        
        return {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
            "total_monthly_emi": total_monthly_emi,
            "asset_breakdown": asset_breakdown,
            "liability_breakdown": liability_breakdown
        }
    
    def get_goals_summary(self, profile_id: int) -> Dict[str, Any]:
        """
        Get summary of all goals with feasibility analysis
        
        Args:
            profile_id: Onboarding profile ID
        
        Returns:
            Dictionary with goals summary and feasibility
        """
        profile = self.db.query(OnboardingProfile).filter_by(profile_id=profile_id).first()
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        goals = self.db.query(FinancialGoal).filter_by(profile_id=profile_id, is_active=True).all()
        
        goals_list = []
        total_monthly_required = 0
        
        for goal in goals:
            goals_list.append({
                "goal_id": goal.goal_id,
                "goal_type": goal.goal_type.value,
                "target_amount": goal.target_amount_rupees,
                "monthly_saving_required": goal.monthly_saving_required_rupees,
                "years_to_goal": goal.years_to_goal,
                "details": goal.details
            })
            total_monthly_required += goal.monthly_saving_required_rupees
        
        # Get income range
        income_range = get_income_range_values(profile.monthly_income_range or "1l_2l")
        
        # Calculate feasibility
        feasibility = calculate_goal_feasibility(
            total_monthly_required=total_monthly_required,
            monthly_income_min=income_range["min"],
            monthly_income_max=income_range["max"]
        )
        
        return {
            "goals": goals_list,
            "total_monthly_required": total_monthly_required,
            "feasibility": feasibility
        }
    
    def complete_onboarding(self, profile_id: int) -> Dict[str, Any]:
        """
        Mark onboarding as complete and return summary
        
        Args:
            profile_id: Onboarding profile ID
        
        Returns:
            Complete onboarding summary
        """
        profile = self.db.query(OnboardingProfile).filter_by(profile_id=profile_id).first()
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        
        # Mark as complete
        profile.is_complete = True
        profile.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Gather all data
        goals_summary = self.get_goals_summary(profile_id)
        net_worth = self.calculate_net_worth(profile_id)
        
        # Generate recommended chart of accounts based on profile type
        coa_template = self._get_chart_of_accounts_template(profile.profile_type)
        
        return {
            "profile": {
                "profile_id": profile.profile_id,
                "name": profile.name,
                "age": profile.age,
                "profile_type": profile.profile_type.value,
                "city": profile.city,
                "marital_status": profile.marital_status,
                "children_count": profile.children_count
            },
            "goals_summary": goals_summary,
            "net_worth": net_worth,
            "chart_of_accounts_template": coa_template,
            "next_steps": [
                "Review and approve proposed transactions",
                "Set up automatic imports from bank accounts",
                "Configure budget categories",
                "Enable smart categorization"
            ]
        }
    
    # Private helper methods
    
    def _get_profile_defaults(self, profile_type: ProfileType) -> Dict[str, str]:
        """Get default values based on profile type"""
        defaults = {
            ProfileType.SALARIED_EMPLOYEE: {
                "risk_tolerance": "moderate",
                "investment_experience": "basic"
            },
            ProfileType.BUSINESS_OWNER: {
                "risk_tolerance": "high",
                "investment_experience": "intermediate"
            },
            ProfileType.EARLY_INVESTOR: {
                "risk_tolerance": "very_high",
                "investment_experience": "advanced"
            }
        }
        return defaults.get(profile_type, defaults[ProfileType.SALARIED_EMPLOYEE])
    
    def _get_city_tier(self, city: str) -> int:
        """Determine city tier"""
        tier_1_cities = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad"]
        tier_2_cities = ["Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Bhopal", "Visakhapatnam", "Patna"]
        
        if city in tier_1_cities:
            return 1
        elif city in tier_2_cities:
            return 2
        else:
            return 3
    
    def _get_col_index(self, city: str) -> float:
        """Get cost of living index for city"""
        col_indexes = {
            "Mumbai": 2.0,
            "Delhi": 1.7,
            "Bangalore": 1.5,
            "Hyderabad": 1.3,
            "Pune": 1.4,
            "Chennai": 1.2,
            "Kolkata": 1.1,
            "Ahmedabad": 1.0
        }
        return col_indexes.get(city, 1.0)
    
    def _calculate_goal_details(
        self,
        goal_type: GoalType,
        profile: OnboardingProfile,
        goal_data: GoalCreateRequest
    ) -> Dict[str, Any]:
        """Calculate goal-specific details"""
        
        if goal_type == GoalType.RETIREMENT:
            # Get monthly expenses from details or use default
            monthly_expense = goal_data.details.get("monthly_expense", 50000) if goal_data.details else 50000
            
            result = calculate_retirement_corpus(
                current_age=profile.age,
                retirement_age=goal_data.details.get("retirement_age", 60) if goal_data.details else 60,
                monthly_expense=monthly_expense
            )
            result["years_to_goal"] = result["years_to_retirement"]
            
        elif goal_type == GoalType.CHILD_EDUCATION:
            child_age = goal_data.details.get("child_age", 5) if goal_data.details else 5
            current_cost = goal_data.details.get("current_cost", 2500000) if goal_data.details else 2500000
            
            result = calculate_education_corpus(
                child_current_age=child_age,
                current_cost=current_cost
            )
            result["years_to_goal"] = result["years_to_save"]
            result["target_amount"] = result["future_cost"]
            
        elif goal_type == GoalType.HOME_PURCHASE:
            property_value = goal_data.details.get("property_value") if goal_data.details else None
            if not property_value:
                # Auto-calculate based on city
                property_value = get_city_property_price(profile.city, "2bhk")
            
            years_to_save = goal_data.details.get("years_to_save", 5) if goal_data.details else 5
            
            result = calculate_home_down_payment(
                property_value=property_value,
                years_to_save=years_to_save
            )
            result["years_to_goal"] = years_to_save
            result["target_amount"] = result["down_payment_required"]
            
        elif goal_type == GoalType.CAR_PURCHASE:
            car_value = goal_data.details.get("car_value", 1200000) if goal_data.details else 1200000
            years_to_save = goal_data.details.get("years_to_save", 2) if goal_data.details else 2
            
            result = calculate_car_down_payment(
                car_value=car_value,
                years_to_save=years_to_save
            )
            result["years_to_goal"] = years_to_save
            result["target_amount"] = result["down_payment_required"]
            
        elif goal_type == GoalType.VACATION:
            annual_budget = goal_data.details.get("annual_budget", 200000) if goal_data.details else 200000
            special_trip = goal_data.details.get("special_trip_cost", 500000) if goal_data.details else 500000
            years_to_special = goal_data.details.get("years_to_special_trip", 3) if goal_data.details else 3
            
            result = calculate_vacation_fund(
                annual_budget=annual_budget,
                special_trip_cost=special_trip,
                years_to_special_trip=years_to_special
            )
            result["years_to_goal"] = years_to_special
            result["target_amount"] = annual_budget + special_trip
            
        elif goal_type == GoalType.MARRIAGE:
            target_amount = goal_data.details.get("target_amount", 1500000) if goal_data.details else 1500000
            years_to_save = goal_data.details.get("years_to_save", 3) if goal_data.details else 3
            
            # Simple SIP calculation for marriage
            from .calculators import calculate_vacation_fund  # Reuse logic
            result = {
                "target_amount": target_amount,
                "years_to_goal": years_to_save,
                "monthly_sip": int(target_amount / (years_to_save * 12 * 1.08)),  # Rough estimate with 8% returns
                "return_rate": 0.08
            }
        else:
            # Generic goal
            target_amount = goal_data.details.get("target_amount", 500000) if goal_data.details else 500000
            years_to_goal = goal_data.details.get("years_to_goal", 5) if goal_data.details else 5
            
            result = {
                "target_amount": target_amount,
                "years_to_goal": years_to_goal,
                "monthly_sip": int(target_amount / (years_to_goal * 12)),
                "return_rate": 0.08
            }
        
        return result
    
    def _get_chart_of_accounts_template(self, profile_type: ProfileType) -> List[Dict[str, Any]]:
        """Generate chart of accounts based on profile type"""
        
        base_accounts = [
            {"code": "1000", "name": "Assets", "type": "asset", "parent": None},
            {"code": "1100", "name": "Current Assets", "type": "asset", "parent": "1000"},
            {"code": "1110", "name": "Cash and Bank", "type": "asset", "parent": "1100"},
            {"code": "1120", "name": "Investments", "type": "asset", "parent": "1100"},
            {"code": "1200", "name": "Fixed Assets", "type": "asset", "parent": "1000"},
            
            {"code": "2000", "name": "Liabilities", "type": "liability", "parent": None},
            {"code": "2100", "name": "Current Liabilities", "type": "liability", "parent": "2000"},
            {"code": "2200", "name": "Long-term Liabilities", "type": "liability", "parent": "2000"},
            
            {"code": "3000", "name": "Equity", "type": "equity", "parent": None},
            {"code": "3100", "name": "Net Worth", "type": "equity", "parent": "3000"},
            
            {"code": "4000", "name": "Income", "type": "income", "parent": None},
            {"code": "5000", "name": "Expenses", "type": "expense", "parent": None},
        ]
        
        # Add profile-specific accounts
        if profile_type == ProfileType.SALARIED_EMPLOYEE:
            base_accounts.extend([
                {"code": "4100", "name": "Salary Income", "type": "income", "parent": "4000"},
                {"code": "5100", "name": "Housing", "type": "expense", "parent": "5000"},
                {"code": "5200", "name": "Transportation", "type": "expense", "parent": "5000"},
                {"code": "5300", "name": "Food & Groceries", "type": "expense", "parent": "5000"},
            ])
        elif profile_type == ProfileType.BUSINESS_OWNER:
            base_accounts.extend([
                {"code": "4100", "name": "Business Revenue", "type": "income", "parent": "4000"},
                {"code": "4200", "name": "Salary/Draw", "type": "income", "parent": "4000"},
                {"code": "5100", "name": "Business Expenses", "type": "expense", "parent": "5000"},
                {"code": "5200", "name": "Personal Expenses", "type": "expense", "parent": "5000"},
            ])
        elif profile_type == ProfileType.EARLY_INVESTOR:
            base_accounts.extend([
                {"code": "4100", "name": "Investment Income", "type": "income", "parent": "4000"},
                {"code": "4200", "name": "Capital Gains", "type": "income", "parent": "4000"},
                {"code": "1130", "name": "Portfolio Investments", "type": "asset", "parent": "1100"},
            ])
        
        return base_accounts

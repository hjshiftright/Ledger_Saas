"""
Onboarding V2 - Goal Calculation Utilities

Financial goal calculation algorithms
"""
from typing import Dict, Any
import math


def calculate_retirement_corpus(
    current_age: int,
    retirement_age: int = 60,
    monthly_expense: int = 50000,
    inflation_rate: float = 0.06,
    return_rate_pre: float = 0.12,
    return_rate_post: float = 0.08,
    life_expectancy: int = 85
) -> Dict[str, Any]:
    """
    Calculate retirement corpus using 25x rule with inflation
    
    Args:
        current_age: User's current age
        retirement_age: Planned retirement age (default: 60)
        monthly_expense: Current monthly expenses (default: ₹50,000)
        inflation_rate: Annual inflation rate (default: 6%)
        return_rate_pre: Return rate before retirement (default: 12%)
        return_rate_post: Return rate after retirement (default: 8%)
        life_expectancy: Expected life expectancy (default: 85)
    
    Returns:
        Dictionary with required_corpus, monthly_sip, future_monthly_expense, etc.
    """
    years_to_retirement = retirement_age - current_age
    years_in_retirement = life_expectancy - retirement_age
    
    if years_to_retirement <= 0:
        raise ValueError("Current age must be less than retirement age")
    
    # Inflate monthly expenses to retirement
    future_monthly_expense = monthly_expense * ((1 + inflation_rate) ** years_to_retirement)
    annual_expense_at_retirement = future_monthly_expense * 12
    
    # 25x rule: corpus = 25 * annual expenses
    required_corpus = annual_expense_at_retirement * 25
    
    # Calculate monthly SIP needed
    # Future Value = P × [((1 + r)^n - 1) / r] × (1 + r)
    r = return_rate_pre / 12  # Monthly return
    n = years_to_retirement * 12  # Months
    
    if r > 0:
        monthly_sip = required_corpus / (((1 + r) ** n - 1) / r * (1 + r))
    else:
        monthly_sip = required_corpus / n
    
    return {
        "required_corpus": int(required_corpus),
        "monthly_sip": int(monthly_sip),
        "future_monthly_expense": int(future_monthly_expense),
        "years_to_retirement": years_to_retirement,
        "years_in_retirement": years_in_retirement,
        "current_monthly_expense": monthly_expense,
        "inflation_rate": inflation_rate,
        "return_rate_pre": return_rate_pre
    }


def calculate_education_corpus(
    child_current_age: int,
    college_age: int = 18,
    current_cost: int = 2500000,  # ₹25L default
    inflation_rate: float = 0.08,  # Education inflation higher
    return_rate: float = 0.12
) -> Dict[str, Any]:
    """
    Calculate education corpus with education inflation
    
    Args:
        child_current_age: Child's current age
        college_age: Age when child goes to college (default: 18)
        current_cost: Current cost of education (default: ₹25L)
        inflation_rate: Education inflation rate (default: 8%)
        return_rate: Investment return rate (default: 12%)
    
    Returns:
        Dictionary with future_cost, monthly_sip, years_to_save
    """
    years_to_college = college_age - child_current_age
    
    if years_to_college <= 0:
        raise ValueError("Child's age must be less than college age")
    
    # Inflate education cost
    future_cost = current_cost * ((1 + inflation_rate) ** years_to_college)
    
    # Calculate monthly SIP
    r = return_rate / 12
    n = years_to_college * 12
    
    if r > 0:
        monthly_sip = future_cost / (((1 + r) ** n - 1) / r * (1 + r))
    else:
        monthly_sip = future_cost / n
    
    return {
        "future_cost": int(future_cost),
        "monthly_sip": int(monthly_sip),
        "years_to_save": years_to_college,
        "current_cost": current_cost,
        "inflation_rate": inflation_rate,
        "return_rate": return_rate
    }


def calculate_home_down_payment(
    property_value: int,
    down_payment_pct: float = 0.20,
    years_to_save: int = 5,
    return_rate: float = 0.08,
    price_appreciation: float = 0.05,
    loan_interest_rate: float = 0.085,  # 8.5%
    loan_tenure_years: int = 20
) -> Dict[str, Any]:
    """
    Calculate down payment savings with property appreciation
    
    Args:
        property_value: Current property value
        down_payment_pct: Down payment percentage (default: 20%)
        years_to_save: Years to save for down payment (default: 5)
        return_rate: Return on savings (default: 8%)
        price_appreciation: Annual property price increase (default: 5%)
        loan_interest_rate: Home loan interest rate (default: 8.5%)
        loan_tenure_years: Loan tenure in years (default: 20)
    
    Returns:
        Dictionary with future property value, down payment, monthly SIP, loan details
    """
    # Inflate property value
    future_property_value = property_value * ((1 + price_appreciation) ** years_to_save)
    down_payment_required = future_property_value * down_payment_pct
    
    # Calculate monthly SIP
    r = return_rate / 12
    n = years_to_save * 12
    
    if r > 0:
        monthly_sip = down_payment_required / (((1 + r) ** n - 1) / r * (1 + r))
    else:
        monthly_sip = down_payment_required / n
    
    # Calculate loan amount and EMI
    loan_amount = future_property_value - down_payment_required
    monthly_emi = calculate_emi(loan_amount, loan_interest_rate, loan_tenure_years)
    
    return {
        "future_property_value": int(future_property_value),
        "current_property_value": property_value,
        "down_payment_required": int(down_payment_required),
        "monthly_sip": int(monthly_sip),
        "loan_amount": int(loan_amount),
        "estimated_emi": int(monthly_emi),
        "years_to_save": years_to_save,
        "loan_tenure_years": loan_tenure_years,
        "loan_interest_rate": loan_interest_rate
    }


def calculate_car_down_payment(
    car_value: int,
    down_payment_pct: float = 0.30,
    years_to_save: int = 2,
    return_rate: float = 0.08,
    loan_interest_rate: float = 0.09,  # 9%
    loan_tenure_years: int = 5
) -> Dict[str, Any]:
    """
    Calculate car down payment savings
    
    Args:
        car_value: Target car value
        down_payment_pct: Down payment percentage (default: 30%)
        years_to_save: Years to save (default: 2)
        return_rate: Return on savings (default: 8%)
        loan_interest_rate: Car loan interest rate (default: 9%)
        loan_tenure_years: Loan tenure (default: 5 years)
    
    Returns:
        Dictionary with down payment, monthly SIP, loan details
    """
    down_payment_required = car_value * down_payment_pct
    
    # Calculate monthly SIP
    r = return_rate / 12
    n = years_to_save * 12
    
    if r > 0:
        monthly_sip = down_payment_required / (((1 + r) ** n - 1) / r * (1 + r))
    else:
        monthly_sip = down_payment_required / n
    
    # Calculate loan amount and EMI
    loan_amount = car_value - down_payment_required
    monthly_emi = calculate_emi(loan_amount, loan_interest_rate, loan_tenure_years)
    
    return {
        "car_value": car_value,
        "down_payment_required": int(down_payment_required),
        "monthly_sip": int(monthly_sip),
        "loan_amount": int(loan_amount),
        "estimated_emi": int(monthly_emi),
        "years_to_save": years_to_save,
        "loan_tenure_years": loan_tenure_years
    }


def calculate_vacation_fund(
    annual_budget: int = 200000,  # ₹2L per year
    special_trip_cost: int = 500000,  # ₹5L special trip
    years_to_special_trip: int = 3,
    return_rate: float = 0.06
) -> Dict[str, Any]:
    """
    Calculate vacation fund savings
    
    Args:
        annual_budget: Annual vacation budget (default: ₹2L)
        special_trip_cost: Special trip cost (default: ₹5L)
        years_to_special_trip: Years to special trip (default: 3)
        return_rate: Return on savings (default: 6%)
    
    Returns:
        Dictionary with monthly savings needed
    """
    # Monthly savings for annual budget
    monthly_for_annual = annual_budget / 12
    
    # Monthly savings for special trip
    r = return_rate / 12
    n = years_to_special_trip * 12
    
    if r > 0:
        monthly_for_special = special_trip_cost / (((1 + r) ** n - 1) / r * (1 + r))
    else:
        monthly_for_special = special_trip_cost / n
    
    total_monthly = monthly_for_annual + monthly_for_special
    
    return {
        "annual_budget": annual_budget,
        "special_trip_cost": special_trip_cost,
        "monthly_sip": int(total_monthly),
        "monthly_for_annual": int(monthly_for_annual),
        "monthly_for_special": int(monthly_for_special),
        "years_to_special_trip": years_to_special_trip
    }


def calculate_emi(
    principal: int,
    annual_rate: float,
    years: int
) -> int:
    """
    Calculate Equated Monthly Installment (EMI) for a loan
    
    Formula: EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
    
    Args:
        principal: Loan amount in rupees
        annual_rate: Annual interest rate as decimal (e.g., 0.085 for 8.5%)
        years: Loan tenure in years
    
    Returns:
        Monthly EMI amount in rupees
    """
    r = annual_rate / 12  # Monthly interest rate
    n = years * 12  # Total number of months
    
    if r > 0:
        emi = principal * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
    else:
        emi = principal / n
    
    return int(emi)


def calculate_goal_feasibility(
    total_monthly_required: int,
    monthly_income_min: int,
    monthly_income_max: int = None
) -> Dict[str, Any]:
    """
    Calculate if goals are achievable based on income
    
    Args:
        total_monthly_required: Total monthly savings required for all goals
        monthly_income_min: Minimum monthly income
        monthly_income_max: Maximum monthly income (optional)
    
    Returns:
        Dictionary with feasibility status, score, and message
    """
    if monthly_income_min <= 0:
        return {
            "status": "unknown",
            "feasibility_score": 0,
            "savings_rate_required": 0,
            "message": "Income information not provided"
        }
    
    savings_rate = total_monthly_required / monthly_income_min
    
    # Determine feasibility
    if savings_rate > 0.7:
        status = "unrealistic"
        score = 30
        message = f"You'd need to save {savings_rate:.0%} of income. This is very difficult to achieve. Consider reducing or extending timelines."
    elif savings_rate > 0.5:
        status = "ambitious"
        score = 60
        message = f"You'd need to save {savings_rate:.0%} of minimum income. Consider prioritizing or extending timelines."
    elif savings_rate > 0.3:
        status = "achievable"
        score = 85
        message = f"Saving {savings_rate:.0%} of income is challenging but achievable with discipline."
    else:
        status = "conservative"
        score = 95
        message = f"Saving {savings_rate:.0%} of income is very achievable. You're on track!"
    
    return {
        "status": status,
        "feasibility_score": score,
        "savings_rate_required": round(savings_rate, 2),
        "monthly_income_min": monthly_income_min,
        "message": message
    }


def get_city_property_price(city: str, property_type: str = "2bhk") -> int:
    """
    Get estimated property prices by city and type
    
    Args:
        city: City name
        property_type: Property type (1bhk, 2bhk, 3bhk)
    
    Returns:
        Estimated property price in rupees
    """
    city_tier_1 = {
        "Mumbai": {"1bhk": 8000000, "2bhk": 15000000, "3bhk": 25000000},
        "Delhi": {"1bhk": 7000000, "2bhk": 12000000, "3bhk": 20000000},
        "Bangalore": {"1bhk": 6000000, "2bhk": 10000000, "3bhk": 16000000},
        "Hyderabad": {"1bhk": 5000000, "2bhk": 8000000, "3bhk": 13000000},
        "Pune": {"1bhk": 5000000, "2bhk": 8000000, "3bhk": 13000000},
        "Chennai": {"1bhk": 4500000, "2bhk": 7500000, "3bhk": 12000000},
    }
    
    city_tier_2 = {
        "1bhk": 3000000,
        "2bhk": 5000000,
        "3bhk": 8000000
    }
    
    city_tier_3 = {
        "1bhk": 2000000,
        "2bhk": 3500000,
        "3bhk": 5500000
    }
    
    # Try tier 1 cities first
    if city in city_tier_1:
        return city_tier_1[city].get(property_type, city_tier_1[city]["2bhk"])
    
    # Default to tier 2 for unknown cities
    return city_tier_2.get(property_type, city_tier_2["2bhk"])


def get_income_range_values(income_range: str) -> Dict[str, int]:
    """
    Get min and max values for income range
    
    Args:
        income_range: Income range code (e.g., "1l_2l")
    
    Returns:
        Dictionary with min and max values in rupees
    """
    ranges = {
        "under_25k": {"min": 0, "max": 25000},
        "25k_50k": {"min": 25000, "max": 50000},
        "50k_75k": {"min": 50000, "max": 75000},
        "75k_1l": {"min": 75000, "max": 100000},
        "1l_2l": {"min": 100000, "max": 200000},
        "2l_5l": {"min": 200000, "max": 500000},
        "5l_10l": {"min": 500000, "max": 1000000},
        "above_10l": {"min": 1000000, "max": 10000000},
    }
    
    return ranges.get(income_range, {"min": 0, "max": 0})

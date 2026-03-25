# Standard financial tree for India.
# Single source of truth — used by both COASetupService (onboarding path) and
# provision-defaults API endpoint.  All codes / names / subtypes must stay in
# sync with coa_categories.py.
DEFAULT_COA = [
    {
        "code": "1000", "name": "Assets",
        "type": "ASSET", "subtype": "OTHER_ASSET", "normal_balance": "DEBIT",
        "is_placeholder": True, "is_system": True, "children": [
            {
                "code": "1100", "name": "Cash & Bank",
                "type": "ASSET", "subtype": "BANK", "normal_balance": "DEBIT",
                "is_placeholder": True, "is_system": True, "children": [
                    {
                        "code": "1101", "name": "Cash in Hand",
                        "type": "ASSET", "subtype": "CASH", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "1102", "name": "Savings Account",
                        "type": "ASSET", "subtype": "BANK", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                ]
            },
            {
                "code": "1200", "name": "Investments",
                "type": "ASSET", "subtype": "INVESTMENT", "normal_balance": "DEBIT",
                "is_placeholder": True, "is_system": True, "children": [
                    {
                        "code": "1201", "name": "Mutual Funds",
                        "type": "ASSET", "subtype": "INVESTMENT", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "1202", "name": "Stocks / Equities",
                        "type": "ASSET", "subtype": "INVESTMENT", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "1203", "name": "Fixed Deposits",
                        "type": "ASSET", "subtype": "FIXED_DEPOSIT", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "1204", "name": "PPF / EPF / NPS",
                        "type": "ASSET", "subtype": "PPF_EPF", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "1210", "name": "Mutual Fund Portfolio",
                        "type": "ASSET", "subtype": "INVESTMENT", "normal_balance": "DEBIT",
                        "is_placeholder": True, "is_system": False, "children": []
                    },
                    {
                        "code": "1220", "name": "Equity Holdings",
                        "type": "ASSET", "subtype": "INVESTMENT", "normal_balance": "DEBIT",
                        "is_placeholder": True, "is_system": False, "children": []
                    },
                    {
                        "code": "1230", "name": "Zerodha Trading Account",
                        "type": "ASSET", "subtype": "BANK", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                ]
            },
            {
                "code": "1300", "name": "Gold",
                "type": "ASSET", "subtype": "GOLD", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "1400", "name": "Real Estate",
                "type": "ASSET", "subtype": "REAL_ESTATE", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
        ]
    },
    {
        "code": "2000", "name": "Liabilities",
        "type": "LIABILITY", "subtype": "OTHER_LOAN", "normal_balance": "CREDIT",
        "is_placeholder": True, "is_system": True, "children": [
            {
                "code": "2100", "name": "Credit Cards",
                "type": "LIABILITY", "subtype": "CREDIT_CARD", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "2200", "name": "Home Loan",
                "type": "LIABILITY", "subtype": "HOME_LOAN", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "2300", "name": "Vehicle Loan",
                "type": "LIABILITY", "subtype": "VEHICLE_LOAN", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "2400", "name": "Personal Loan",
                "type": "LIABILITY", "subtype": "PERSONAL_LOAN", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "2999", "name": "Transfer Clearing",
                "type": "LIABILITY", "subtype": "OTHER_LOAN", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": True, "children": []
            },
        ]
    },
    {
        "code": "3000", "name": "Equity",
        "type": "EQUITY", "subtype": "RETAINED", "normal_balance": "CREDIT",
        "is_placeholder": True, "is_system": True, "children": [
            {
                "code": "3100", "name": "Opening Balances",
                "type": "EQUITY", "subtype": "OPENING_BALANCE", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": True, "children": []
            },
        ]
    },
    {
        "code": "4000", "name": "Income",
        "type": "INCOME", "subtype": "OTHER_INCOME", "normal_balance": "CREDIT",
        "is_placeholder": True, "is_system": True, "children": [
            {
                "code": "4100", "name": "Salary / Wages",
                "type": "INCOME", "subtype": "SALARY", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "4200", "name": "Interest Income",
                "type": "INCOME", "subtype": "INTEREST", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "4300", "name": "Dividend Income",
                "type": "INCOME", "subtype": "DIVIDEND", "normal_balance": "CREDIT",
                "is_placeholder": True, "is_system": False, "children": [
                    {
                        "code": "4301", "name": "Dividend Income - Equity",
                        "type": "INCOME", "subtype": "DIVIDEND", "normal_balance": "CREDIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "4302", "name": "Dividend Income - MF (Payout)",
                        "type": "INCOME", "subtype": "DIVIDEND", "normal_balance": "CREDIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                ]
            },
            {
                "code": "4400", "name": "Capital Gains",
                "type": "INCOME", "subtype": "CAPITAL_GAINS", "normal_balance": "CREDIT",
                "is_placeholder": True, "is_system": False, "children": [
                    {
                        "code": "4401", "name": "Realised Capital Gains - Short Term",
                        "type": "INCOME", "subtype": "CAPITAL_GAINS", "normal_balance": "CREDIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "4402", "name": "Realised Capital Gains - Long Term",
                        "type": "INCOME", "subtype": "CAPITAL_GAINS", "normal_balance": "CREDIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "4403", "name": "Realised P&L - F&O",
                        "type": "INCOME", "subtype": "CAPITAL_GAINS", "normal_balance": "CREDIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                ]
            },
            {
                "code": "4500", "name": "Rental Income",
                "type": "INCOME", "subtype": "RENTAL", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "4900", "name": "Other Income",
                "type": "INCOME", "subtype": "OTHER_INCOME", "normal_balance": "CREDIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
        ]
    },
    {
        "code": "5000", "name": "Expenses",
        "type": "EXPENSE", "subtype": "OTHER_EXPENSE", "normal_balance": "DEBIT",
        "is_placeholder": True, "is_system": True, "children": [
            {
                "code": "5100", "name": "Groceries",
                "type": "EXPENSE", "subtype": "FOOD", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5101", "name": "Dining Out",
                "type": "EXPENSE", "subtype": "FOOD", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5200", "name": "Transportation",
                "type": "EXPENSE", "subtype": "TRANSPORT", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5300", "name": "Housing / Rent",
                "type": "EXPENSE", "subtype": "HOUSING", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5400", "name": "Utilities",
                "type": "EXPENSE", "subtype": "UTILITIES", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5401", "name": "Mobile & Internet",
                "type": "EXPENSE", "subtype": "UTILITIES", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5500", "name": "Healthcare",
                "type": "EXPENSE", "subtype": "HEALTHCARE", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5600", "name": "Education",
                "type": "EXPENSE", "subtype": "EDUCATION", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5700", "name": "Shopping",
                "type": "EXPENSE", "subtype": "SHOPPING", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5800", "name": "Entertainment",
                "type": "EXPENSE", "subtype": "ENTERTAINMENT", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5900", "name": "Insurance Premium",
                "type": "EXPENSE", "subtype": "INSURANCE", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5950", "name": "Taxes Paid",
                "type": "EXPENSE", "subtype": "TAXES", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5999", "name": "Miscellaneous",
                "type": "EXPENSE", "subtype": "OTHER_EXPENSE", "normal_balance": "DEBIT",
                "is_placeholder": False, "is_system": False, "children": []
            },
            {
                "code": "5850", "name": "Investment Expenses",
                "type": "EXPENSE", "subtype": "OTHER_EXPENSE", "normal_balance": "DEBIT",
                "is_placeholder": True, "is_system": False, "children": [
                    {
                        "code": "5851", "name": "Broker Charges & Fees",
                        "type": "EXPENSE", "subtype": "OTHER_EXPENSE", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "5852", "name": "DP Charges / AMC",
                        "type": "EXPENSE", "subtype": "OTHER_EXPENSE", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                    {
                        "code": "5853", "name": "STT / Stamp Duty",
                        "type": "EXPENSE", "subtype": "OTHER_EXPENSE", "normal_balance": "DEBIT",
                        "is_placeholder": False, "is_system": False, "children": []
                    },
                ]
            },
        ]
    },
]


# Ledger 3.0 - User Guide

**Your Personal Finance Management Platform**

A comprehensive guide to help you understand and use Ledger 3.0 for managing your personal finances, tracking investments, and achieving your financial goals.

---

## Table of Contents

1. [Welcome to Ledger 3.0](#welcome-to-ledger-30)
2. [Getting Started](#getting-started)
3. [Understanding the Dashboard](#understanding-the-dashboard)
4. [Core Features](#core-features)
5. [Step-by-Step Processes](#step-by-step-processes)
6. [Advanced Features](#advanced-features)
7. [Tips & Best Practices](#tips--best-practices)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Welcome to Ledger 3.0

Ledger 3.0 is a **privacy-first, desktop finance tracker** designed specifically for Indian investors. It helps you:

- 🏦 **Track all your accounts** - Bank accounts, investments, loans, and credit cards
- 📊 **Manage double-entry bookkeeping** - Professional-grade financial tracking
- 🎯 **Set and achieve financial goals** - Retirement, home purchase, education, and more
- 📈 **Monitor investments** - Mutual funds, stocks, EPF/NPS, and more
- 💰 **Create budgets** - Track spending vs. income
- 🤖 **AI-assisted categorization** - Smart transaction categorization powered by AI

### What Makes Ledger Different?

- **Your data stays on your device** - No cloud uploads, complete privacy
- **Designed for India** - Supports Indian financial instruments, tax rules, and formats
- **Progressive onboarding** - Start simple and add complexity as you need it
- **Professional accounting** - Uses double-entry bookkeeping for accuracy
- **AI-powered insights** - Get help categorizing transactions and understanding your finances

---

## Getting Started

### System Requirements

- **Operating System**: Windows, macOS, or Linux
- **Python**: 3.11 or higher (if running from source)
- **Browser**: Modern web browser (Chrome, Firefox, Safari, Edge) for web interface
- **Storage**: 100MB minimum (grows with your data)

### Installation Options

#### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd Ledger_Saas-new-ui

# Copy environment file and configure
cp .env.example .env
# Edit .env with your settings

# Start the application
docker compose up --build
```

#### Option 2: Local Development Setup

```bash
# Start PostgreSQL database
docker compose up -d db

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run database migrations
cd backend
PYTHONPATH=src alembic upgrade head

# Start the application
cd src
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Accessing the Application

- **Web Interface**: http://localhost:80
- **API Documentation**: http://localhost:8000/docs
- **API Base URL**: http://localhost:8000

---

## Understanding the Dashboard

Your dashboard is your financial cockpit. It gives you a complete overview of your financial health at a glance.

### Main Dashboard Components

#### 1. Net Worth Card
- **What it shows**: Total assets minus total liabilities
- **Why it matters**: Your overall financial position
- **How to use**: Click to see detailed breakdown of assets and liabilities

#### 2. Goals Progress Strip
- **What it shows**: Your financial goals with progress rings
- **Why it matters**: Visual motivation and tracking
- **How to use**: Click any goal to see details and make updates

#### 3. Cash Flow Summary
- **What it shows**: Monthly income vs. expenses
- **Why it matters**: Understand where your money goes
- **How to use**: Click to see detailed cash flow analysis

#### 4. Budget Overview
- **What it shows**: Budget categories with spending vs. limits
- **Why it matters**: Control your spending habits
- **How to use**: Click to adjust budgets or view detailed spending

#### 5. Recent Transactions
- **What it shows**: Latest financial transactions
- **Why it matters**: Keep track of recent activity
- **How to use**: Click to edit, categorize, or view details

#### 6. Next Best Steps
- **What it shows**: Personalized recommendations
- **Why it matters**: Guidance on what to do next
- **How to use**: Follow the suggestions to improve your financial setup

---

## Core Features

### 1. Account Management

#### What You Can Track
- **Bank Accounts**: Savings, current, salary, fixed deposits
- **Investment Accounts**: Mutual funds, stocks, EPF/NPS
- **Credit Cards**: Multiple cards with outstanding balances
- **Loans**: Home loan, vehicle loan, personal loan, education loan
- **Cash**: Physical cash and digital wallets
- **Assets**: Property, gold, vehicles, other valuables

#### How to Add Accounts
1. Go to **Accounts** section
2. Click **"Add Account"**
3. Choose account type
4. Fill in details:
   - Account name/nickname
   - Institution (bank, broker, etc.)
   - Current balance
   - Account type (savings, current, etc.)
5. Click **"Save"**

### 2. Transaction Management

#### Transaction Types
- **Income**: Salary, business income, interest, dividends
- **Expenses**: Groceries, rent, utilities, entertainment
- **Transfers**: Moving money between accounts
- **Investments**: Buying/selling stocks, mutual fund SIPs
- **Loan Payments**: EMIs, credit card payments

#### Adding Transactions
1. Click **"Add Transaction"** from dashboard or Transactions page
2. Fill in transaction details:
   - Date and amount
   - From account (where money came from)
   - To account (where money went)
   - Category and description
   - Tags (optional)
3. Review the double-entry breakdown (automatic)
4. Click **"Save Transaction"**

### 3. Budget Creation

#### Budget Categories
- **Essentials**: Housing, food, transport, utilities
- **Lifestyle**: Entertainment, dining out, shopping
- **Savings & Investments**: SIPs, goal contributions
- **Debt Payments**: EMIs, credit card payments

#### Creating a Budget
1. Go to **Budgets** section
2. Choose **"Auto-generate from cash flow"** (recommended) or **"Build from scratch"**
3. Set limits for each category
4. Allocate surplus to goals or savings
5. Save and start tracking

### 4. Goal Setting

#### Popular Goal Types
- **Emergency Fund**: 3-6 months of expenses
- **Home Purchase**: Down payment saving
- **Retirement**: Retirement corpus target
- **Children's Education**: School/college planning
- **Debt Freedom**: Pay off all loans
- **Major Purchase**: Car, vacation, renovation

#### Setting Up Goals
1. Go to **Goals** section
2. Click **"Add Goal"**
3. Choose goal type or create custom goal
4. Set:
   - Target amount
   - Target date
   - Priority level
   - Linked accounts (optional)
5. Add milestones for large goals
6. Save and start tracking

---

## Step-by-Step Processes

### Process 1: First-Time Setup

#### Step 1: Basic Profile 
1. **Tell us about yourself**
   - Your name and age
   - What you do (salaried, business, etc.)
   - Where you live
   - Family details

#### Step 2: Add What You Own
1. **Bank Accounts**: Add all your bank accounts with current balances
2. **Investments**: Add mutual funds, stocks, EPF/NPS
3. **Cash**: Physical cash and digital wallets
4. **Property & Gold**: Real estate and gold jewelry
5. **Other Assets**: Anything else of value

#### Step 3: Add What You Owe
1. **Credit Cards**: All cards with outstanding balances
2. **Loans**: Home loan, vehicle loan, personal loans
3. **Other Dues**: Any money you owe to others

#### Step 4: Set Your Goals
1. **Choose 1-3 goals** that matter most to you
2. **Set target amounts** and dates
3. **Link accounts** that will fund these goals
4. **Add milestones** for long-term goals

### Process 2: Monthly Financial Review

#### Step 1: Review Cash Flow
1. **Check income vs. expenses** for the month
2. **Identify unusual spending** patterns
3. **Categorize uncategorized transactions**
4. **Note any large expenses** or income changes

#### Step 2: Update Budget Progress
1. **Compare actual spending** vs. budget
2. **Identify categories** over or under budget
3. **Adjust budgets** if needed for next month
4. **Plan for next month's** major expenses

#### Step 3: Track Goal Progress
1. **Check progress** toward each goal
2. **Update contributions** if possible
3. **Celebrate milestones** reached
4. **Adjust timelines** if needed

#### Step 4: Plan Ahead
1. **Note upcoming large expenses**
2. **Plan for irregular income** (bonuses, dividends)
3. **Set priorities** for next month
4. **Schedule any account actions** (investments, payments)

### Process 3: Investment Tracking

#### Step 1: Update Portfolio Values
1. **Current market values** of all investments
2. **Add new investments** made during the quarter
3. **Record any sales** or redemptions
4. **Update dividends** and interest received

#### Step 2: Review Performance
1. **Calculate returns** (XIRR for investments)
2. **Compare against benchmarks**
3. **Analyze asset allocation**
4. **Identify underperformers**

#### Step 3: Rebalance if Needed
1. **Check target allocation** vs. actual
2. **Plan rebalancing** actions
3. **Consider tax implications**
4. **Execute rebalancing** over time

---

## Advanced Features

### 1. Recurring Transactions

#### What It Does
Automatically creates recurring transactions like:
- Monthly salary credit
- SIP investments
- Loan EMIs
- Rent payments
- Insurance premiums

#### Setting Up
1. Go to **Recurring Transactions**
2. Click **"Add Recurring Transaction"**
3. Set:
   - Transaction details (amount, accounts, category)
   - Frequency (monthly, quarterly, yearly)
   - Start date and end date (optional)
   - Next occurrence date
4. Save and the system will auto-create transactions

### 2. Import/Export

#### Import Capabilities
- **Bank Statements**: CSV files from most Indian banks
- **Demat Statements**: CSV from brokers like Zerodha, Groww
- **Mutual Fund Statements**: CAS from CAMS/KFintech
- **Credit Card Statements**: CSV from major card issuers

#### Export Options
- **Transaction History**: CSV with all transactions
- **Account Balances**: Current status snapshot
- **Tax Reports**: Section 80C, capital gains reports
- **Goal Progress**: Detailed goal tracking reports

### 3. AI-Powered Features

#### Smart Categorization
- **Automatic categorization** of transactions based on description
- **Learning from your corrections** to improve accuracy
- **Bulk categorization** of similar transactions

#### Financial Insights
- **Spending pattern analysis**
- **Anomaly detection** for unusual transactions
- **Goal feasibility analysis**
- **Optimization suggestions**

### 4. Tax Planning (Indian Context)

#### Section 80C Tracking
- **EPF/PPF contributions**
- **ELSS mutual funds**
- **Life insurance premiums**
- **Home loan principal**
- **Tuition fees**

#### HRA Exemption Calculator
- **Basic salary calculation**
- **HRA received**
- **Rent paid**
- **Metro/non-metro classification**

#### Capital Gains Reporting
- **LTCG/STCG calculations**
- **FIFO/average cost methods**
- **Tax-loss harvesting opportunities**

---

### Best Practices

#### Data Accuracy
- **Reconcile accounts monthly** with bank statements
- **Keep descriptions consistent** for better categorization
- **Use tags** for custom tracking needs
- **Backup your data** regularly

#### Security
- **Use strong passwords** if you enable authentication
- **Keep your system updated**
- **Backup to encrypted external drive**
- **Be careful with imports** - validate data before importing

#### Goal Setting
- **Start with 1-3 goals** - don't overwhelm yourself
- **Make goals SMART** (Specific, Measurable, Achievable, Relevant, Time-bound)
- **Review and adjust** goals quarterly
- **Celebrate small wins** to stay motivated

#### Budget Management
- **Be realistic** when setting budget limits
- **Include a buffer** category for unexpected expenses
- **Review and adjust** budgets based on actual spending
- **Use the 50/30/20 rule** as a starting point (50% essentials, 30% lifestyle, 20% savings)

---

## Troubleshooting

### Common Issues

#### Transaction Won't Save
**Check:**
- Are both debit and credit accounts selected?
- Is the amount valid?
- Are all required fields filled?
- Is the date format correct?

#### Account Balance Wrong
**Solutions:**
1. **Reconcile with bank statement**
2. **Check for duplicate transactions**
3. **Verify opening balances**
4. **Look for missing transactions**

#### Categories Not Working
**Fixes:**
1. **Check category spelling**
2. **Create missing categories**
3. **Review AI categorization rules**
4. **Bulk edit similar transactions**

#### Import Failed
**Troubleshooting:**
1. **Check file format** (CSV required)
2. **Verify column headers**
3. **Ensure date format matches**
4. **Check for special characters**

#### Performance Issues
**Optimizations:**
1. **Archive old transactions** (if available)
2. **Clear browser cache**
3. **Check system resources**
4. **Restart the application**

### Getting Help

#### Self-Service Resources
- **API Documentation**: http://localhost:8000/docs
- **Error Messages**: Check tooltips and help text
- **Data Validation**: Use the built-in validation features

#### Data Recovery
1. **Check automatic backups** in the data directory
2. **Export current data** before making changes
3. **Use version control** if you're technically comfortable
4. **Contact support** with specific error messages

---

## FAQ

### General Questions

**Q: Is my financial data secure?**
A: Yes! Your data stays on your local device. No cloud uploads, no third-party access. We use industry-standard encryption for data storage.

**Q: Can I use this for business finances?**
A: Ledger 3.0 is designed for personal finance. For business use, you'd need accounting software with business-specific features.

**Q: How accurate are the AI categorizations?**
A: The AI learns from your corrections and typically achieves 80-90% accuracy after a few weeks of use.

**Q: Can I access my data from multiple devices?**
A: Currently, Ledger 3.0 runs on a single device. You can export/import data to sync between devices manually.

### Technical Questions

**Q: What happens if I forget to categorize transactions?**
A: Uncategorized transactions are marked clearly and won't affect your budget analysis. You can categorize them anytime.

**Q: Can I customize the Chart of Accounts?**
A: Yes! You can add, modify, and hide accounts to match your specific needs.

**Q: How does double-entry bookkeeping work here?**
A: Every transaction automatically creates balanced debit and credit entries. You don't need to know accounting - just tell us what happened.

**Q: Can I import data from other finance apps?**
A: Yes, most apps allow CSV export. You can import these files and map the columns to Ledger's format.

### Feature Questions

**Q: Can I track multiple currencies?**
A: Currently, Ledger 3.0 supports single-currency tracking. Multi-currency support is planned for future versions.

**Q: How are investment returns calculated?**
A: We use XIRR (Extended Internal Rate of Return) for accurate time-weighted returns on investments.

**Q: Can I share reports with my family/CA?**
A: Yes, you can export reports in PDF or CSV format and share them as needed.

**Q: Is there a mobile app?**
A: Currently, Ledger 3.0 has a web interface that works on mobile browsers. A dedicated mobile app is under consideration.

---

### Success Indicators
You're using Ledger effectively when you can:
- ✅ Answer "Where did my money go?" for any month
- ✅ Know your exact net worth at any time
- ✅ Track progress toward your financial goals
- ✅ Make informed decisions about spending and saving
- ✅ Feel in control of your financial future

---

## Need More Help?

If you need additional assistance:

1. **Check the API documentation** at http://localhost:8000/docs
2. **Review the error messages** - they often contain helpful hints
3. **Start with the basics** - don't try to use all features at once
4. **Join our community** (if available) for tips from other users
5. **Contact support** with specific questions and error details

Remember: Personal finance is a journey, not a destination. Ledger 3.0 is here to help you every step of the way!

---

**Version**: 1.0  
**Last Updated**: April 2026  
**For Ledger 3.0 Personal Finance Management System**

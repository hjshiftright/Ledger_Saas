# Double-Entry Accounting — A Complete Primer

> Written for developers and non-accountants who need to understand how personal finance
> ledger software works under the hood.
>
> **If you are not comfortable with accounting**, read Sections 1–5 carefully and
> bookmark the Quick Reference Card in Section 11.  Everything else is built on those
> five sections.  You do not need to memorise debits and credits — the software does
> that.  You only need to understand *which account type* each transaction touches so
> you can spot when the software gets it wrong.

---

## 1. The Core Idea

Every financial event touches **exactly two places** simultaneously.
Money never appears from nowhere and never disappears — it always moves *from* somewhere *to* somewhere.

**The fundamental equation that must always hold:**

```
Assets = Liabilities + Equity
```

Or equivalently:

```
What you OWN = What you OWE + What's left for you
```

Double-entry accounting keeps this equation in balance by recording every transaction as a pair:
one **Debit** and one **Credit** of equal value.

---

## 2. The Five Account Types

Everything in your financial life fits into one of five buckets:

| # | Type | What it represents | Normal balance | Real examples |
|---|------|--------------------|----------------|---------------|
| 1 | **Asset** | Things you own or are owed | Debit (DR) | Savings account, cash, investments, home, car |
| 2 | **Liability** | Things you owe others | Credit (CR) | Credit card outstanding, home loan, personal loan |
| 3 | **Equity** | Your net worth (Assets - Liabilities) | Credit (CR) | Opening balance, retained surplus |
| 4 | **Income** | Money that flows to you | Credit (CR) | Salary, interest earned, refunds, cashback, dividends |
| 5 | **Expense** | Money that flows away from you | Debit (DR) | Food, rent, travel, subscriptions, EMIs |

**Normal balance** means the side (DR or CR) that makes the account *increase*.
- Asset & Expense accounts naturally stay on the **left (DR)** side of the ledger.
- Liability, Equity & Income accounts naturally stay on the **right (CR)** side.

### Why does this matter for importing?

When you import a bank statement, every row is either money **coming in** or **going out**.
The software needs to know:
1. What kind of account is the *source* (your bank = Asset, your credit card = Liability)
2. What kind of account is the *counterpart* (where did the money come from or go to?)

That combination determines the exact DR/CR assignment.

---

## 3. Debit and Credit — The Only Rule You Need

### 3a. What DR and CR actually mean

**Debit (DR)** = the LEFT side of an account
**Credit (CR)** = the RIGHT side of an account

That is the complete definition. They are positions — nothing more.

STOP: Forget the everyday meaning of debit and credit.
  Everyday:  "My card was debited" = money left my account.
  Everyday:  "A credit landed in my account" = money arrived.
  Accounting: DR = left.  CR = right.  Full stop.

The everyday meanings vary by whose perspective you are reading from.
The accounting meaning never changes. DR is always left, CR is always right.

### 3b. The T-Account — what a ledger account looks like

Every account is drawn as the letter T. DR entries go on the left column,
CR entries go on the right column:

```
                   Savings Account  (Asset)
              +----------------+----------------+
              |   Debit (DR)   |  Credit (CR)   |
              |    LEFT side   |   RIGHT side   |
              +----------------+----------------+
              |  +80,000 (salary in)            |
              |                |  -5,000 (grocery out) |
              +----------------+----------------+
              Running balance: 75,000 on the DR side
```

Whatever side an account "lives on" — that side INCREASES the account.
The other side DECREASES it.

### 3c. Why the table is exactly what it is — derived from the equation

Everything comes from one equation:

```
  Assets  =  Liabilities  +  Equity
  [LEFT]       [RIGHT]        [RIGHT]
```

The equation places Assets visually on the LEFT and Liabilities + Equity on the RIGHT.
That directly determines which side is the "home" (increasing) side for each account type:

```
  Account     Side of equation   Home side   DR effect    CR effect
  -------     ----------------   ---------   ---------    ---------
  Asset       LEFT               DR          INCREASES    decreases
  Liability   RIGHT              CR          decreases    INCREASES
  Equity      RIGHT              CR          decreases    INCREASES
```

Income and Expense connect to Equity indirectly:

```
  Income  -> makes you RICHER  -> increases Equity  -> same home side as Equity  -> CR
  Expense -> makes you POORER  -> decreases Equity  -> opposite side from Equity -> DR
```

Putting it all together — the table now makes sense because you can derive it:

```
                  +-------------+-------------+  Why
  ----------------+-------------+-------------+  ---------------------------------
  Asset           |  INCREASES  |  decreases  |  lives on LEFT  of equation
  Liability       |  decreases  |  INCREASES  |  lives on RIGHT of equation
  Equity          |  decreases  |  INCREASES  |  lives on RIGHT of equation
  Income          |  decreases  |  INCREASES  |  increases Equity (RIGHT)
  Expense         |  INCREASES  |  decreases  |  decreases Equity (opposite=LEFT)
  ----------------+-------------+-------------+
```

You never have to memorise this table if you remember the equation.

### 3d. Prove it yourself — step-by-step for one transaction

**Event:** Salary of Rs.80,000 arrives in your savings account.

Step 1 — Which two accounts are touched?
  A) Savings Account (Asset)  — bank balance goes UP
  B) Salary Income   (Income) — income goes UP

Step 2 — Look up the home side for each account type:
  A) Asset  increases -> DR   (lives on LEFT of equation)
  B) Income increases -> CR   (same side as Equity = RIGHT)

Step 3 — Write the journal entry:
```
  DR  1102  Savings Account    80,000      <- Asset increases = DR
  CR  4100  Salary Income      80,000      <- Income increases = CR
  ------------------------------
  Sum of DR = Sum of CR = 80,000   BALANCED
```

Step 4 — Verify the accounting equation still holds:
```
  Asset +80,000   Equity +80,000 (via Income)
  Both sides grew by the same amount -> equation still holds
```

Try another: **Grocery Rs.1,200 paid from savings**

  A) Savings Account (Asset)     — bank balance goes DOWN
  B) Food & Grocery  (Expense)   — expense goes UP

  A) Asset  decreases -> CR   (opposite of home side)
  B) Expense increases -> DR  (expense lives on LEFT)
```
  DR  5100  Food & Grocery     1,200       <- Expense increases = DR
  CR  1102  Savings Account    1,200       <- Asset decreases = CR
  BALANCED
```

### 3e. The one-line memory aid

> **DEAL:**  Dividends / Expenses / Assets / Losses  ->  DR increases
> Everything else (Liabilities, Equity, Income, Gains) -> CR increases

(Or just re-derive from the equation. Takes 10 seconds.)

### The Golden Rule of Double Entry

> **For every transaction, the total of all Debit amounts MUST equal the total of all Credit amounts.**

If your journal entry does not balance, it is wrong. Period.

---

## 4. Reading Your Bank Statement vs. Your Books

This is where most people get confused.

Your **bank statement** shows transactions from the *bank's perspective*:
- CR on your statement = the bank owes YOU more money (your balance went up)
- DR on your statement = the bank owes YOU less money (your balance went down)

Your **personal ledger** is from *your perspective*:
- Your savings account is an **Asset** that you own
- When money arrives -> your Asset increases -> **DR your savings account**
- When money leaves -> your Asset decreases -> **CR your savings account**

```
Bank says "CR Rs.10,000"  ->  Your books: DR Savings Rs.10,000
Bank says "DR Rs.5,000"   ->  Your books: CR Savings Rs.5,000
```

The sign is flipped. This trips up everyone the first time.

### The same flip applies to credit cards — in reverse again

Your **credit card statement** also shows the bank's perspective:
- CR on CC statement = your outstanding balance went *down* (payment or refund)
- DR on CC statement = your outstanding balance went *up* (you spent)

Your **personal ledger** for a credit card (a Liability):
- When you spend -> your Liability increases -> **CR your CC account**
- When you pay -> your Liability decreases -> **DR your CC account**

So:
```
CC statement says "DR Rs.2,500" (purchase) -> Your books: CR CC Payable Rs.2,500
CC statement says "CR Rs.15,000" (payment) -> Your books: DR CC Payable Rs.15,000
```

---

## 5. All 25 Possible Transaction Combinations

Every transaction moves value from one account type to another. There are 5 account types,
giving 5x5 = 25 combinations. Not all make real-world sense, but all are shown for
completeness.

The notation is: **`Source Account -> Counterpart Account`**

### 5A. Source = Asset (e.g. your savings bank account)

| # | Combination | What happens in real life | DR | CR |
|---|-------------|---------------------------|----|----|
| 1 | Asset -> Asset | Buy investment / ATM withdrawal / transfer between own accounts | New Asset (investment/cash) | Bank Acct |
| 2 | Asset -> Liability | Repay a loan / pay credit card bill | Loan/CC Payable | Bank Acct |
| 3 | Asset -> Equity | Withdrawal toward personal equity / opening balance post | Equity Acct | Bank Acct |
| 4 | Asset -> Income | *Rare: bank reverses money back into bank from income source* | Bank Acct | Income |
| 5 | Asset -> Expense | Normal bank spend (food, rent, utilities, travel) | Expense Acct | Bank Acct |

Most bank statement rows fall into **1, 2, or 5**.

### 5B. Source = Liability (e.g. your credit card)

| # | Combination | What happens in real life | DR | CR |
|---|-------------|---------------------------|----|----|
| 6 | Liability -> Asset | Pay off liability using another asset (unusual: brokerage paying card) | CC Payable | Investment Acct |
| 7 | Liability -> Liability | Transfer between two credit cards / balance transfer | Old CC Payable | New CC Payable |
| 8 | Liability -> Equity | *Extremely rare personal finance scenario* | CC Payable | Equity |
| 9 | Liability -> Income | CC refund / cashback credited to card | CC Payable | Income/Cashback |
| 10 | Liability -> Expense | Normal CC purchase (food, travel, shopping) | Expense Acct | CC Payable |

Most CC statement rows fall into **9 or 10**.

### 5C. Source = Income (you receive income)

| # | Combination | What happens in real life | DR | CR |
|---|-------------|---------------------------|----|----|
| 11 | Income -> Asset | Salary/interest/dividend credited to savings | Bank/Investment | Income |
| 12 | Income -> Liability | Income credited directly to CC (rare: salary credited to card) | CC Payable | Income |
| 13 | Income -> Equity | Annual profit transferred to equity / retained earnings | Equity | -- |
| 14 | Income -> Income | Reclassification / correction between income accounts | Income Acct A | Income Acct B |
| 15 | Income -> Expense | *Not a real transaction — income offset against expense directly* | Expense | Income |

In practice: **11** is the dominant pattern for bank imports.

### 5D. Source = Expense (you incur an expense)

| # | Combination | What happens in real life | DR | CR |
|---|-------------|---------------------------|----|----|
| 16 | Expense -> Asset | Expense paid from bank (see 5A row 5, same entry from expense side) | Expense | Bank Acct |
| 17 | Expense -> Liability | Expense charged to CC (see 5B row 10, same entry from expense side) | Expense | CC Payable |
| 18 | Expense -> Equity | Expense paid from owner's capital / adjustment | Expense | Equity |
| 19 | Expense -> Income | *Not real — contra entries are rare in personal finance* | Income | Expense |
| 20 | Expense -> Expense | Reclassify expense (e.g. move from Misc to Food) | Correct Expense | Wrong Expense |

### 5E. Source = Equity

| # | Combination | What happens in real life | DR | CR |
|---|-------------|---------------------------|----|----|
| 21 | Equity -> Asset | Opening balance entry / capital injection | Bank Acct | Opening Equity |
| 22 | Equity -> Liability | Opening balance of a loan | Loan Payable | Opening Equity |
| 23 | Equity -> Equity | Transfer between equity accounts / retained earnings | Equity A | Equity B |
| 24 | Equity -> Income | Reverse year-end close (rare adjustment) | Equity | Income |
| 25 | Equity -> Expense | Allocate equity to expense budget (unusual) | Expense | Equity |

**Most personal finance imports cover only 6 combinations:**
`Asset->Expense, Asset->Income, Asset->Asset (invest/transfer), Asset->Liability (loan pay),
Liability->Expense (CC purchase), Liability->Income (CC refund/cashback)`

---

## 6. Worked Examples

### Example A — Salary credited to savings

**Event:** Employer credits Rs.80,000 salary to your HDFC savings account.

```
DR  1102  Savings Account (Asset)     Rs.80,000   <- your bank balance went UP
CR  4100  Salary Income (Income)      Rs.80,000   <- it came from your salary
```

Combination: **Income -> Asset** (row 11 in the table above)

Why?
- Savings Account is an Asset -> DR = increase (correct)
- Salary is Income -> CR = increase (correct)

---

### Example B — Grocery purchase via UPI

**Event:** You pay Rs.1,200 at a supermarket via UPI from your savings account.

```
DR  5100  Food & Grocery (Expense)    Rs.1,200    <- you spent money on food
CR  1102  Savings Account (Asset)     Rs.1,200    <- your bank balance went DOWN
```

Combination: **Asset -> Expense** (row 5 / same as row 16)

Why?
- Food is an Expense -> DR = increase (you incurred more expense)
- Savings Account is an Asset -> CR = decrease (you have less money)

---

### Example C — IRCTC ticket cancellation refund

**Event:** IRCTC refunds Rs.1,259.05 for a cancelled train ticket back to your savings.

```
DR  1102  Savings Account (Asset)     Rs.1,259.05   <- money came back to your bank
CR  4600  Refunds Received (Income)   Rs.1,259.05   <- it came from a refund
```

Combination: **Income -> Asset** (same as salary, but different income account)

**What the system was doing wrong:**
```
DR  1102  Savings Account             Rs.1,259.05   <- correct
CR  4100  Salary / Wages              Rs.1,259.05   <- WRONG — this is not salary
```

Why a different income account matters:
Salary income is taxable differently from a refund. A refund merely cancels a previous
expense — it should not inflate your taxable salary figure.

---

### Example D — Credit card cashback

**Event:** Your credit card company gives Rs.500 cashback reward to your account.

```
DR  1102  Savings Account (Asset)     Rs.500    <- money in bank
CR  4700  Cashback Income (Income)    Rs.500    <- it's a reward, not a refund
```

Or if cashback is credited directly on the CC (reduces outstanding):

```
DR  2100  Credit Card Payable (Liability)   Rs.500    <- outstanding reduced
CR  4700  Cashback Income (Income)          Rs.500    <- reward earned
```

Combination: **Liability -> Income** (row 9 in the table)

Why a separate account from refunds?
Refund = reverses a specific past expense you paid.
Cashback = new money earned as a reward — not tied to a specific expense reversal.
Keeping them separate lets you report them independently at tax time.

---

### Example E — Credit card payment from savings

**Event:** You pay Rs.15,000 to clear your credit card bill from your savings account.

```
DR  2100  Credit Card Payable (Liability)   Rs.15,000   <- you owe LESS to the card company
CR  1102  Savings Account (Asset)           Rs.15,000   <- your bank balance went DOWN
```

Combination: **Asset -> Liability** (row 2)

Why?
- Credit card outstanding is a Liability -> DR = decrease (you paid it off)
- Savings is an Asset -> CR = decrease (money left your account)

Note: the expenses were already recorded when you *swiped the card*, not when you pay the bill.

---

### Example F — Credit card purchase (swipe)

**Event:** You buy a Rs.3,000 flight on your credit card (not yet paid).

```
DR  5200  Travel Expense (Expense)          Rs.3,000   <- you incurred travel cost
CR  2100  Credit Card Payable (Liability)   Rs.3,000   <- you now owe the card company
```

Combination: **Liability -> Expense** (row 10)

Why?
- Travel is an Expense -> DR = increase
- Credit Card Payable is a Liability -> CR = increase (you owe more)

---

### Example G — EMI deducted for home loan

**Event:** Rs.25,000 EMI auto-debited from savings. Assume Rs.18,000 is principal, Rs.7,000 is interest.

```
DR  2200  Home Loan Payable (Liability)    Rs.18,000   <- principal reduces your debt
DR  5600  Loan Interest (Expense)          Rs.7,000    <- interest is a cost
CR  1102  Savings Account (Asset)          Rs.25,000   <- total money left your account
```

Combination: Split — **Asset -> Liability** + **Asset -> Expense** in one entry

Why split? Principal repayment reduces a liability (not an expense). Interest is a pure expense.
Most people treat the whole EMI as expense — that's incorrect accounting.

---

### Example H — Investment purchase (mutual fund)

**Event:** You buy Rs.50,000 of a mutual fund from your savings.

```
DR  1200  Mutual Fund Portfolio (Asset)    Rs.50,000   <- you now own units
CR  1102  Savings Account (Asset)          Rs.50,000   <- cash left your bank
```

Combination: **Asset -> Asset** (row 1)

Why two Assets? You didn't spend it — you converted one asset (cash) to another (investment).
No Income or Expense is touched. Net worth stays the same.

---

### Example I — Opening balance entry

**Event:** You set up the system for the first time. Your savings account has Rs.1,00,000.

```
DR  1102  Savings Account (Asset)    Rs.1,00,000   <- you own this money
CR  3001  Opening Balance (Equity)   Rs.1,00,000   <- it is your starting equity
```

Combination: **Equity -> Asset** (row 21)

---

### Example J — Transfer between own bank accounts

**Event:** You transfer Rs.10,000 from HDFC savings to ICICI savings.

```
Step 1 — money leaves HDFC:
  DR  2999  Transfer Clearing        Rs.10,000   <- suspense
  CR  1102  HDFC Savings             Rs.10,000   <- HDFC balance down

Step 2 — money arrives at ICICI:
  DR  1103  ICICI Savings            Rs.10,000   <- ICICI balance up
  CR  2999  Transfer Clearing        Rs.10,000   <- suspense clears to zero
```

Combination: **Asset -> Asset** via a clearing bridge

Why the clearing account?
Both transactions may appear in different statements on different dates.
The clearing account bridges the gap and confirms the transfer completed.

---

## 7. Credit Cards — The Complete Picture

Credit cards are the most confusing part of personal accounting because they involve a **Liability** account, and statements use DR/CR from the bank's perspective, not yours.

### 7a. What the credit card account represents

Your credit card outstanding is a **Liability** (code 2100).
- When you spend on the card -> your liability **increases** -> CR 2100
- When you pay the bill -> your liability **decreases** -> DR 2100
- When you receive a refund on card -> your liability **decreases** -> DR 2100

### 7b. The two-statement problem

When you pay your credit card bill, the event touches **two statements**:

| Statement | What it shows | Entry on that statement |
|---|---|---|
| Bank statement (HDFC savings) | Debit — money left the bank | CR 1102 Savings |
| CC statement (HDFC CC) | Credit — bill was settled | DR 2100 CC Payable |

This is why both legs use **Transfer Clearing (2999)** as the bridge:

```
From bank statement (import bank.csv):
  DR  2999  Transfer Clearing       Rs.15,000   <- payment leaves bank
  CR  1102  Savings Account         Rs.15,000   <- savings decreases

From CC statement (import cc.csv):
  DR  2100  Credit Card Payable     Rs.15,000   <- liability decreases
  CR  2999  Transfer Clearing       Rs.15,000   <- clears the bridge entry
```

### 7c. All four credit card transaction types

**Type 1 — Purchase on card (appears as DEBIT on CC statement)**

```
DR  5100  Food & Grocery (Expense)          Rs.2,500   <- expense incurred
CR  2100  Credit Card Payable (Liability)   Rs.2,500   <- you owe more
```

**Type 2 — Bill payment from bank (appears as DEBIT on bank statement, CREDIT on CC statement)**

*Bank statement entry:*
```
DR  2999  Transfer Clearing            Rs.15,000   <- outgoing payment
CR  1102  Savings Account (Asset)      Rs.15,000   <- savings decreased
```

*CC statement entry:*
```
DR  2100  Credit Card Payable          Rs.15,000   <- liability reduced
CR  2999  Transfer Clearing            Rs.15,000   <- other leg
```

**Type 3 — Merchant refund on card (appears as CREDIT on CC statement)**

```
DR  2100  Credit Card Payable (Liability)   Rs.1,800   <- liability reduced
CR  4600  Refunds Received (Income)         Rs.1,800   <- refund received
```

**Type 4 — Cashback credited on card (appears as CREDIT on CC statement)**

```
DR  2100  Credit Card Payable (Liability)   Rs.500   <- liability reduced
CR  4700  Cashback Income (Income)          Rs.500   <- reward earned
```

### 7d. Importing CC statements with the CLI

Use `--account-type CREDIT_CARD` so the system knows the source account is a Liability (2100):

```bash
# Import bank statement (auto-detected)
python cli.py import hdfc_jan2026.csv --account-id HDFC-SAV

# Import credit card statement
python cli.py import hdfc_cc_jan2026.csv --account-id HDFC-CC --account-type CREDIT_CARD
```

### 7e. The key insight: direction is symmetric

Whether the source account is a **Bank (Asset)** or **Credit Card (Liability)**, the journal entry logic is the same formula:

```
is_debit = True  (something happened that costs you / increases liability):
    CR source_account / DR counterpart

is_debit = False (something came back to you / reduces liability):
    DR source_account / CR counterpart
```

| Scenario | is_debit | Source account | Effect on source |
|---|---|---|---|
| Bank purchase | True | 1102 Savings (Asset) | CR -> asset decreases |
| CC purchase | True | 2100 CC (Liability) | CR -> liability increases |
| Bank credit/income | False | 1102 Savings (Asset) | DR -> asset increases |
| CC refund/payment | False | 2100 CC (Liability) | DR -> liability decreases |

---

## 8. How Source Type Tells Us the Account Type

A key insight: **the SourceType (which parser was used) tells us the account type of the source account automatically.**

This is the foundation of the source-aware journal generation system:

```
Source Type                     -> Account Type  -> CoA Code  -> Account Name
------------------------------------------------------------------------
HDFC_BANK, ICICI_BANK, ...      -> ASSET         -> 1102       Savings Account
HDFC_BANK_CSV, SBI_BANK_CSV,... -> ASSET         -> 1102       Savings Account
ZERODHA_HOLDINGS, CAS_CAMS,...  -> ASSET         -> 1200       Investments
HDFC_CC, AXIS_CC, SBI_CC,...    -> LIABILITY     -> 2100       Credit Card Payable
HOME_LOAN, CAR_LOAN,...         -> LIABILITY     -> 2200       Loan Payable
ZERODHA_TRADEBOOK               -> ASSET         -> 1201       Equity Portfolio
```

Once we know the source account type, the counterpart (the other leg of the entry)
can be inferred from the category:

```python
COUNTERPART_BY_CATEGORY = {
    # Income -> source DR, counterpart CR
    "INCOME_SALARY":   ("4100", "Salary / Wages"),
    "INCOME_INTEREST": ("4200", "Interest Income"),
    "INCOME_REFUND":   ("4600", "Refunds Received"),
    "INCOME_CASHBACK": ("4700", "Cashback Income"),

    # Expense -> source CR, counterpart DR
    "EXPENSE_FOOD":      ("5100", "Dining Out"),
    "EXPENSE_TRANSPORT": ("5200", "Transportation"),

    # Asset <-> Asset
    "INVESTMENT": ("1200", "Investments"),
    "TRANSFER":   ("2999", "Transfer Clearing"),

    # Asset -> Liability (repayment)
    "CC_PAYMENT": ("2999", "Transfer Clearing"),
    "LOAN_REPAY": ("2200", "Loan Payable"),
}
```

### How categorize_service uses SourceType (Stage 0)

For structured statement types the `txn_type_hint` set by the parser already encodes what the
transaction is. No regex matching is needed:

```
SourceType              txn_type_hint   -> category
---------------------------------------------------------
ZERODHA_TRADEBOOK       PURCHASE (BUY)  -> INVESTMENT
ZERODHA_TRADEBOOK       REDEMPTION(SELL)-> INCOME_CAPITAL_GAINS
ZERODHA_TAX_PNL         any             -> INCOME_CAPITAL_GAINS
ZERODHA_CAPITAL_GAINS   any             -> INCOME_CAPITAL_GAINS
CAS_CAMS / KFINTECH     PURCHASE / SIP  -> INVESTMENT
CAS_CAMS / KFINTECH     DIVIDEND_PAYOUT -> INCOME_DIVIDEND
CAS_CAMS / KFINTECH     REDEMPTION      -> INVESTMENT
```

For bank statements (HDFC, SBI, ICICI, etc.) there is no entry in `_SOURCE_TYPE_CATEGORIES`,
so they fall through to the existing narration regex rules.

---

## 9. The Chart of Accounts (CoA)

A CoA is just a numbered list of all your accounts. The numbering convention used in this project:

```
1000-1999   Assets
  1100        Bank Accounts
    1101        Cash in Hand
    1102        Savings Account (default bank import)
    1103        ICICI Savings
  1200        Investments
    1201        Equity Portfolio (Zerodha)
    1202        Mutual Funds (CAS)
    1203        Fixed Deposits

2000-2999   Liabilities
  2100        Credit Card Payable (default CC import)
    2101        HDFC Credit Card
  2200        Loans
    2201        Home Loan
    2202        Car Loan
  2999        Transfer Clearing (suspense / bridge account)

3000-3999   Equity
  3001        Opening Balance

4000-4999   Income
  4100        Salary / Wages
  4200        Interest Earned
  4300        Dividend Income
  4400        Capital Gains
  4600        Refunds Received
  4700        Cashback Income
  4900        Other Income

5000-5999   Expenses
  5100        Food & Dining
  5200        Transportation
  5300        Housing / Rent
  5400        Utilities
  5500        Healthcare
  5600        Loan Interest
  5700        Shopping
  5800        Entertainment
  5900        Insurance Premium
  5999        Miscellaneous
```

---

## 10. Why Direction Matters for Reporting

At the end of the year, you run reports:

**Income Statement (Profit & Loss):**
```
Total Income   =  sum of all CR balances in Income accounts
Total Expenses =  sum of all DR balances in Expense accounts
Net Surplus    =  Total Income - Total Expenses
```

**Balance Sheet:**
```
Assets      =  sum of all DR balances in Asset accounts
Liabilities =  sum of all CR balances in Liability accounts
Equity      =  Assets - Liabilities
```

If a single transaction is posted to the wrong account or wrong direction, every report downstream is wrong. This is why the IRCTC entry being mapped to Salary is a problem — it inflates your salary income and hides your refund income.

---

## 11. Quick Reference Card

```
+----------------------------+--------------------+----------------+
|  TRANSACTION TYPE          |  DR                |  CR            |
+----------------------------+--------------------+----------------+
|  -- BANK ACCOUNT --        |                    |                |
|  Money arrives in bank     |  Savings Account   |  Income source |
|  Money leaves bank         |  Expense           |  Savings Acct  |
|  Buy investment            |  Investment Acct   |  Savings Acct  |
|  Receive refund to bank    |  Savings Account   |  Refunds Recvd |
|  Receive cashback to bank  |  Savings Account   |  Cashback Inc  |
|  Pay credit card bill      |  Transfer Clearing |  Savings Acct  |
|  Loan EMI - principal      |  Loan Payable      |  Savings Acct  |
|  Loan EMI - interest       |  Loan Interest Exp |  Savings Acct  |
|  Transfer out              |  Transfer Clearing |  Source Acct   |
|  ATM withdrawal            |  Cash in Hand      |  Savings Acct  |
+----------------------------+--------------------+----------------+
|  -- CREDIT CARD --         |                    |                |
|  Purchase on card          |  Expense           |  CC Payable    |
|  Bill payment (CC stmt)    |  CC Payable        |  Transfer Clrg |
|  Merchant refund on card   |  CC Payable        |  Refunds Recvd |
|  Cashback on card          |  CC Payable        |  Cashback Inc  |
+----------------------------+--------------------+----------------+
|  -- INVESTMENTS --         |                    |                |
|  Buy MF units/stocks       |  Investment Acct   |  Savings Acct  |
|  Sell MF units/stocks      |  Savings Acct      |  Investment    |
|  Dividend received         |  Savings Acct      |  Dividend Inc  |
|  Capital gain from sale    |  Savings Acct      |  Capital Gains |
+----------------------------+--------------------+----------------+
```

---

## 12. Common Mistakes and How to Fix Them

| Mistake | What you see | Why it's wrong | Correct fix |
|---------|-------------|----------------|-------------|
| Refund mapped to Salary | Salary income is inflated | Refund != wages | Use `INCOME_REFUND` -> 4600 |
| CC payment recorded as expense | Expense is double-counted | Payment != expense (expense was on swipe) | Use `CC_PAYMENT` -> 2999 |
| Transfer recorded as income | Income is inflated | Moving money between your own accounts | Use `TRANSFER` -> 2999 |
| ATM withdrawal as expense | Expense inflated by cash carries | Cash isn't spent yet | Use `CASH_WITHDRAWAL` -> 1101 Cash in Hand |
| EMI full amount as expense | Expense inflated; debt not reduced | Principal reduces liability | Split: principal -> 2200, interest -> 5600 |
| Investment as expense | Expenses hugely overstated | You still own the asset | Use `INVESTMENT` -> 1200 |

---

## 13. Status in Ledger 3.0

### Done

1. **DR/CR direction** — `proposal_service.py` uses the account-class table directly (ASSET/EXPENSE = DR-normal; LIABILITY/EQUITY/INCOME = CR-normal). See Section 3c.
2. **Refund account** — `4600 Refunds Received` in CoA; `INCOME_REFUND` category auto-detected.
3. **Cashback account** — `4700 Cashback Income`; `INCOME_CASHBACK` detected from keywords.
4. **Credit card support** — `--account-type CREDIT_CARD` sets source to `2100 Credit Card Payable`.
5. **CC_PAYMENT category** — maps to Transfer Clearing (2999).
6. **Source-type -> account-type mapper** — `core/models/source_map.py` derives the correct source account automatically from the parsed SourceType; no manual flags needed for known sources.
7. **Source-type-aware categorization** — `categorize_service.py` Stage 0 uses SourceType + txn_type_hint to categorize Zerodha and CAS transactions without narration regex.
8. **Multi-stage staged pipeline** — `pipeline parse -> analyze -> propose -> commit`.

### Pending

1. **Loan EMI split** — auto-splitting principal vs. interest from EMI narration.
2. **CC statement parsers** — dedicated parsers for HDFC CC, SBI Card, Axis CC statement formats.
3. **Investment parsers** — full MF/stock parsers with capital gains calculation.



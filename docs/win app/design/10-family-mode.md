# Ledger Desktop — Family Mode Design

**Version:** 1.0  
**Status:** Design Review

---

## 1. Overview

Family Mode is a **v2 feature** that lets the primary user track net worth, accounts, and transactions for every member of their household — spouse, children, parents, or any other dependent. The v1 schema is pre-extended to support family mode with zero future migration effort.

**Core idea:** Every financial entity in the database carries a nullable `FamilyMemberId`. In v1, this is always `1` (Self). In v2, this column meaningfully separates each family member's data.

---

## 2. Family Member Entity

### 2.1 Data Model

```sql
CREATE TABLE family_members (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name        TEXT    NOT NULL,
    relationship        TEXT    NOT NULL,  -- Self|Spouse|Child|Parent|Sibling|Other
    dob_encrypted       TEXT,              -- AES-256-GCM encrypted
    pan_encrypted       TEXT,              -- AES-256-GCM encrypted
    mobile_encrypted    TEXT,              -- AES-256-GCM encrypted
    avatar_color        TEXT    DEFAULT '#6C5CE7',
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT
);

-- Seed at install (migration 0000)
INSERT INTO family_members (id, display_name, relationship)
VALUES (1, 'Me', 'Self');
```

### 2.2 Nullable FK on All Core Tables

```sql
-- On every core entity — part of migration 0001
ALTER TABLE accounts           ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);
ALTER TABLE bank_accounts      ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);
ALTER TABLE credit_cards       ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);
ALTER TABLE transactions       ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);
ALTER TABLE file_registry      ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);
ALTER TABLE budgets             ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);
ALTER TABLE goals               ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);
ALTER TABLE net_worth_history   ADD COLUMN family_member_id INTEGER REFERENCES family_members(id);
```

**In v1:** All queries implicitly filter `WHERE family_member_id = 1 OR family_member_id IS NULL`.  
**In v2:** `family_mode_enabled = true` unlocks full family queries.

---

## 3. Family Mode Enable Flow

### 3.1 AppSettings Flag

```
key:   family_mode_enabled
value: false              (v1 default)
```

**Enable Family Mode (v2):**
```
Settings → Family → "Enable Family Mode"
    └─ Confirmation dialog:
       "This lets you add family members and track their accounts
        and finances separately. All your existing data will remain
        yours (Member: Self). Ready?"
       [Enable Family Mode]

→ PATCH /settings  { family_mode_enabled: true }
→ App re-reads settings → family UI features unlock
```

### 3.2 What Unlocks

| Feature | v1 (disabled) | v2 (enabled) |
|---|---|---|
| "Family" tab in nav | Hidden | Visible |
| "Family View" toggle on Dashboard | Hidden | Visible |
| `Family/{Name}/` LedgerDrive subfolders | Not watched | Watched + auto-attributed |
| Family member management | Not available | Full CRUD |
| `?memberId=all` on reports | Returns 501 | Returns consolidated view |
| Per-member reports and filtering | Not available | Available |
| Family-aware toast notifications | Silent | "Priya's file needs..." |

---

## 4. Adding Family Members

### 4.1 UI Flow

```
Settings → Family → [+ Add Member]
┌──────────────────────────────────────────────────────┐
│ Add Family Member                                    │
├──────────────────────────────────────────────────────┤
│ Name *          [Priya Kumar              ]           │
│ Relationship *  [Spouse ▼]                           │
│ Date of Birth   [DD/MM/YYYY              ]           │
│ PAN Number      [                        ]           │
│ Mobile Number   [                        ]           │
│                                                      │
│ 🔒 DOB, PAN, and mobile are stored using the same   │
│    encryption as your own profile. They are used     │
│    to auto-unlock Priya's encrypted PDF statements.  │
│                                                      │
│ Avatar Color    [● Change]                           │
│                                                      │
│ [Cancel]                              [Add Member]   │
└──────────────────────────────────────────────────────┘
```

### 4.2 API

```
POST /family/members
{
  "displayName": "Priya Kumar",
  "relationship": "Spouse",
  "dateOfBirth": "1988-11-23",
  "panNumber": "PQRST9876Z",
  "mobileNumber": "9123456789",
  "avatarColor": "#E17055"
}

→ 201 { "id": 2, "displayName": "Priya Kumar", "relationship": "Spouse" }
```

---

## 5. LedgerDrive Folder Attribution

### 5.1 Folder Structure

```
C:\Users\Ravi\LedgerDrive\
├── HDFC_Jan_2025.pdf              ← Attributed to Self (id=1)
├── ICICI_salary_jan.pdf           ← Attributed to Self
├── Family\
│   ├── Priya\
│   │   ├── priya_sbi_dec.pdf      ← Attributed to Priya (id=2)
│   │   └── priya_credit_card.pdf  ← Attributed to Priya (id=2)
│   ├── Arjun\
│   │   └── arjun_ppf_statement.pdf ← Attributed to Arjun (id=3)
│   └── Mom\
│       └── mom_pension.pdf         ← Attributed to Mom (id=4)
└── .vault\                        ← Hidden, all originals
```

### 5.2 FileWatcher Setup

```csharp
// FileWatcherService.cs (v2 extension)
// Called when family_mode_enabled = true and LedgerDrive is initialized

var familyRoot = Path.Combine(ledgerDrivePath, "Family");
Directory.CreateDirectory(familyRoot);

// For each active family member, ensure folder exists
foreach (var member in await _db.FamilyMembers.Where(m => m.IsActive && m.Id != 1))
{
    var memberFolder = Path.Combine(familyRoot, SanitizeName(member.DisplayName));
    Directory.CreateDirectory(memberFolder);
}

// FileSystemWatcher set to IncludeSubdirectories = true already covers Family/*
// Attribution is resolved in FileEnqueueService:

private int? AttributeToMember(string filePath)
{
    // Check if path is inside Family/{Name}/
    var familyRoot = Path.Combine(_ledgerDrivePath, "Family");
    if (!filePath.StartsWith(familyRoot, StringComparison.OrdinalIgnoreCase))
        return 1;  // Self

    var relativeParts = Path.GetRelativePath(familyRoot, filePath).Split(Path.DirectorySeparatorChar);
    if (relativeParts.Length < 2) return 1;

    var folderName = relativeParts[0];
    var member = _members.FirstOrDefault(m =>
        string.Equals(SanitizeName(m.DisplayName), folderName, StringComparison.OrdinalIgnoreCase));
    return member?.Id ?? 1;   // Fallback to Self if folder name doesn't match
}
```

---

## 6. Password Cracking Attribution

### 6.1 Priority Order

When an encrypted file is detected in `Family/Priya/priya_sbi_dec.pdf`:

1. **Try Priya's credentials first** (DOB, PAN, mobile, name permutations)
2. **Then try Self credentials** (Ravi Kumar's DOB, PAN, mobile, name permutations)
3. **Still fails** → `file.pw_required` event with `memberName: "Priya"`

```csharp
// PasswordCrackerService.cs
private IEnumerable<string> BuildAttemptList(int attributedMemberId)
{
    // Primary: the attributed member
    var primary = _members.Single(m => m.Id == attributedMemberId);
    foreach (var attempt in GenerateAttempts(primary))
        yield return attempt;

    // Fallback: Self (if not already self)
    if (attributedMemberId != 1)
    {
        var self = _members.Single(m => m.Id == 1);
        foreach (var attempt in GenerateAttempts(self))
            yield return attempt;
    }
}
```

### 6.2 Toast on Failure

```csharp
_toastService.Notify(new ToastDefinition(
    Title: "Password Required",
    Body:  $"Could not unlock {fileName} ({member.DisplayName}'s file)",
    ActionLabel: "Enter Password",
    ActionId:    "openFile",
    ActionParam: fileId.ToString()
));
```

---

## 7. Family Dashboard (v2)

### 7.1 View Toggle

```
[👤 My View] [👨‍👩‍👧 Family View]

Family View shows:
├── Consolidated Net Worth: ₹1,24,50,000
│   breakdown by member: Ravi ₹85L | Priya ₹32L | Arjun ₹7.5L
│
├── Per-member Account Summary cards
│   [Ravi Kumar] [Priya Kumar] [Arjun] [Mom]
│    ₹45,678      ₹12,340      ₹7,500  ₹25,000
│
└── Recent Family Activity
    Priya's SBI Dec 2024 processed — 89 txns
    Arjun's PPF Statement organized
```

### 7.2 Consolidated Net Worth Query

```sql
-- Family consolidated net worth (v2)
SELECT
    COALESCE(fm.display_name, 'Unknown') AS member,
    SUM(CASE WHEN a.type IN ('Asset') THEN t.amount ELSE -t.amount END) AS net_worth
FROM accounts a
JOIN family_members fm ON fm.id = a.family_member_id
LEFT JOIN transactions t ON t.account_id = a.id
WHERE fm.is_active = 1
GROUP BY fm.id, fm.display_name;

-- Sum for consolidated total
SELECT SUM(net_worth) AS family_net_worth FROM (above);
```

---

## 8. Per-Member Reports

All report endpoints accept `?memberId=N` or `?memberId=all`:

```
GET /reports/net-worth?memberId=2
→ Shows Priya's net worth trend only

GET /reports/income-expense?memberId=all&from=2025-01-01&to=2025-03-31
→ Consolidated family income-expense for Q1
→ Response includes:
  {
    "consolidated": { "income": 200000, "expense": 95000 },
    "byMember": [
      { "memberId": 1, "name": "Ravi", "income": 120000, "expense": 55000 },
      { "memberId": 2, "name": "Priya", "income": 80000, "expense": 40000 }
    ]
  }
```

---

## 9. Goals and Budgets (v2)

### 9.1 Goal Scoping

```sql
-- Goal can be personal or family-shared
CREATE TABLE goals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    family_member_id INTEGER REFERENCES family_members(id),  -- NULL = whole family goal
    title            TEXT    NOT NULL,
    target_amount    REAL    NOT NULL,
    due_date         TEXT,
    is_active        INTEGER NOT NULL DEFAULT 1
);

-- Example: Family vacation goal (shared)
INSERT INTO goals (family_member_id, title, target_amount)
VALUES (NULL, 'Goa Vacation 2025', 80000);

-- Example: Priya's personal savings goal
INSERT INTO goals (family_member_id, title, target_amount)
VALUES (2, 'Priya Emergency Fund', 200000);
```

### 9.2 Budget Scoping

Budgets work the same way — `family_member_id = NULL` means a family-wide budget; `family_member_id = 2` applies only to Priya's spending.

---

## 10. Data Isolation Principles

1. **Family members cannot see each other's data** within the app (single-user app — the device owner sees everyone's data).
2. **Deletion of a family member** prompts: "Remove Priya? Her 234 transactions will remain in your ledger, associated with [No Member]. They will not be deleted."
3. **Export:** When exporting a family member's report (PDF/CSV), the file is named `Priya_IncomeExpense_2025.pdf` and includes only that member's data.
4. **Privacy Mode:** When sending data to LLM with Privacy Mode ON, member names are also anonymized (`PERSON_B` for Priya, `PERSON_C` for Arjun, etc.).

---

## 11. v1 → v2 Migration Path

Since all schema hooks are in place from day 1 (nullable FK, `family_mode_enabled = false`), the v2 upgrade only requires:

| Change | Type |
|---|---|
| `family_mode_enabled` set to `true` (user action) | Settings flag |
| Show "Family" nav tab | Frontend: unhide |
| Show "Family View" dashboard toggle | Frontend: unhide |
| Create `Family/` subfolder in LedgerDrive | App action on enable |
| Watch `Family/*` subfolders | FileWatcher already recursive |
| Attribute new files from `Family/*` | FileEnqueueService: new code |
| `/family/members` CRUD endpoints | New API endpoints |
| `?memberId=all` consolidated report queries | New query logic |
| ML.NET model: add `memberId` feature | Incremental model update |

**No database migration required.** All `family_member_id` columns already exist with `DEFAULT NULL`. Existing records remain attributed to member `1` (Self).

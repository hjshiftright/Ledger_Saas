# Ledger Desktop — Files to Carry to the New Repo

When this project is moved to a dedicated Windows Desktop repository, carry the following files.
Everything under `docs/win app/` is desktop-specific and should move with it.

---

## 1. Design Documents (all required)

Move as-is into `/docs/design/` in the new repo:

| File | Purpose |
|---|---|
| `design/00-overview.md` | Product vision, non-goals, technology choices |
| `design/01-requirements.md` | Full functional + non-functional requirements (F-* / NF-*) |
| `design/02-architecture.md` | Solution structure, projects, DI, in-process Kestrel |
| `design/03-data-model.md` | All SQLite tables with DDL + ERD |
| `design/04-file-intelligence.md` | LedgerDrive watcher, Vault Manager, Password Candidates, Parsers, ML pipeline |
| `design/05-security.md` | SQLCipher key derivation, DPAPI, column encryption, PIN, audit log |
| `design/06-shell-integration.md` | SharpShell overlays, context menus, tray icon, Windows Search |
| `design/07-llm-privacy.md` | PrivacyTransformer, local-first LLM strategy, LLM provider config |
| `design/08-api-design.md` | All REST + SignalR endpoints |
| `design/09-frontend.md` | React pages, dashlet system, UX language standards, routing |
| `design/10-family-mode.md` | Family Mode v2 design (future) |
| `design/11-packaging.md` | MSIX, code signing, AppInstaller, update flow |
| `design/12-roadmap.md` | Phase 0–5 release plan |

## 2. Plan File

| File | Purpose |
|---|---|
| `plan-ledgerDesktop.prompt.md` | Master design brief — use as CLAUDE.md / Copilot instructions seed in new repo |

## 3. Consolidated Reference Doc (already done)

`reference.md` in this same folder has already extracted and consolidated the relevant sections from the existing `docs/` files. Carry it as `/docs/reference.md` in the new repo. It contains:

- Double-entry accounting primer + full Chart of Accounts (Indian)
- Parser supported sources, pipeline stages, CAS password convention, NormalizedTransaction schema
- Full report suite reference (8 core reports + 5 investment reports)
- **All 20 strategic insight dashlets** across 5 phases (Safety, Wealth, Aspirations, Reality, Legacy) with calculation logic and visual descriptions
- Cross-reference table pointing every topic back to its design doc

**Do NOT also carry the raw source files** (`double-entry-accounting.md`, `pdf-parser.md`, `reporting.md`, `dashboard_team_brief*.md`) — `reference.md` is the distilled version.

## 4. Do NOT Carry

| What | Why |
|---|---|
| `backend/` Python source | Completely replaced by .NET solution |
| `frontend/` React SaaS app | Desktop frontend will be a new Vite project inside the solution |
| `requirements*.txt`, `pyproject.toml` | Python-only |
| `pytest.ini`, `conftest.py`, test files | Python tests |
| `backend/src/migrations/` | Python Alembic migrations — superseded by EF Core migrations |
| All `docs/onboarding*` files | SaaS onboarding wizard — not relevant to desktop |
| `docs/api/onboarding-v2-api-spec.md` | SaaS API — desktop has its own API spec in 08-api-design.md |

---

## 5. Suggested New Repo Structure

```
LedgerDesktop\
├── docs\
│   ├── design\          ← All 13 design docs from win app/design/
│   └── reference\       ← Extracted accounting + parser reference docs
├── src\
│   ├── Ledger.Desktop\  ← WPF + WebView2 shell
│   ├── Ledger.Api\      ← ASP.NET Core in-process API
│   ├── Ledger.Domain\   ← Entities, interfaces
│   ├── Ledger.Infrastructure\ ← EF Core, SQLCipher, repositories
│   ├── Ledger.Parsers\  ← IDocumentParser implementations
│   ├── Ledger.ShellExtension\ ← SharpShell overlays
│   └── Ledger.CrackerProcess\ ← Isolated password attempt process
├── frontend\            ← React 19 + Vite 6 (new project)
├── tests\
│   ├── Ledger.Tests.Unit\
│   └── Ledger.Tests.Integration\
├── installer\           ← MSIX packaging + AppInstaller
├── CLAUDE.md            ← Seeded from plan-ledgerDesktop.prompt.md
└── Ledger.Desktop.sln
```

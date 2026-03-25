# Ledger Desktop — Product Overview

**Version:** 1.0 Design  
**Date:** 2026-03-25  
**Status:** Design Review

---

## 1. Vision

Ledger Desktop is a **zero-onboarding, fully offline, self-protecting Windows personal finance manager**. The user installs the application, chooses a folder (LedgerDrive), drops their bank statements and financial documents into it, and the app does everything else — automatically parsing, decrypting, organizing, categorizing, and journalling every transaction without a single manual data-entry step.

No accounts. No wizards. No cloud. All data encrypted on-device.

---

## 2. Problem Statement

Existing personal finance tools — both desktop (Quicken, MoneyMoney) and web/SaaS (Ledger 3.0 SaaS, YNAB, Money Manager Ex) — require substantial upfront work:

| Pain | Current State | Ledger Desktop |
|---|---|---|
| Setup time | 10-60 min wizard | 2 screens, < 2 min |
| Import friction | Manual file upload per statement | Drop once, done forever |
| Encryption | None / cloud-dependent | SQLCipher + DPAPI, all local |
| Encrypted PDFs | User manually decrypts first | App cracks common password patterns |
| Privacy | Data sent to cloud by default | Zero cloud ingress; LLM opt-in with anonymization |
| Family coverage | Individual only | Designed for family extensibility (Phase 2) |
| File backup | No original preservation | `.vault\` immutable backup of all originals |

---

## 3. Target Users

**Primary (v1):** Individual Indian households with:
- Multiple bank accounts, credit cards, mutual funds, loans
- Password-protected bank statement PDFs (very common: DOB-based, PAN-based passwords)
- Need for consolidated net-worth and tax-ready reports
- Privacy concerns about cloud-based tools

**Secondary (v2 — Family Mode):** Head-of-household wanting to track the entire family's finances:
- Spouse's separate bank accounts and credit cards
- Children's/parents' accounts they manage
- Consolidated family net-worth dashboard
- Per-member tax reports (separate ITR preparation)

---

## 4. Core Concepts

### 4.1 LedgerDrive
A user-chosen folder that acts as the input surface. The user treats it like a drop zone — any financial document placed there is automatically ingested. The app watches it 24/7.

### 4.2 .vault\
A hidden sub-folder inside LedgerDrive that contains immutable copies of every file ever dropped. This is the gold-copy backup. The app never modifies or deletes files from `.vault\`. Users can compare, restore, or reference originals at any time.

### 4.3 Auto-Organization
After successful parsing, files are moved from the root into a canonical folder hierarchy:
```
LedgerDrive\
  Banks\HDFC\2025\January.pdf
  CreditCards\ICICI_CC\2025\March.pdf
  Investments\Zerodha\2025\
  Loans\HDFC_Home\2025\
```

### 4.4 Encrypted Database
All ledger data lives in a single SQLite file encrypted with SQLCipher (AES-256). The encryption key is derived from the machine's hardware identity, optionally strengthened by a user PIN. The DB file is meaningless without the exact machine it was created on (or the PIN, if set).

### 4.5 Privacy-First LLM
LLM providers (Gemini, OpenAI, Anthropic) are entirely optional. When used, a `PrivacyTransformer` replaces real names, account numbers, and exact amounts with anonymized tokens before any data leaves the machine. Users who disable Privacy Mode must explicitly acknowledge that real data is being sent.

### 4.6 Family Mode (Future Phase)
Multiple family member profiles can be created, each with their own encrypted credentials (DOB, PAN, mobile). Files dropped into `Family/{Name}/` subfolders are attributed to that member. The password cracker uses each member's specific credentials. Net worth and reports can be viewed per-member or consolidated across the family.

---

## 5. Product Scope

### v1 — Individual (This Document)
- Quick-Start setup (2 screens, < 2 min)
- LedgerDrive watch + auto-parse + auto-organize
- 15+ bank/institution parsers (PDF + CSV + XLSX)
- PDF password cracking (DOB/PAN/mobile-based)
- Encrypted local database (SQLCipher + DPAPI)
- Windows Shell integration (overlay icons, context menu, Search)
- Dashboard, transactions, reports, budgets, goals
- Manual cash transaction entry
- Optional LLM with Privacy Mode
- System tray, toast notifications
- MSIX distribution with auto-update

### v2 — Family Mode
- Multiple family member profiles
- `Family/{Name}/` drop-zone subfolders in LedgerDrive
- Per-member and consolidated net-worth dashboard
- Per-member password cracking using their own credentials
- Consolidated family reports and tax summaries
- "Needs Password" prompt scoped per family member

### v3 — SaaS / Sync (Optional, Out of Scope)
- Optional encrypted cloud backup (user-controlled key)
- Cross-device sync (phone companion app)
- Shared family workspace (end-to-end encrypted)

---

## 6. Non-Goals (v1)

- Multi-user / multi-machine sync
- Android/iOS companion app
- GST filing or ITR XML export
- Voice commands
- Broker API live feed (no API keys to external financial services)
- Automatic bank email parsing

---

## 7. Technology Choice Summary

| Decision | Choice | Rationale |
|---|---|---|
| Backend language | C# / .NET 9 | Full rewrite; type-safety, Windows-native APIs, single-process shell |
| Frontend | React 19 + Vite 6 + Tailwind 4 | Reuse existing codebase; hosted in WebView2 |
| Database | SQLite + SQLCipher 4.6 | Zero server, encrypted at rest, industry-proven |
| PDF text extraction | PdfPig 0.1.9 | MIT license, best pure-.NET text/table extraction |
| PDF rendering | Docnet.Core 2.6 (PDFium) | Apache 2, Chrome's engine, native AES-256-CBC decryption |
| OCR | Windows.Media.Ocr + Tesseract 5 | Dual-engine: built-in zero-install + LSTM high-accuracy fallback |
| ML categorization | ML.NET 3.0 | On-device, no cloud, incremental learning |
| Shell integration | SharpShell 2.7 | .NET wrapper for Windows Shell COM extensions |
| Distribution | MSIX + AppInstaller | Store-compatible, signed, delta updates |

---

## 8. Document Index

| # | Document | Contents |
|---|---|---|
| 01 | Requirements | Functional, non-functional, constraints |
| 02 | Architecture | System components, deployment, process model |
| 03 | Data Model | All DB entities, relationships, extensibility |
| 04 | File Intelligence | LedgerDrive, vault, pipeline, organizer |
| 05 | Security | Encryption, PIN, memory, anti-tamper |
| 06 | Shell Integration | Overlays, context menus, Search, toasts |
| 07 | LLM & Privacy | Providers, transformer, cert pinning |
| 08 | API Design | All endpoints, SignalR events |
| 09 | Frontend | Pages, components, state management |
| 10 | Family Mode | Extensibility design for Phase 2 |
| 11 | Packaging | MSIX, signing, CI/CD, update |
| 12 | Roadmap | v1 → v2 → v3 phases and milestones |

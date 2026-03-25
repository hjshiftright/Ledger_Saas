# Ledger Desktop — Roadmap

**Version:** 1.0  
**Status:** Design Review

---

## Version 1 — Personal Finance Desktop App

**Theme:** Solid, secure, zero-cloud personal ledger that processes financial documents automatically.

### Scope
v1 is a single-user Windows desktop application. It covers the user's own accounts, statements, and net worth. Family Mode infrastructure is in place (schema, flags) but no family UI is shown.

### Milestones

| Phase | Description | Deliverable | Effort |
|---|---|---|---|
| 0 — Bootstrap | Solution scaffold, WPF + WebView2 shell, embedded Kestrel, health check, QuickStartWizard (2 screens), navigation shell | App launches, shows wizard, navigates to dashboard | 1 week |
| 1 — Security Foundation | SQLCipher setup, DPAPI key derivation, column-level AES-256-GCM, optional Argon2id PIN, anti-tamper guard | DB encrypted, PIN lock screen functional | 1 week |
| 2 — Database & Domain | All EF Core entities, migrations (0000–0003), Chart of Accounts seed, FamilyMember seed (Self=1), repositories, service layer skeleton | `ledger.db` created and opened correctly | 1 week |
| 3 — LedgerDrive & Vault | FileSystemWatcher, VaultManager (copy + deletion detection), folder icon + `desktop.ini`, crash-recovery scan, SignalR `file.*` events | Drop a file → vaulted + event appears in FilesPage | 1 week |
| 4 — File Intelligence | FileDetectorService, PasswordCrackerService (isolated process), all 19 parser classes (starting with HDFC, SBI, ICICI, Axis priorities), OCR chain (WinOCR + Tesseract), NormalizerService, DeduplicationService, FileOrganizerService | HDFC/SBI PDFs auto-parse end-to-end | 3 weeks |
| 5 — Transaction Pipeline | ProposalGeneratorService, ML.NET TextClassification categorization (pre-trained model), ProposalsPage (approve/edit/reject + bulk), transaction posting, incremental ML retraining from approvals | Full statement → proposals → approved transactions | 2 weeks |
| 6 — Shell Integration | SharpShell overlay handler (4 states), context menu, custom folder icon, Windows Search crawl scope + property metadata, ToastService | Overlays visible in Explorer, right-click menu works, Search finds HDFC 2025 | 1 week |
| 7 — LLM & Privacy | ILlmProvider + 3 providers, PrivacyTransformer (all rules), Chat endpoint, ChatWidget with Privacy Mode toggle, cert pinning, API key save/test in Settings, LLM vision fallback for failed parses | Chat works with Gemini in Privacy Mode | 1 week |
| 8 — Reports & Dashboard | All 9 report endpoints, PDF/CSV export, Dashboard widgets (Net Worth, File Activity, This Month), ProfilePage, SettingsPage (all panels), tax summary | Full financial reports with export | 1 week |
| 9 — Polish & Packaging | MSIX package, MSIX manifest with COM registration, SharpShell custom action, Tesseract + model bundling, React build integration, Azure Trusted Signing CI, AppInstaller delta update file, system tray, auto-start setting | Signed MSIX installer, installable on clean machine | 1 week |

**Total v1 Effort:** ~13 weeks (3 months)

### Parser Priority Order (Phase 4)

Port parsers from existing Python `backend/src/api/parser/` in this order:

1. HDFC Bank (savings + credit) — highest user volume
2. SBI (savings + credit)
3. ICICI Bank (savings + credit + iMobile CSV)
4. Axis Bank (savings + credit)
5. Kotak Mahindra (savings + credit)
6. YES Bank (savings)
7. IDFC First Bank
8. IndusInd Bank
9. Bank of Baroda
10. Union Bank of India
11. Canara Bank
12. Bank of India
13. Punjab National Bank
14. RBL Bank (credit focus)
15. Standard Chartered India (credit)
16. American Express India (credit)
17. HSBC India (savings + credit)
18. Generic CSV (fallback)
19. Generic XLSX (fallback)

---

## Version 2 — Family Finance Mode

**Theme:** Track net worth for your whole family from one app.

**Trigger:** Family Mode is enabled by user in Settings. All v1 data continues undisturbed.

### Features

| Feature | Description |
|---|---|
| Family member management | Add/edit/remove Spouse, Children, Parents etc. with encrypted PAN/DOB/mobile |
| `Family/{Name}/` LedgerDrive subfolders | Auto-created per member, files dropped here auto-attributed |
| Family-aware password cracking | Tries attributed member's credentials first |
| Family dashboard view | "Family View" toggle showing consolidated net worth + per-member cards |
| Per-member reports | All 9 reports filterable by member or consolidated (`?memberId=all`) |
| Family-scoped budgets & goals | Goals and budgets can be shared (family-wide) or per-member |
| Family-aware toasts | "Priya's file needs password" |
| Family data export | Per-member PDF/CSV reports |

### Milestones

| Phase | Description | Effort |
|---|---|---|
| FM-1 | Family member CRUD UI + API, `Family/` subfolder creation, FileWatcher attribution from path | 1 week |
| FM-2 | Family-aware password cracking, family-aware toast messages | 3 days |
| FM-3 | Family dashboard toggle, consolidated net worth widget, per-member account summary | 1 week |
| FM-4 | All reports: `?memberId=all` consolidated queries, per-member drill-down, PDF/CSV export with member name | 1 week |
| FM-5 | Family-scoped budgets and goals, family financial health score | 1 week |
| FM-6 | Regression testing, polish, release MSIX update | 1 week |

**Total v2 Effort:** ~6 weeks (1.5 months)

---

## Version 3 — Cloud Sync & SaaS Bridge (Optional / Long-term)

**Theme:** Optionally sync your secure Ledger data across devices or share selected reports with a CA/family member.

> v3 is speculative. It will only be designed when v2 is stable and there is validated user demand.

### Candidate Features

| Feature | Notes |
|---|---|
| Encrypted cloud backup | Full SQLCipher DB backup to user's own cloud storage (OneDrive, Google Drive) — key never leaves device |
| Multi-device sync | Second Windows machine can open the same encrypted local DB synced via OneDrive |
| Read-only share links | Generate a time-limited encrypted report share link (CA/CA-assistant access) |
| Mobile companion app | iOS/Android read-only app to view net worth and recent transactions |
| Bank statement email forwarding | Forward email from bank → webhook → auto-add to LedgerDrive |
| Tax filing integration | One-click export of ITR-required schedules (Salary, Capital Gains, etc.) |
| SaaS plan | If user wants managed hosting, optional upgrade to Ledger Cloud with monthly subscription |

**Key constraint:** Any cloud feature must be zero-trust. The server never sees plaintext financial data. User holds the key.

---

## Parser Improvement Backlog (Ongoing)

The parser engine is never "done." Financial institutions update statement formats frequently.

| Item | Priority |
|---|---|
| HDFC 2025 new PDF layout support | High |
| SBI YONO CSV export support | High |
| ICICI iMobile statement format | Medium |
| Multi-currency account support | Medium |
| NPS (National Pension Scheme) statement parsing | Low |
| PPF passbook PDF | Low |
| Mutual fund CAS statement (CAMS/Karvy) | High (v2) |
| Zerodha contract note PDF | Medium (v2) |
| Groww statement | Medium (v2) |
| Kuvera folio statement | Low (v2) |
| SGB (Sovereign Gold Bond) document | Low |

---

## Quality Gates Before Each Release

- All existing parser integration tests pass (fixtures in `backend/tests/fixtures/` ported to C#)
- No `CRITICAL` or `HIGH` severity findings in SAST scan (Semgrep)
- SQLCipher key derivation verified via known-answer test
- SharpShell overlay visible in Explorer on clean VM
- MSIX installs and uninstalls cleanly on Windows 10 + Windows 11 VMs
- AppInstaller delta update tested (v1.0 → v1.1 clean update)
- Memory scan: no SecureString content visible as cleartext in heap dump (verified with ProcDump + strings)

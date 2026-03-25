"""Bulk-refactor remaining router import paths to use ledger.db.repositories."""
import pathlib, re

SRC = pathlib.Path(r"e:\NonProjCode\ledger-3.0\src\ledger")

REPLACEMENTS = [
    (
        "from ledger.repositories.inmemory.store import account_repo, institution_repo, account_detail_repo",
        "from ledger.db.repositories import account_repo, institution_repo, account_detail_repo",
    ),
    (
        "from ledger.repositories.inmemory.store import account_repo, transaction_repo",
        "from ledger.db.repositories import account_repo, transaction_repo",
    ),
    (
        "from ledger.repositories.inmemory.store import snapshot_repo, account_repo, transaction_repo",
        "from ledger.db.repositories import snapshot_repo, account_repo, transaction_repo",
    ),
    (
        "from ledger.repositories.inmemory.store import institution_repo",
        "from ledger.db.repositories import institution_repo",
    ),
    (
        "from ledger.repositories.inmemory.store import account_repo",
        "from ledger.db.repositories import account_repo",
    ),
    (
        "from ledger.repositories.inmemory.store import settings_repo",
        "from ledger.db.repositories import settings_repo",
    ),
    # Orchestrator imports InMemorySettingsRepository class directly
    (
        "from ledger.db.repositories.settings_repo import InMemorySettingsRepository",
        "from ledger.db.repositories import settings_repo",
    ),
]

changed = []
for py_file in SRC.rglob("*.py"):
    text = py_file.read_text(encoding="utf-8")
    new_text = text
    for old, new in REPLACEMENTS:
        new_text = new_text.replace(old, new)
    if new_text != text:
        py_file.write_text(new_text, encoding="utf-8")
        changed.append(str(py_file))

print(f"Updated {len(changed)} file(s):")
for f in changed:
    print(" ", f)

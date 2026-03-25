"""Unit tests for LLMProviderRegistry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from modules.llm.registry import LLMProviderRegistry


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_provider(name: str = "gemini") -> MagicMock:
    provider = MagicMock()
    provider.PROVIDER_NAME = name
    return provider


# ── register & get ────────────────────────────────────────────────────────────

class TestRegisterAndGet:
    def test_register_and_get_by_id(self):
        reg = LLMProviderRegistry()
        p = _make_provider()
        reg.register("user-1", p, provider_id="p1")
        assert reg.get_by_id("user-1", "p1") is p

    def test_get_by_id_unknown_returns_none(self):
        reg = LLMProviderRegistry()
        assert reg.get_by_id("user-1", "missing") is None

    def test_get_default_returns_default(self):
        reg = LLMProviderRegistry()
        p1 = _make_provider("gemini")
        p2 = _make_provider("openai")
        reg.register("user-1", p1, provider_id="p1", is_default=False)
        reg.register("user-1", p2, provider_id="p2", is_default=True)
        assert reg.get_default("user-1") is p2

    def test_get_default_falls_back_to_first_active(self):
        """If no provider is marked default, return the first active one."""
        reg = LLMProviderRegistry()
        p = _make_provider()
        reg.register("user-1", p, provider_id="p1", is_default=False)
        assert reg.get_default("user-1") is p

    def test_get_default_no_providers_returns_none(self):
        reg = LLMProviderRegistry()
        assert reg.get_default("unknown-user") is None

    def test_register_new_default_demotes_old(self):
        reg = LLMProviderRegistry()
        p1 = _make_provider("gemini")
        p2 = _make_provider("openai")
        reg.register("user-1", p1, provider_id="p1", is_default=True)
        reg.register("user-1", p2, provider_id="p2", is_default=True)
        # p2 should now be the default
        assert reg.get_default("user-1") is p2


# ── has_provider ──────────────────────────────────────────────────────────────

class TestHasProvider:
    def test_has_provider_true_when_active(self):
        reg = LLMProviderRegistry()
        reg.register("user-1", _make_provider(), provider_id="p1")
        assert reg.has_provider("user-1") is True

    def test_has_provider_false_when_no_providers(self):
        reg = LLMProviderRegistry()
        assert reg.has_provider("user-1") is False

    def test_has_provider_false_when_all_inactive(self):
        reg = LLMProviderRegistry()
        reg.register("user-1", _make_provider(), provider_id="p1")
        reg.deactivate("user-1", "p1")
        assert reg.has_provider("user-1") is False


# ── deactivate ────────────────────────────────────────────────────────────────

class TestDeactivate:
    def test_deactivate_returns_true_when_found(self):
        reg = LLMProviderRegistry()
        reg.register("user-1", _make_provider(), provider_id="p1")
        assert reg.deactivate("user-1", "p1") is True

    def test_deactivate_returns_false_when_not_found(self):
        reg = LLMProviderRegistry()
        assert reg.deactivate("user-1", "missing") is False

    def test_deactivated_provider_not_returned_as_default(self):
        reg = LLMProviderRegistry()
        p = _make_provider()
        reg.register("user-1", p, provider_id="p1", is_default=True)
        reg.deactivate("user-1", "p1")
        assert reg.get_default("user-1") is None


# ── remove ────────────────────────────────────────────────────────────────────

class TestRemove:
    def test_remove_returns_true_when_found(self):
        reg = LLMProviderRegistry()
        reg.register("user-1", _make_provider(), provider_id="p1")
        assert reg.remove("user-1", "p1") is True

    def test_remove_returns_false_when_not_found(self):
        reg = LLMProviderRegistry()
        assert reg.remove("user-1", "missing") is False

    def test_removed_provider_not_accessible(self):
        reg = LLMProviderRegistry()
        reg.register("user-1", _make_provider(), provider_id="p1")
        reg.remove("user-1", "p1")
        assert reg.get_by_id("user-1", "p1") is None


# ── list_providers ────────────────────────────────────────────────────────────

class TestListProviders:
    def test_list_returns_all_entries(self):
        reg = LLMProviderRegistry()
        reg.register("user-1", _make_provider("gemini"), provider_id="p1")
        reg.register("user-1", _make_provider("openai"), provider_id="p2")
        entries = reg.list_providers("user-1")
        assert len(entries) == 2

    def test_list_empty_for_unknown_user(self):
        reg = LLMProviderRegistry()
        assert reg.list_providers("unknown") == []

    def test_list_includes_inactive(self):
        reg = LLMProviderRegistry()
        reg.register("user-1", _make_provider(), provider_id="p1")
        reg.deactivate("user-1", "p1")
        entries = reg.list_providers("user-1")
        assert len(entries) == 1
        assert entries[0].is_active is False

"""LLMProviderRegistry — manages multiple provider instances for a user.

Usage:
    registry = LLMProviderRegistry()
    registry.register("user-123", gemini_provider)
    provider = registry.get_default("user-123")
    response = provider.extract_text(request)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from modules.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


@dataclass
class ProviderEntry:
    """A registered provider with its metadata."""

    provider: BaseLLMProvider
    provider_id: str
    is_default: bool = False
    is_active: bool = True


class LLMProviderRegistry:
    """Stores and retrieves LLM provider instances keyed by user_id.

    Each user can have multiple providers registered. One is marked as default.
    The registry does not manage API keys — that is done by the LLMProvider
    database model. This registry holds live, instanciated provider objects.

    Thread safety: Not thread-safe. Use one registry per request context
    (FastAPI dependency injection) or protect with a lock for long-lived use.
    """

    def __init__(self) -> None:
        # user_id → list[ProviderEntry]
        self._providers: dict[str, list[ProviderEntry]] = {}

    def register(
        self,
        user_id: str,
        provider: BaseLLMProvider,
        provider_id: str,
        is_default: bool = False,
        is_active: bool = True,
    ) -> None:
        """Register a provider instance for a user.

        If `is_default=True`, any previously-default provider is demoted.
        """
        entries = self._providers.setdefault(user_id, [])

        # Demote existing default if setting a new one
        if is_default:
            for entry in entries:
                entry.is_default = False

        entries.append(
            ProviderEntry(
                provider=provider,
                provider_id=provider_id,
                is_default=is_default,
                is_active=is_active,
            )
        )
        logger.debug(
            "LLMProviderRegistry: registered %s for user %s (default=%s)",
            provider.PROVIDER_NAME,
            user_id,
            is_default,
        )

    def get_default(self, user_id: str) -> BaseLLMProvider | None:
        """Return the default provider for a user, or the first active one."""
        for entry in self._providers.get(user_id, []):
            if entry.is_active and entry.is_default:
                return entry.provider
        # Fall back to first active provider
        for entry in self._providers.get(user_id, []):
            if entry.is_active:
                return entry.provider
        return None

    def get_by_id(self, user_id: str, provider_id: str) -> BaseLLMProvider | None:
        """Return a specific provider by its registered ID."""
        for entry in self._providers.get(user_id, []):
            if entry.provider_id == provider_id:
                return entry.provider
        return None

    def list_providers(self, user_id: str) -> list[ProviderEntry]:
        """Return all registered entries for a user."""
        return list(self._providers.get(user_id, []))

    def has_provider(self, user_id: str) -> bool:
        """Return True if the user has at least one active provider."""
        return any(e.is_active for e in self._providers.get(user_id, []))

    def deactivate(self, user_id: str, provider_id: str) -> bool:
        """Deactivate a provider without removing it. Returns True if found."""
        for entry in self._providers.get(user_id, []):
            if entry.provider_id == provider_id:
                entry.is_active = False
                return True
        return False

    def remove(self, user_id: str, provider_id: str) -> bool:
        """Remove a provider entry entirely. Returns True if found."""
        entries = self._providers.get(user_id, [])
        before = len(entries)
        self._providers[user_id] = [e for e in entries if e.provider_id != provider_id]
        return len(self._providers[user_id]) < before

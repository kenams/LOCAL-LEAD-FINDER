"""
Base provider interface
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.schemas.prospect import ProspectCreate


@dataclass
class SearchProviderResult:
    """Structured provider response with diagnostics."""

    provider: str
    leads: List[Dict[str, Any]] = field(default_factory=list)
    raw_count: int = 0
    queries_attempted: List[Dict[str, Any]] = field(default_factory=list)
    fallback_triggered: bool = False
    notes: str = ""


class ProviderBase(ABC):
    """Base class for lead providers."""

    @abstractmethod
    async def search_leads(
        self,
        location: str,
        category: str,
        limit: int,
        search_queries: List[str] | None = None,
        max_candidates: int | None = None,
    ) -> SearchProviderResult:
        """Search for leads in a location/category."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (API keys, etc.)."""
        raise NotImplementedError

    def normalize_lead(self, raw_data: Dict[str, Any], location: str, category: str) -> ProspectCreate:
        """Normalize raw data to ProspectCreate schema."""
        return ProspectCreate(
            business_name=raw_data.get("business_name", ""),
            category=category,
            location=location,
            address=raw_data.get("address"),
            phone=raw_data.get("phone"),
            website=raw_data.get("website"),
            source=self.__class__.__name__,
        )

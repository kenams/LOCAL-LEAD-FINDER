"""
Test deduplication
"""
import pytest
from app.services.deduplicator import Deduplicator

class TestDeduplicator:
    def test_deduplicate_identical(self):
        dedup = Deduplicator()

        leads = [
            {"business_name": "Coiffure Plus", "location": "Toulouse", "website": "https://coiffureplus.fr"},
            {"business_name": "Coiffure Plus", "location": "Toulouse", "website": "https://coiffureplus.fr"}
        ]

        unique = dedup.deduplicate_leads(leads)
        assert len(unique) == 1

    def test_deduplicate_similar(self):
        dedup = Deduplicator()

        leads = [
            {"business_name": "Coiffure Plus", "location": "Toulouse"},
            {"business_name": "Coiffure Plus Toulouse", "location": "Toulouse"}
        ]

        unique = dedup.deduplicate_leads(leads)
        assert len(unique) == 1  # Should be deduplicated as similar

    def test_normalize_text(self):
        dedup = Deduplicator()

        assert dedup._normalize_text("Coiffure Plus") == dedup._normalize_text("coiffure plus")
        assert dedup._normalize_text("À la Française") == dedup._normalize_text("a la francaise")
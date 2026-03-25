"""
Test scoring functionality
"""
import pytest
from app.services.site_analyzer import SiteAnalyzer

class TestSiteAnalyzer:
    def test_calculate_quality_score(self):
        analyzer = SiteAnalyzer()

        # Perfect site
        checks = {
            "has_https": True,
            "has_title": True,
            "has_meta_description": True,
            "has_h1": True,
            "has_services": True,
            "has_contact_info": True,
            "has_cta": True,
            "has_responsive_meta": True,
            "reasonable_size": True,
            "has_images": True
        }

        score = analyzer._calculate_quality_score(checks)
        assert score == 100

        # Poor site
        checks = {k: False for k in checks.keys()}
        score = analyzer._calculate_opportunity_score(checks)
        assert score > 50  # High opportunity

    def test_determine_feasibility(self):
        analyzer = SiteAnalyzer()

        # Easy project
        checks = {f"check_{i}": True for i in range(10)}
        feasibility = analyzer._determine_feasibility(checks)
        assert feasibility == "EASY"

        # Advanced project
        checks = {f"check_{i}": False for i in range(10)}
        feasibility = analyzer._determine_feasibility(checks)
        assert feasibility == "ADVANCED"

    @pytest.mark.asyncio
    async def test_missing_website_is_high_opportunity(self):
        analyzer = SiteAnalyzer()
        result = await analyzer.analyze_site("", country="CH", language="fr")
        assert result["opportunity_score"] >= 90
        assert result["site_quality_score"] == 0
        assert "no_website" in result["detected_issues"]

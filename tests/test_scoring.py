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
        assert result["new_business_score"] >= 90
        assert result["target_type"] == "early_stage_business"
        assert result["site_quality_score"] == 0
        assert "no_website" in result["detected_issues"]

    def test_new_business_profile_detects_early_stage_signals(self):
        analyzer = SiteAnalyzer()
        profile = analyzer._derive_new_business_profile(
            checks={
                "has_booking_system": False,
                "has_seo_foundation": False,
                "has_modern_ui": False,
            },
            page_count=2,
            content_length=900,
            reviews_count=3,
            instagram_url="https://instagram.com/example",
            quality_score=35,
            opportunity_score=82,
        )

        assert profile["new_business_score"] >= 65
        assert profile["target_type"] == "early_stage_business"
        assert profile["social_first_business"] is True

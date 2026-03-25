"""
Tests for premium mockup generation.
"""
from pathlib import Path

from app.services.mockup_generator import MockupGenerator


def test_generate_premium_mockup_for_beauty(tmp_path, monkeypatch):
    generator = MockupGenerator()
    generator.output_dir = str(tmp_path)

    filepath = generator.generate_mockup("Maison Studio", "hair salon", "Geneva", language="en", quality_level="premium")

    assert filepath
    html = Path(filepath).read_text(encoding="utf-8")
    assert "Maison Studio" in html
    assert "Premium concept" in html or "premium" in html.lower()
    assert "View signature services" in html
    assert "Editorial elegance" in html


def test_generate_premium_mockup_for_trades(tmp_path):
    generator = MockupGenerator()
    generator.output_dir = str(tmp_path)

    filepath = generator.generate_mockup("Urgence Plomberie", "plumber", "Toulouse", language="fr", quality_level="premium")

    assert filepath
    html = Path(filepath).read_text(encoding="utf-8")
    assert "Appel urgence prioritaire" in html
    assert "Urgence 7j/7" in html
    assert "Des preuves placees la ou le prospect les attend" in html
    assert "Un process plus clair qui retire les frictions avant le premier appel." in html

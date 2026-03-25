#!/usr/bin/env python3
"""
Script de test rapide pour Local Lead Finder
"""
import sys
import os
from pathlib import Path

# Ajouter le répertoire app au path
sys.path.insert(0, str(Path(__file__).parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def test_imports():
    """Tester les imports de base"""
    print("🔍 Test des imports...")

    try:
        # Test des imports de base sans dépendances externes
        from app.models.prospect import Prospect
        print("✅ Modèles importés")

        from app.schemas.prospect import ProspectCreate
        print("✅ Schémas importés")

        print("🎉 Imports réussis ! Le projet est structuré correctement.")
        return True

    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False

def test_config():
    """Tester la configuration (nécessite dotenv)"""
    print("\n🔧 Test de la configuration...")

    try:
        from app.core.config import settings
        print("✅ Configuration chargée")
        print(f"   - DB: {settings.DATABASE_URL}")
        print(f"   - Langue par défaut: {settings.DEFAULT_LANGUAGE}")
        return True
    except ImportError as e:
        print(f"❌ Configuration nécessite: {e}")
        print("💡 Installez avec: pip install python-dotenv")
        return False

def test_database():
    """Tester la base de données"""
    print("\n💾 Test de la base de données...")

    try:
        from app.db.session import init_db
        init_db()
        print("✅ Base de données initialisée")
        return True
    except Exception as e:
        print(f"❌ Erreur base de données: {e}")
        return False

def test_services():
    """Tester les services de base"""
    print("\n🔧 Test des services...")

    try:
        from app.services.deduplicator import Deduplicator
        dedup = Deduplicator()

        # Test déduplication
        leads = [
            {"business_name": "Test Coiffure", "location": "Toulouse"},
            {"business_name": "Test Coiffure", "location": "Toulouse"}
        ]
        unique = dedup.deduplicate_leads(leads)
        assert len(unique) == 1, "Déduplication échouée"
        print("✅ Déduplication fonctionne")

        from app.services.email_generator import EmailGenerator
        generator = EmailGenerator()
        email = generator.generate_email({"business_name": "Test", "category": "coiffeur"}, "fr")
        assert "subject" in email and "body" in email, "Génération email échouée"
        print("✅ Génération d'emails fonctionne")

        return True

    except Exception as e:
        print(f"❌ Erreur services: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 Test du projet Local Lead Finder")
    print("=" * 50)

    results = []

    # Test 1: Imports de base
    results.append(("Imports de base", test_imports()))

    # Test 2: Configuration
    results.append(("Configuration", test_config()))

    # Test 3: Base de données
    results.append(("Base de données", test_database()))

    # Test 4: Services
    results.append(("Services", test_services()))

    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSULTATS DES TESTS:")

    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if success:
            passed += 1

    print(f"\n🎯 Score: {passed}/{len(results)} tests réussis")

    if passed == len(results):
        print("\n🎉 Tous les tests sont passés ! Le projet est prêt.")
        print("\n📋 Prochaines étapes:")
        print("   1. python run.py --init-db")
        print("   2. python seed.py  # Données d'exemple")
        print("   3. python run.py --ui  # Interface")
        print("   4. python run.py --collect --locations 'Toulouse' --categories 'coiffeur' --limit 3")
    else:
        print("\n⚠️  Certains tests ont échoué. Installez les dépendances manquantes:")
        print("   pip install python-dotenv sqlalchemy pydantic")

if __name__ == "__main__":
    main()

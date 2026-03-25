#!/usr/bin/env python3
"""
Script d'installation simplifié pour Local Lead Finder
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Exécuter une commande et afficher le résultat"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ {description} réussi")
            return True
        else:
            print(f"❌ {description} échoué:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Erreur lors de {description}: {e}")
        return False

def main():
    """Installation simplifiée"""
    print("🚀 Installation de Local Lead Finder")
    print("=" * 50)

    # Vérifier Python
    print(f"🐍 Python: {sys.version}")

    # Installer packages de base
    packages = [
        ("python-dotenv", "Gestion des variables d'environnement"),
        ("sqlalchemy", "Base de données ORM"),
        ("pydantic", "Validation de données"),
        ("fastapi", "API web"),
        ("uvicorn", "Serveur ASGI"),
        ("streamlit", "Interface utilisateur"),
        ("requests", "Requêtes HTTP"),
        ("beautifulsoup4", "Parsing HTML"),
        ("jinja2", "Templates"),
        ("pandas", "Manipulation de données"),
        ("openpyxl", "Export Excel"),
        ("apscheduler", "Planification de tâches"),
        ("httpx", "Client HTTP async"),
        ("faker", "Données de test")
    ]

    installed = 0
    for package, desc in packages:
        if run_command(f"pip install {package}", f"Installation de {package} ({desc})"):
            installed += 1

    print(f"\n📊 Installation terminée: {installed}/{len(packages)} packages installés")

    if installed >= 8:  # Packages essentiels
        print("\n🎉 Installation réussie ! Vous pouvez maintenant tester le projet:")
        print("   1. python run.py --init-db")
        print("   2. python run.py --ui")
        print("   3. python run.py --collect --locations 'Toulouse' --categories 'coiffeur' --limit 2")
    else:
        print("\n⚠️  Installation incomplète. Essayez d'installer manuellement:")
        print("   pip install python-dotenv sqlalchemy pydantic fastapi uvicorn streamlit")

if __name__ == "__main__":
    main()
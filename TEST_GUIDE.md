# Guide de Test - Local Lead Finder

## 🚀 Démarrage Rapide

### 1. Installation des Dépendances
```bash
# Installation complète
pip install -r requirements.txt

# Ou installation par étapes si problème:
pip install python-dotenv sqlalchemy pydantic
pip install fastapi uvicorn streamlit
pip install requests beautifulsoup4 httpx
pip install pandas openpyxl jinja2 apscheduler
```

### 2. Configuration
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env si nécessaire (optionnel)
# nano .env
```

### 3. Initialisation
```bash
# Créer la base de données
python run.py --init-db

# Ajouter des données d'exemple (optionnel)
python seed.py
```

## 🧪 Tests par Fonctionnalité

### Test 1: Interface Utilisateur
```bash
# Lancer l'interface Streamlit
python run.py --ui
```
- Ouvrir http://localhost:8501
- Tester le formulaire de recherche
- Vérifier l'affichage des prospects

### Test 2: Collecte de Données
```bash
# Collecte simple
python run.py --collect --locations "Toulouse" --categories "coiffeur" --limit 3 --lang fr
```

### Test 3: Exports
```bash
# Après collecte, exporter
python run.py --export csv
python run.py --export xlsx
```

### Test 4: Génération d'Emails
```bash
# Générer les emails pour les prospects existants
python run.py --generate-emails
```

### Test 5: Tests Unitaires
```bash
# Lancer les tests
pytest tests/
```

## 🔍 Tests Avancés

### Test du Scheduler
```bash
# Mode automatique (attention: tourne en continu)
python run.py
# Ctrl+C pour arrêter
```

### Test avec API externe (si configurée)
```bash
# Éditer .env pour ajouter:
# SERPAPI_KEY=votre_clé_api
# APIFY_TOKEN=votre_token

# Puis relancer la collecte
python run.py --collect --locations "London" --categories "hairdresser" --limit 2 --lang en
```

## 📊 Vérifications

### Base de Données
```bash
# Vérifier les données
python -c "
from app.db.session import SessionLocal
from app.models.prospect import Prospect
db = SessionLocal()
prospects = db.query(Prospect).all()
print(f'Nombre de prospects: {len(prospects)}')
for p in prospects[:3]:
    print(f'- {p.business_name} ({p.location}) - Score: {p.opportunity_score}')
db.close()
"
```

### Logs
```bash
# Vérifier les logs
tail -f logs/app.log
```

## 🐛 Dépannage

### Erreur "ModuleNotFoundError"
```bash
pip install python-dotenv sqlalchemy pydantic fastapi
```

### Erreur Base de Données
```bash
# Supprimer l'ancienne DB
rm data/local_lead_finder.db
python run.py --init-db
```

### Interface ne se lance pas
```bash
pip install streamlit
python -c "import streamlit; print('Streamlit OK')"
```

### Collecte échoue
- Vérifier la connexion internet
- Tester avec moins de prospects: `--limit 1`
- Vérifier les logs dans `logs/app.log`

## ✅ Critères de Succès

- [ ] Interface Streamlit s'ouvre
- [ ] Formulaire de recherche fonctionne
- [ ] Collecte trouve des prospects
- [ ] Emails sont générés
- [ ] Export CSV/XLSX fonctionne
- [ ] Base de données contient des données
- [ ] Tests unitaires passent (au moins 3/4)

## 🎯 Tests Fonctionnels Recommandés

1. **Test Complet**: Toulouse + coiffeur + 5 prospects
2. **Test Multi-localisations**: Toulouse,Montpellier + coiffeur,plombier
3. **Test Export**: Vérifier colonnes et format
4. **Test Email**: Vérifier personnalisation par métier
5. **Test Interface**: Navigation et filtres

---

**Temps estimé pour tests complets**: 15-30 minutes
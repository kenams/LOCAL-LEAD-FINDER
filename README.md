# Local Lead Finder

Un outil automatisé pour trouver des prospects locaux potentiels pour des refontes de sites web de petites entreprises.

## Fonctionnalités

- Recherche automatique de prospects dans plusieurs localisations
- Analyse heuristique des sites web
- Extraction automatique des contacts (email, téléphone)
- Estimation de faisabilité et prix
- Génération d'emails de prospection personnalisés (FR/EN)
- Export CSV/XLSX
- Interface web simple avec Streamlit
- Planification automatique des recherches
- Architecture modulaire avec providers interchangeables

## Installation

1. Cloner le projet
2. Créer un environnement virtuel :
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```
3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
4. Copier le fichier d'environnement :
   ```bash
   cp .env.example .env
   ```
5. Initialiser la base de données :
   ```bash
   python run.py --init-db
   ```

## Configuration

Éditer le fichier `.env` pour configurer :
- Clés API (optionnelles)
- Paramètres par défaut
- Chemins de logs et exports

## Lancement

### Interface Web
```bash
python run.py --ui
```
Accéder à http://localhost:8501

### Collecte manuelle
```bash
python run.py --collect --locations "Toulouse,Montpellier" --categories "coiffeur,plombier" --limit 5 --lang fr
```

### Génération d'emails
```bash
python run.py --generate-emails
```

### Export
```bash
python run.py --export csv
python run.py --export xlsx
```

### Mode automatique (scheduler)
```bash
python run.py
```

## Structure du projet

```
/app
  /api          # Endpoints FastAPI
  /core         # Configuration et settings
  /db           # Gestion base de données
  /models       # Modèles SQLAlchemy
  /schemas      # Schémas Pydantic
  /services     # Logique métier
  /integrations # Intégrations externes (Netlify placeholder)
  /templates    # Templates d'emails
  /utils        # Utilitaires
/tests          # Tests unitaires
/data           # Base de données SQLite
/exports        # Exports CSV/XLSX
/logs           # Logs
```

## Providers

Le système utilise une architecture provider-based :

- **SimpleProvider** : Recherche via moteur de recherche classique (fallback)
- **SerpApiProvider** : Via SerpApi (nécessite clé)
- **ApifyProvider** : Via Apify (nécessite token)
- **ManualProvider** : Import CSV manuel

## Estimation et Scoring

- **Site Quality Score** : Analyse heuristique du site (0-100)
- **Opportunity Score** : Potentiel de conversion (0-100)
- **Faisabilité** : EASY/MEDIUM/ADVANCED
- **Prix estimé** : Fourchette basée sur complexité

## Tests

```bash
pytest tests/
```

## Limites et Éthique

- Respecter les CGU des sources utilisées
- Vérification humaine avant envoi d'emails
- Éviter l'envoi massif non contrôlé
- Usage professionnel uniquement

## Évolutions possibles

- Intégration Netlify pour déploiement automatique
- Plus de providers (Google Maps API, etc.)
- Analyse IA du design
- Intégration CRM
- Dashboard analytics

## Support

Pour les questions, créer une issue sur le repository.
# LOCAL LEAD FINDER

Machine de prospection autonome orientee qualite.

Le produit est maintenant centre sur un flux simple :

`SEARCH -> ANALYSE -> EMAIL -> REPORT`

Le mode de production actuel est `email-only`.
Si un lead n'a pas d'email exploitable, il est ignore.

## Ce que fait le programme

- recherche des leads par zones et categories
- enrichit les sites et extrait les emails
- filtre les leads faibles
- score les opportunites
- choisit l'offre la plus adaptee :
  - `landing page`
  - `site vitrine`
- genere les emails automatiquement
- envoie les emails en mode autonome
- enregistre les rapports et les logs

## Interface

L'interface Streamlit sert surtout de moniteur d'automatisation :

- statut de l'automatisation
- prochain run
- dernier run
- rapports
- logs
- suivi business
- mode debug secondaire

## Lancement rapide

### Interface web

```powershell
python run.py --ui
```

### Run autonome one-shot

```powershell
python run.py --auto-outreach
```

### Dry run

```powershell
python run.py --auto-outreach --dry-run
```

### Diagnostic SMTP

```powershell
python run.py --check-smtp
```

## Installation

1. Creer un environnement virtuel

```powershell
python -m venv venv
venv\Scripts\activate
```

2. Installer les dependances

```powershell
pip install -r requirements.txt
```

3. Copier la config

```powershell
copy .env.example .env
```

4. Initialiser la base

```powershell
python run.py --init-db
```

## Configuration importante

Dans `.env`, verifier surtout :

- `AUTO_MODE_ENABLED`
- `AUTO_MODE_CRON`
- `AUTO_MODE_LOCATIONS`
- `AUTO_MODE_CATEGORIES`
- `AUTO_MODE_LIMIT`
- `AUTO_SEND_ENABLED`
- `EMAIL_ONLY_OUTREACH`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`

## Production Windows

Le mode recommande en production est :

`Windows Task Scheduler -> wrapper PowerShell -> one-shot auto outreach -> exit`

Voir le guide :

- `WINDOWS_TASK_SCHEDULER.md`

Wrappers disponibles :

- `scripts/run_auto_outreach.ps1`
- `scripts/run_auto_outreach_prod.ps1`

## Tests

```powershell
pytest tests/
```

## Structure utile

- `run.py` : entree principale CLI
- `app/services/lead_service.py` : orchestration principale
- `app/services/email_generator.py` : generation des offres et emails
- `app/services/email_sender.py` : envoi SMTP
- `app/services/scheduler_service.py` : etat de planification
- `app/ui/streamlit_app.py` : interface de monitoring

## Etat actuel

- mode autonome stable
- envoi email actif
- SMS retire du flux produit actuel
- Streamlit francise
- taches Windows prêtes

# Windows Task Scheduler Setup

This project is designed to run in production as a one-shot task:

`Windows Task Scheduler -> run script -> auto outreach once -> save logs/reports -> exit`

## Recommended command

Use the PowerShell wrapper:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER\scripts\run_auto_outreach.ps1"
```

For the current production rollout on Windows, use the production wrapper:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER\scripts\run_auto_outreach_prod.ps1"
```

## What the wrapper does

- switches to the project root
- uses `venv\Scripts\python.exe` or `.venv\Scripts\python.exe`
- runs `python run.py --auto-outreach`
- writes a dedicated log file in `logs\runs\`
- exits with the Python process exit code

The production wrapper additionally forces safe rollout settings:

- `AUTO_SEND_ENABLED=true`
- `EMAIL_ONLY_OUTREACH=true`
- `SEND_MAX_PER_RUN=5`
- `SEND_BATCH_SIZE=5`
- `AUTO_MODE_REQUIRE_EMAIL_AND_PHONE=false`
- mockup generation and Netlify deployment disabled

## One-shot CLI commands

Real execution:

```powershell
python run.py --auto-outreach
```

Safe dry run:

```powershell
python run.py --auto-outreach --dry-run
```

Dry run through the wrapper:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER\scripts\run_auto_outreach.ps1" --dry-run --locations "Geneva" --categories "marketing,consultant" --limit 1
```

## Task Scheduler settings

Create the production tasks with:

- Trigger:
  daily at `09:00` and `18:00`
- Action:
  start a program
- Program/script:
  `powershell.exe`
- Add arguments:
  `-ExecutionPolicy Bypass -File "C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER\scripts\run_auto_outreach_prod.ps1"`
- Start in:
  `C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER`

Recommended options:

- Run whether user is logged on or not when possible
- Run with highest privileges
- Run task as soon as possible after a scheduled start is missed
- Wake the computer to run this task
- If the task fails, retry according to your Windows policy

## Sleep and missed-run behavior

Current recommended behavior:

- if the PC is asleep at `09:00` or `18:00`, Task Scheduler can wake it to run the task
- if a scheduled start is missed, Windows should run it as soon as possible afterward
- if the PC is completely powered off, nothing can run until Windows starts again
- a separate logon catch-up script still exists as an extra safety net after sign-in

Important note:

- wake timers must be allowed by Windows power settings
- on the current machine, wake timers are enabled on AC power and disabled on battery
- in practice, scheduled wake is reliable when the PC is plugged in

## Environment variables

The project loads `.env` automatically through `python-dotenv`.

Before enabling the task, verify:

- SMTP configuration is complete
- `AUTO_SEND_ENABLED=true`
- `REQUIRE_WEBSITE=true`
- `REQUIRE_CONTACT=true`
- `PRIORITY_NICHES_ENABLED=true`
- `AUTO_MODE_CATEGORIES` is set to your B2B niches
- `EMAIL_ONLY_OUTREACH=true`
- `AUTO_MODE_GENERATE_MOCKUPS=false` unless you explicitly want local mockups during auto mode
- `AUTO_MODE_DEPLOY_MOCKUPS=false` unless you explicitly want Netlify deployment during auto mode

Each one-shot run prints a compact preflight summary into the console and the per-run log file. This makes scheduled-mode diagnosis easier when SMTP or mockup deployment are not ready yet.

## Output locations

- Main application log:
  `logs\app.log`
- Per-run scheduled logs:
  `logs\runs\`
- JSON/CSV reports:
  `reports\`

## Expected behavior

Each scheduled run should:

1. load config
2. search leads
3. enrich and score them
4. choose `email` or `skipped`
5. send automatically by email
6. save logs
7. save a report
8. exit cleanly

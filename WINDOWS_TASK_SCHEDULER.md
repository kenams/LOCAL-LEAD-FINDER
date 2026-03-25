# Windows Task Scheduler Setup

This project is designed to run in production as a one-shot task:

`Windows Task Scheduler -> run script -> auto outreach once -> save logs/reports -> exit`

## Recommended command

Use the PowerShell wrapper:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER\scripts\run_auto_outreach.ps1"
```

## What the wrapper does

- switches to the project root
- uses `venv\Scripts\python.exe` or `.venv\Scripts\python.exe`
- runs `python run.py --auto-outreach`
- writes a dedicated log file in `logs\runs\`
- exits with the Python process exit code

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
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER\scripts\run_auto_outreach.ps1" --dry-run --locations "Geneva" --categories "coiffeur" --limit 1
```

## Task Scheduler settings

Create a new task with:

- Trigger:
  every 2 days
- Action:
  start a program
- Program/script:
  `powershell.exe`
- Add arguments:
  `-ExecutionPolicy Bypass -File "C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER\scripts\run_auto_outreach.ps1"`
- Start in:
  `C:\Users\kenam\Application-Projet-K\LOCAL LEAD FINDER`

Recommended options:

- Run whether user is logged on or not
- Run with highest privileges
- If the task fails, retry according to your Windows policy

## Environment variables

The project loads `.env` automatically through `python-dotenv`.

Before enabling the task, verify:

- SMTP configuration is complete
- SMS provider configuration is complete if SMS should be sent
- `AUTO_SEND_ENABLED=true`
- `AUTO_MODE_GENERATE_MOCKUPS=false` unless you explicitly want local mockups during auto mode
- `AUTO_MODE_DEPLOY_MOCKUPS=false` unless you explicitly want Netlify deployment during auto mode

Each one-shot run prints a compact preflight summary into the console and the per-run log file. This makes scheduled-mode diagnosis easier when SMTP, SMS, or mockup deployment are not ready yet.

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
4. choose `email`, `sms`, or `skipped`
5. send automatically
6. save logs
7. save a report
8. exit cleanly

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CatchupScript = Join-Path $ScriptDir "run_auto_outreach_startup_catchup.ps1"

if (-not (Test-Path $CatchupScript)) {
    throw "Catch-up script not found: $CatchupScript"
}

Start-Sleep -Seconds 1800
& $CatchupScript
exit $LASTEXITCODE

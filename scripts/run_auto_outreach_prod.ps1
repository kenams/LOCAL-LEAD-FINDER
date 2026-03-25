$ErrorActionPreference = "Stop"

$CliArgs = @($args)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseWrapper = Join-Path $ScriptDir "run_auto_outreach.ps1"

if (-not (Test-Path $BaseWrapper)) {
    throw "Base wrapper not found: $BaseWrapper"
}

# Safe rollout defaults for scheduled production runs.
$env:AUTO_SEND_ENABLED = "true"
$env:SEND_MAX_PER_RUN = "5"
$env:SEND_BATCH_SIZE = "5"
$env:AUTO_MODE_SMS_ENABLED = "false"
$env:AUTO_MODE_REQUIRE_EMAIL_AND_PHONE = "true"
$env:AUTO_MODE_CONTACT_CANDIDATE_MULTIPLIER = "12"
$env:AUTO_MODE_GENERATE_MOCKUPS = "false"
$env:AUTO_MODE_DEPLOY_MOCKUPS = "false"

& $BaseWrapper @CliArgs
exit $LASTEXITCODE

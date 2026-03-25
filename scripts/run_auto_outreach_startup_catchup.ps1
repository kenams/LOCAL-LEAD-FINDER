$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$ProdWrapper = Join-Path $ScriptDir "run_auto_outreach_prod.ps1"
$ReportsDir = Join-Path $ProjectRoot "reports"
$RunLogsDir = Join-Path $ProjectRoot "logs\runs"

if (-not (Test-Path $ProdWrapper)) {
    throw "Production wrapper not found: $ProdWrapper"
}

New-Item -ItemType Directory -Force -Path $RunLogsDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $RunLogsDir "startup_catchup_$Timestamp.log"
$Today = (Get-Date).Date

Write-Output "Starting startup catch-up check from $ProjectRoot" | Tee-Object -FilePath $LogFile -Append
Write-Output "Current local time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $LogFile -Append

$TodayReports = @()
if (Test-Path $ReportsDir) {
    $TodayReports = Get-ChildItem $ReportsDir -Filter "*_one_shot_auto_outreach.json" -File | Where-Object {
        $_.LastWriteTime.Date -eq $Today
    }
}

if ($TodayReports.Count -gt 0) {
    Write-Output "Skipping startup catch-up because a report already exists for today." | Tee-Object -FilePath $LogFile -Append
    $TodayReports | Sort-Object LastWriteTime -Descending | Select-Object -First 3 Name, LastWriteTime | Format-Table -AutoSize | Out-String | Tee-Object -FilePath $LogFile -Append | Out-Null
    exit 0
}

Write-Output "No report found for today. Launching autonomous outreach catch-up run." | Tee-Object -FilePath $LogFile -Append
& $ProdWrapper
$ExitCode = $LASTEXITCODE
Write-Output "Startup catch-up exit code: $ExitCode" | Tee-Object -FilePath $LogFile -Append
exit $ExitCode

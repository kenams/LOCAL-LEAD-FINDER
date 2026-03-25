$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found in venv or .venv."
}

$RunLogsDir = Join-Path $ProjectRoot "logs\runs"
New-Item -ItemType Directory -Force -Path $RunLogsDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path $RunLogsDir "task_scheduler_$Timestamp.log"

Write-Output "Starting auto outreach run from $ProjectRoot" | Tee-Object -FilePath $LogFile -Append
Write-Output "Using Python: $PythonExe" | Tee-Object -FilePath $LogFile -Append

& $PythonExe "run.py" "--auto-outreach" 2>&1 | Tee-Object -FilePath $LogFile -Append
$ExitCode = $LASTEXITCODE

Write-Output "Auto outreach exit code: $ExitCode" | Tee-Object -FilePath $LogFile -Append
exit $ExitCode

$CliArgs = @($args)

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
$StdOutFile = Join-Path $RunLogsDir "task_scheduler_$Timestamp.stdout.log"
$StdErrFile = Join-Path $RunLogsDir "task_scheduler_$Timestamp.stderr.log"

Write-Output "Starting auto outreach run from $ProjectRoot" | Tee-Object -FilePath $LogFile -Append
Write-Output "Using Python: $PythonExe" | Tee-Object -FilePath $LogFile -Append

if ($CliArgs.Length -gt 0) {
    Write-Output "Additional CLI args: $($CliArgs -join ' ')" | Tee-Object -FilePath $LogFile -Append
}

$ProcessArgs = @("run.py", "--auto-outreach") + $CliArgs

$Process = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList $ProcessArgs `
    -WorkingDirectory $ProjectRoot `
    -NoNewWindow `
    -PassThru `
    -Wait `
    -RedirectStandardOutput $StdOutFile `
    -RedirectStandardError $StdErrFile

if (Test-Path $StdOutFile) {
    Get-Content $StdOutFile | Tee-Object -FilePath $LogFile -Append
}
if (Test-Path $StdErrFile) {
    Get-Content $StdErrFile | Tee-Object -FilePath $LogFile -Append
}

$ExitCode = $Process.ExitCode

Write-Output "Auto outreach exit code: $ExitCode" | Tee-Object -FilePath $LogFile -Append
Remove-Item -ErrorAction SilentlyContinue $StdOutFile, $StdErrFile
exit $ExitCode

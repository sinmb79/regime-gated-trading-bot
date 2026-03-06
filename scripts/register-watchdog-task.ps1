[CmdletBinding()]
param(
    [string]$TaskName = "BossTradingWatchdog",
    [string]$Config = "configs/default.json",
    [string]$ListenHost = "127.0.0.1",
    [int]$ListenPort = 8000,
    [int]$IntervalSeconds = 15
)

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -Path (Split-Path -Parent $PSScriptRoot)).Path
if (-not [System.IO.Path]::IsPathRooted($Config)) {
    $Config = Join-Path $rootPath $Config
}

$launcher = Join-Path $rootPath "start-system.bat"
$cmd = "`"$launcher`" watchdog `"$Config`" $ListenHost $ListenPort $IntervalSeconds"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $cmd"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "watchdog 작업 등록 완료: $TaskName"

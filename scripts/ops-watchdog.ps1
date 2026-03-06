[CmdletBinding()]
param(
    [string]$Config = "configs/default.json",
    [string]$ListenHost = "127.0.0.1",
    [int]$ListenPort = 8000,
    [int]$CheckIntervalSeconds = 15,
    [int]$RestartCooldownSeconds = 20
)

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -Path (Split-Path -Parent $PSScriptRoot)).Path
if (-not [System.IO.Path]::IsPathRooted($Config)) {
    $Config = Join-Path $rootPath $Config
}

$checkInterval = [Math]::Max(3, [int]$CheckIntervalSeconds)
$restartCooldown = [Math]::Max(5, [int]$RestartCooldownSeconds)
$statusUrl = "http://$ListenHost`:$ListenPort/api/status"
$lastRestartAt = [DateTime]::MinValue

function Write-WatchdogLog {
    param([string]$Message)
    $ts = [DateTime]::Now.ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $Message"
    Write-Host $line
    $logDir = Join-Path $rootPath "logs"
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
    Add-Content -Path (Join-Path $logDir "watchdog.log") -Value $line -Encoding UTF8
}

function Test-DashboardAlive {
    try {
        $status = Invoke-RestMethod -Uri $statusUrl -Method Get -TimeoutSec 4
        return ($null -ne $status)
    }
    catch {
        return $false
    }
}

function Start-DashboardWeb {
    $launcher = Join-Path $rootPath "start-system.bat"
    $args = @(
        "web",
        $Config,
        $ListenHost,
        "$ListenPort"
    )
    Start-Process -FilePath $launcher -ArgumentList $args -WorkingDirectory $rootPath -WindowStyle Minimized | Out-Null
}

Write-WatchdogLog "watchdog started (host=$ListenHost port=$ListenPort interval=${checkInterval}s cooldown=${restartCooldown}s)"

while ($true) {
    $alive = Test-DashboardAlive
    if ($alive) {
        Start-Sleep -Seconds $checkInterval
        continue
    }

    $elapsed = ([DateTime]::UtcNow - $lastRestartAt).TotalSeconds
    if ($elapsed -lt $restartCooldown) {
        Write-WatchdogLog "dashboard unreachable but restart cooldown active (${elapsed:n1}s/${restartCooldown}s)"
        Start-Sleep -Seconds $checkInterval
        continue
    }

    Write-WatchdogLog "dashboard unreachable -> restarting web dashboard"
    try {
        Start-DashboardWeb
        $lastRestartAt = [DateTime]::UtcNow
    }
    catch {
        Write-WatchdogLog "restart failed: $($_.Exception.Message)"
    }

    Start-Sleep -Seconds $checkInterval
}

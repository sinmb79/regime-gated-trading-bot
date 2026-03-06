[CmdletBinding()]
param(
    [string]$Config = "configs/default.json",
    [string]$ListenHost = "127.0.0.1",
    [int]$ListenPort = 8000,
    [switch]$IncludeReadiness
)

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -Path (Split-Path -Parent $PSScriptRoot)).Path
if (-not [System.IO.Path]::IsPathRooted($Config)) {
    $Config = Join-Path $rootPath $Config
}

$result = @{
    timestamp = [DateTime]::UtcNow.ToString("o")
    dashboard = @{
        host = $ListenHost
        port = $ListenPort
        reachable = $false
        running = $false
        mode = ""
        cycle_count = 0
    }
    readiness = $null
    checks = @()
    overall_passed = $false
}

function Add-Check {
    param(
        [string]$Code,
        [bool]$Passed,
        [string]$Detail
    )
    $script:result.checks += @{
        code = $Code
        passed = $Passed
        detail = $Detail
    }
}

$statusUrl = "http://$ListenHost`:$ListenPort/api/status"
try {
    $status = Invoke-RestMethod -Uri $statusUrl -Method Get -TimeoutSec 4
    $result.dashboard.reachable = $true
    $result.dashboard.running = [bool]$status.running
    $result.dashboard.mode = [string]$status.mode
    $result.dashboard.cycle_count = [int]($status.cycle_count | ForEach-Object { $_ })
    Add-Check -Code "dashboard_status_api" -Passed $true -Detail "status api reachable"
}
catch {
    Add-Check -Code "dashboard_status_api" -Passed $false -Detail $_.Exception.Message
}

if ($IncludeReadiness) {
    $env:PYTHONPATH = Join-Path $rootPath "src"
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    $exe = $null
    $args = @()
    if ($pyCmd) {
        $exe = $pyCmd.Source
        $args += "-3"
    } elseif ($pythonCmd) {
        $exe = $pythonCmd.Source
    }

    if ($exe) {
        try {
            $jsonText = (& $exe @($args + @("-m", "trading_system.main", "--config", $Config, "--live-readiness")) | Out-String).Trim()
            $payload = $jsonText | ConvertFrom-Json -ErrorAction Stop
            $result.readiness = $payload
            Add-Check -Code "live_readiness_cli" -Passed ([bool]$payload.overall_passed) -Detail "live readiness executed"
        }
        catch {
            Add-Check -Code "live_readiness_cli" -Passed $false -Detail $_.Exception.Message
        }
    } else {
        Add-Check -Code "live_readiness_cli" -Passed $false -Detail "python launcher not found"
    }
}

$allPassed = $true
foreach ($c in $result.checks) {
    if (-not [bool]$c.passed) {
        $allPassed = $false
        break
    }
}
$result.overall_passed = $allPassed

$json = $result | ConvertTo-Json -Depth 10
Write-Output $json

if (-not $allPassed) {
    exit 1
}

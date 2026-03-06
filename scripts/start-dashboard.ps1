[CmdletBinding()]
param(
    [string]$Config = "configs/default.json",
    [string]$ListenHost = "127.0.0.1",
    [int]$ListenPort = 8000
)

$runner = Join-Path $PSScriptRoot 'run-trading-system.ps1'
& (Resolve-Path $runner) -Mode web -Config $Config -ListenHost $ListenHost -ListenPort $ListenPort

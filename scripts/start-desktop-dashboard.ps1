[CmdletBinding()]
param(
    [string]$Config = "configs/default.json"
)

$runner = Join-Path $PSScriptRoot 'run-trading-system.ps1'
& (Resolve-Path $runner) -Mode desktop -Config $Config

[CmdletBinding()]
param(
    [string]$MultiConfig = "configs/multi_accounts.sample.json",
    [string]$ListenHost = "127.0.0.1",
    [int]$ListenPort = 8100
)

$runner = Join-Path $PSScriptRoot 'run-trading-system.ps1'
& (Resolve-Path $runner) -Mode multi-ui -MultiConfig $MultiConfig -ListenHost $ListenHost -ListenPort $ListenPort

[CmdletBinding()]
param(
    [string]$MultiConfig = "configs/multi_accounts.sample.json",
    [ValidateSet('status', 'run-once', 'loop')]
    [string]$MultiCommand = "loop",
    [int]$MultiInterval = 0,
    [string]$MultiLiveToken = ""
)

$runner = Join-Path $PSScriptRoot 'run-trading-system.ps1'
& (Resolve-Path $runner) -Mode multi -MultiConfig $MultiConfig -MultiCommand $MultiCommand -MultiInterval $MultiInterval -MultiLiveToken $MultiLiveToken

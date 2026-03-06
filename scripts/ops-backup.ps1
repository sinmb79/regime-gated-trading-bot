[CmdletBinding()]
param(
    [string]$OutputDir = "backups",
    [switch]$IncludeLogs = $true
)

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -Path (Split-Path -Parent $PSScriptRoot)).Path
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $rootPath $OutputDir
}
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
New-Item -Path $OutputDir -ItemType Directory -Force | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$stagingDir = Join-Path $OutputDir "backup_stage_$ts"
$bundleDir = Join-Path $stagingDir "trading_system_backup"
$zipPath = Join-Path $OutputDir "trading_system_backup_$ts.zip"

New-Item -Path $bundleDir -ItemType Directory -Force | Out-Null

function Copy-IfExists {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DestPath
    )
    if (Test-Path -Path $SourcePath) {
        New-Item -Path (Split-Path -Parent $DestPath) -ItemType Directory -Force | Out-Null
        Copy-Item -Path $SourcePath -Destination $DestPath -Recurse -Force
        return $true
    }
    return $false
}

$manifest = @{
    timestamp = [DateTime]::UtcNow.ToString("o")
    root = $rootPath
    entries = @()
}

$pathsToBackup = @(
    @{ Source = (Join-Path $rootPath "configs"); Dest = (Join-Path $bundleDir "configs") },
    @{ Source = (Join-Path $rootPath "docs"); Dest = (Join-Path $bundleDir "docs") },
    @{ Source = (Join-Path $rootPath "data"); Dest = (Join-Path $bundleDir "data") },
    @{ Source = (Join-Path $rootPath "README.md"); Dest = (Join-Path $bundleDir "README.md") }
)

if ($IncludeLogs) {
    $pathsToBackup += @{ Source = (Join-Path $rootPath "logs"); Dest = (Join-Path $bundleDir "logs") }
}

foreach ($entry in $pathsToBackup) {
    $ok = Copy-IfExists -SourcePath $entry.Source -DestPath $entry.Dest
    $manifest.entries += @{
        source = $entry.Source
        destination = $entry.Dest
        copied = $ok
    }
}

$manifestPath = Join-Path $bundleDir "backup_manifest.json"
($manifest | ConvertTo-Json -Depth 10) | Set-Content -Path $manifestPath -Encoding UTF8

if (Test-Path -Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}
Compress-Archive -Path (Join-Path $bundleDir "*") -DestinationPath $zipPath -Force

Remove-Item -Path $stagingDir -Recurse -Force

Write-Host "백업 완료: $zipPath"

[CmdletBinding()]
param(
    [string]$OutputDir = "dist",
    [string]$PackageName = "boss-trading-system-deploy",
    [switch]$CleanOutput = $true
)

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -Path (Split-Path -Parent $PSScriptRoot)).Path
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $rootPath $OutputDir
}
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)

$stagingDir = Join-Path $OutputDir $PackageName
$zipPath = Join-Path $OutputDir ("{0}.zip" -f $PackageName)

function Get-TrackedFiles {
    $gitArgs = @(
        "-c", "safe.directory=$rootPath",
        "-C", $rootPath,
        "ls-files"
    )
    $lines = & git @gitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git ls-files failed (exit code=$LASTEXITCODE)"
    }
    return @($lines | Where-Object { $_ -and $_.Trim() })
}

function Test-IncludedTrackedPath {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $path = ($RelativePath -replace "\\", "/").TrimStart("./")
    if (-not $path) {
        return $false
    }

    $includePrefixes = @(
        "configs/",
        "docs/",
        "scripts/",
        "src/"
    )
    foreach ($prefix in $includePrefixes) {
        if ($path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    $includeExact = @(
        ".gitignore",
        "README.md",
        "requirements.txt",
        "install-system.bat",
        "start-dashboard-oneclick.bat",
        "start-multi-dashboard.bat",
        "start-multi-system.bat",
        "start-nogate-preset.bat",
        "start-system.bat"
    )
    return $includeExact -contains $path
}

function Copy-TrackedFiles {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$DestinationRoot
    )

    foreach ($relative in Get-TrackedFiles) {
        if (-not (Test-IncludedTrackedPath -RelativePath $relative)) {
            continue
        }
        $sourcePath = Join-Path $SourceRoot $relative
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            continue
        }

        $destinationPath = Join-Path $DestinationRoot $relative
        $destinationDir = Split-Path -Parent $destinationPath
        if ($destinationDir) {
            New-Item -Path $destinationDir -ItemType Directory -Force | Out-Null
        }
        Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
    }
}

if ($CleanOutput -and (Test-Path -Path $stagingDir)) {
    Remove-Item -Path $stagingDir -Recurse -Force
}

New-Item -Path $stagingDir -ItemType Directory -Force | Out-Null
Copy-TrackedFiles -SourceRoot $rootPath -DestinationRoot $stagingDir

$installBat = @'
@echo off
setlocal
set "ROOT=%~dp0"
echo 보스 AI 트레이딩 시스템 설치를 시작합니다.
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\install-trading-system.ps1" -InstallDir "%LOCALAPPDATA%\BossTradingSystem" -CreateDesktopShortcuts -OverwriteExisting
if errorlevel 1 (
  echo 설치 실패. 창을 닫기 전에 메시지를 확인하세요.
  pause
  exit /b 1
)
echo 설치 완료.
echo 바탕화면 바로가기로 실행 가능합니다.
pause
exit /b 0
'@
$installBat | Set-Content -Path (Join-Path $stagingDir "install.bat") -Encoding ASCII

$readme = @'
보스 AI 트레이딩 시스템 배포 패키지

1) install.bat 실행
2) 바탕화면에 생성된 바로가기로 실행
   - 보스 AI 트레이딩 데스크톱
   - 보스 AI 트레이딩 웹
   - 보스 AI 트레이딩 멀티 런타임
   - 보스 AI 트레이딩 멀티 대시보드
   - 보스 AI 트레이딩 Watchdog

가상환경은 첫 실행 시 자동으로 복구됩니다.
'@
$readme | Set-Content -Path (Join-Path $stagingDir "README_INSTALL.txt") -Encoding UTF8

if (Test-Path -Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath -Force

Write-Host "배포 패키지 생성 완료"
Write-Host "폴더: $stagingDir"
Write-Host "ZIP: $zipPath"

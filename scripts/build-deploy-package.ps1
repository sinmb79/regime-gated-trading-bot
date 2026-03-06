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

function Invoke-Robocopy {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    $excludeDirs = @(
        ".git",
        ".venv",
        "dist",
        "logs",
        "data",
        "__pycache__"
    )
    $excludeFiles = @(
        "*.pyc",
        "*.pyo"
    )
    $args = @(
        $Source,
        $Destination,
        "/E",
        "/R:1",
        "/W:1",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP"
    )
    foreach ($dirName in $excludeDirs) {
        $args += @("/XD", (Join-Path $Source $dirName))
    }
    foreach ($filePattern in $excludeFiles) {
        $args += @("/XF", $filePattern)
    }
    & robocopy @args | Out-Null
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        throw "파일 복사 실패(robocopy exit code=$code)"
    }
}

if ($CleanOutput -and (Test-Path -Path $stagingDir)) {
    Remove-Item -Path $stagingDir -Recurse -Force
}

New-Item -Path $stagingDir -ItemType Directory -Force | Out-Null
Invoke-Robocopy -Source $rootPath -Destination $stagingDir

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
echo 바탕화면 바로가기에서 실행 가능합니다.
pause
exit /b 0
'@
$installBat | Set-Content -Path (Join-Path $stagingDir "install.bat") -Encoding ASCII

$readme = @'
보스 AI 트레이딩 시스템 배포 패키지

1) install.bat 실행
2) 바탕화면 생성 아이콘으로 실행
   - 보스 AI 트레이딩 데스크톱
   - 보스 AI 트레이딩 웹
   - 보스 AI 트레이딩 멀티운용
   - 보스 AI 트레이딩 멀티 대시보드
   - 보스 AI 트레이딩 Watchdog

의존성/가상환경은 첫 실행 시 자동 복구됩니다.
'@
$readme | Set-Content -Path (Join-Path $stagingDir "README_INSTALL.txt") -Encoding UTF8

if (Test-Path -Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}
Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath -Force

Write-Host "배포 패키지 생성 완료"
Write-Host "폴더: $stagingDir"
Write-Host "ZIP: $zipPath"

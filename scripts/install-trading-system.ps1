[CmdletBinding()]
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\BossTradingSystem",
    [switch]$CreateDesktopShortcuts = $true,
    [switch]$OverwriteExisting,
    [switch]$StartDesktop
)

$ErrorActionPreference = "Stop"

$sourceRoot = (Resolve-Path -Path (Split-Path -Parent $PSScriptRoot)).Path
$installPath = [System.IO.Path]::GetFullPath($InstallDir)

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

function New-AppShortcut {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [string]$Arguments = "",
        [string]$WorkingDirectory = "",
        [string]$Description = ""
    )
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $TargetPath
    $shortcut.Arguments = $Arguments
    if ($WorkingDirectory) {
        $shortcut.WorkingDirectory = $WorkingDirectory
    }
    if ($Description) {
        $shortcut.Description = $Description
    }
    $shortcut.Save()
}

if (Test-Path -Path $installPath) {
    if (-not $OverwriteExisting) {
        throw "설치 경로가 이미 존재합니다: $installPath (덮어쓰려면 -OverwriteExisting 사용)"
    }
    Remove-Item -Path $installPath -Recurse -Force
}

New-Item -Path $installPath -ItemType Directory -Force | Out-Null
Invoke-Robocopy -Source $sourceRoot -Destination $installPath

foreach ($subDir in @("logs", "data", "data\validation")) {
    New-Item -Path (Join-Path $installPath $subDir) -ItemType Directory -Force | Out-Null
}

if ($CreateDesktopShortcuts) {
    try {
        $desktop = [Environment]::GetFolderPath("Desktop")
        $launcher = Join-Path $installPath "start-system.bat"
        New-AppShortcut `
            -Path (Join-Path $desktop "보스 AI 트레이딩 데스크톱.lnk") `
            -TargetPath $launcher `
            -Arguments "desktop" `
            -WorkingDirectory $installPath `
            -Description "보스 AI 트레이딩 데스크톱 대시보드"
        New-AppShortcut `
            -Path (Join-Path $desktop "보스 AI 트레이딩 웹.lnk") `
            -TargetPath $launcher `
            -Arguments "web" `
            -WorkingDirectory $installPath `
            -Description "보스 AI 트레이딩 웹 대시보드"
        New-AppShortcut `
            -Path (Join-Path $desktop "보스 AI 트레이딩 멀티운용.lnk") `
            -TargetPath $launcher `
            -Arguments "multi configs/multi_accounts.sample.json loop 5" `
            -WorkingDirectory $installPath `
            -Description "보스 AI 트레이딩 멀티 계정/전략 동시 운용"
        New-AppShortcut `
            -Path (Join-Path $desktop "보스 AI 트레이딩 멀티 대시보드.lnk") `
            -TargetPath $launcher `
            -Arguments "multi-ui configs/multi_accounts.sample.json 127.0.0.1 8100" `
            -WorkingDirectory $installPath `
            -Description "보스 AI 트레이딩 멀티 통합 대시보드"
        New-AppShortcut `
            -Path (Join-Path $desktop "보스 AI 트레이딩 Watchdog.lnk") `
            -TargetPath $launcher `
            -Arguments "watchdog configs/default.json 127.0.0.1 8000 15" `
            -WorkingDirectory $installPath `
            -Description "보스 AI 트레이딩 웹 대시보드 자동 재기동"
    }
    catch {
        Write-Warning "바탕화면 바로가기 생성 실패: $($_.Exception.Message)"
    }
}

Write-Host "설치 완료: $installPath"
Write-Host "실행: $installPath\start-system.bat"

if ($StartDesktop) {
    Start-Process -FilePath (Join-Path $installPath "start-system.bat") -ArgumentList "desktop" -WorkingDirectory $installPath
}

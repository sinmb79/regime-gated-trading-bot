[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('desktop', 'web', 'multi', 'multi-ui')]
    [string]$Mode,
    [string]$Config = "configs/default.json",
    [string]$ListenHost = "127.0.0.1",
    [int]$ListenPort = 8000,
    [string]$MultiConfig = "configs/multi_accounts.sample.json",
    [ValidateSet('status', 'run-once', 'loop')]
    [string]$MultiCommand = "loop",
    [int]$MultiInterval = 0,
    [string]$MultiLiveToken = "",
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = 'Stop'

$rootPath = Resolve-Path -Path (Split-Path -Parent $PSScriptRoot)
$venvDir = Join-Path $rootPath '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$requirementsFile = Join-Path $rootPath 'requirements.txt'
$pythonPath = Join-Path $rootPath 'src'

if (-not [System.IO.Path]::IsPathRooted($Config)) {
    $Config = Join-Path $rootPath $Config
}

if (($Mode -in @('desktop', 'web')) -and (-not (Test-Path -Path $Config -PathType Leaf))) {
    throw "설정 파일을 찾을 수 없습니다: $Config"
}

function Resolve-SystemPython {
    if ($env:TRADING_SYSTEM_PYTHON) {
        $candidate = Resolve-Path -Path $env:TRADING_SYSTEM_PYTHON -ErrorAction SilentlyContinue
        if ($candidate -and (Test-Path -Path $candidate.Path -PathType Leaf)) {
            return @{ Exe = $candidate.Path; Args = @() }
        }
        Write-Warning "TRADING_SYSTEM_PYTHON가 경로와 맞지 않습니다. 무시하고 기본 탐색으로 진행합니다: $($env:TRADING_SYSTEM_PYTHON)"
    }

    $command = Get-Command py -ErrorAction SilentlyContinue
    if ($command) {
        return @{ Exe = $command.Source; Args = @('-3') }
    }

    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) {
        return @{ Exe = $command.Source; Args = @() }
    }

    $command = Get-Command python3 -ErrorAction SilentlyContinue
    if ($command) {
        return @{ Exe = $command.Source; Args = @() }
    }

    throw 'Python 실행기를 찾을 수 없습니다. `TRADING_SYSTEM_PYTHON`, `py`, `python`를 확인하세요.'
}

function Invoke-Python {
    param(
        [hashtable]$Runtime,
        [string[]]$Arguments
    )
    & $Runtime.Exe @($Runtime.Args + $Arguments)
}

function Test-PythonRuntime {
    param(
        [string]$ExePath,
        [string[]]$Args = @()
    )

    if (-not $ExePath -or -not (Test-Path -Path $ExePath -PathType Leaf)) {
        return $false
    }

    try {
        & $ExePath @($Args + @('-c', 'import sys; sys.exit(0)')) *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Ensure-VenvAndDeps {
    if (Test-PythonRuntime -ExePath $venvPython) {
        $runtime = @{ Exe = $venvPython; Args = @() }
    } else {
        $runtime = Resolve-SystemPython
        $rebuildArgs = @('-m', 'venv')
        if (Test-Path -Path $venvDir -PathType Container) {
            Write-Warning "기존 .venv가 손상되어 재생성합니다: $venvDir"
            $rebuildArgs += '--clear'
        } else {
            Write-Host "가상환경이 없어서 생성합니다: $venvDir"
        }
        $rebuildArgs += $venvDir
        Invoke-Python -Runtime $runtime -Arguments $rebuildArgs

        if (-not (Test-PythonRuntime -ExePath $venvPython)) {
            throw 'venv 생성에 실패했습니다. Python 3.11+ 설치 및 권한을 확인하세요.'
        }

        $runtime = @{ Exe = $venvPython; Args = @() }
    }

    if (-not (Test-Path -Path $requirementsFile -PathType Leaf)) {
        throw "requirements.txt를 찾을 수 없습니다: $requirementsFile"
    }

    if ($SkipDependencyInstall) {
        return $runtime
    }

    $required = @('fastapi', 'uvicorn', 'pydantic', 'pandas', 'numpy', 'requests', 'ccxt')
    $missing = @()

    foreach ($module in $required) {
        $pythonExpr = "import importlib.util; print('1' if importlib.util.find_spec('$module') else '0')"
        $status = (Invoke-Python -Runtime $runtime -Arguments @('-c', $pythonExpr)).Trim()
        if ($status -ne '1') { $missing += $module }
    }

    if ($missing.Count -gt 0) {
        Write-Host "패키지 누락: $($missing -join ', ')"
        Write-Host "의존성 설치를 시작합니다. (최초 1회만 필요)"
        & $runtime.Exe @($runtime.Args + @('-m', 'pip', 'install', '-r', $requirementsFile))
        if ($LASTEXITCODE -ne 0) {
            throw '의존성 설치에 실패했습니다. 인터넷/권한/방화벽 상태를 확인한 뒤 다시 실행하세요.'
        }
    }

    return $runtime
}

Set-Location -Path $rootPath
$env:PYTHONPATH = $pythonPath

$runtime = Ensure-VenvAndDeps

if ($Mode -eq 'desktop') {
    Write-Host "보스 데스크톱 대시보드 실행: config=$Config"
    Invoke-Python -Runtime $runtime -Arguments @('-m', 'trading_system.main', '--ui-desktop', '--config', $Config)
} elseif ($Mode -eq 'web') {
    Write-Host "Boss web dashboard start: http://$ListenHost`:$ListenPort"
    Write-Host "config=$Config"
    Invoke-Python -Runtime $runtime -Arguments @('-m', 'trading_system.main', '--ui', '--config', $Config, '--host', $ListenHost, '--port', "${ListenPort}")
} elseif ($Mode -eq 'multi') {
    if (-not [System.IO.Path]::IsPathRooted($MultiConfig)) {
        $MultiConfig = Join-Path $rootPath $MultiConfig
    }
    if (-not (Test-Path -Path $MultiConfig -PathType Leaf)) {
        throw "Multi config file not found: $MultiConfig"
    }
    Write-Host "Boss multi runtime start: command=$MultiCommand config=$MultiConfig"
    $arguments = @('-m', 'trading_system.main', '--multi-config', $MultiConfig, '--multi-command', $MultiCommand)
    if ($MultiInterval -gt 0) {
        $arguments += @('--multi-interval', "$MultiInterval")
    }
    if ($MultiLiveToken) {
        $arguments += @('--multi-live-token', $MultiLiveToken)
    }
    Invoke-Python -Runtime $runtime -Arguments $arguments
} else {
    if (-not [System.IO.Path]::IsPathRooted($MultiConfig)) {
        $MultiConfig = Join-Path $rootPath $MultiConfig
    }
    if (-not (Test-Path -Path $MultiConfig -PathType Leaf)) {
        throw "Multi config file not found: $MultiConfig"
    }
    Write-Host "Boss multi dashboard start: http://$ListenHost`:$ListenPort"
    Invoke-Python -Runtime $runtime -Arguments @(
        '-m', 'trading_system.main',
        '--ui-multi',
        '--multi-config', $MultiConfig,
        '--host', $ListenHost,
        '--port', "${ListenPort}"
    )
}

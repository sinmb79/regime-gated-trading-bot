@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "CONFIG=%~1"
if "%CONFIG%"=="" set "CONFIG=configs\default.json"
set "HOST=%~2"
if "%HOST%"=="" set "HOST=127.0.0.1"
if /I "%HOST%"=="localhost" set "HOST=127.0.0.1"
set "PORT=%~3"
if "%PORT%"=="" set "PORT=8000"

set "PY="
where py >nul 2>nul
if !ERRORLEVEL!==0 set "PY=py"
if "%PY%"=="" (
  where python >nul 2>nul
  if !ERRORLEVEL!==0 set "PY=python"
)

if "%PY%"=="" (
  echo [오류] python 또는 py 실행기를 찾을 수 없습니다.
  echo Python 경로가 PATH에 등록되어 있는지 확인해 주세요.
  pause
  exit /b 1
)

if not exist "%CONFIG%" (
  echo [오류] 설정 파일을 찾을 수 없습니다: %CONFIG%
  pause
  exit /b 1
)

set "LOG_FILE=%CD%\logs\dashboard-start.log"
if not exist "%CD%\logs" mkdir "%CD%\logs"
set "PYTHONPATH=%CD%\src"

echo [1/5] Python 인터프리터 확인: %PY%
echo [2/5] 프로젝트 경로: %CD%
echo [3/5] 대시보드 의존성 확인...
%PY% -c "import trading_system.main" >nul 2>nul
if !ERRORLEVEL! neq 0 (
  echo 패키지 로드가 실패했습니다. requirements.txt를 설치합니다.
  %PY% -m pip install --disable-pip-version-check -r requirements.txt
  if !ERRORLEVEL! neq 0 (
    echo [오류] requirements 설치 실패.
    pause
    exit /b 1
  )
)

%PY% -c "import fastapi, uvicorn, trading_system.main" >nul 2>nul
if !ERRORLEVEL! neq 0 (
  echo [오류] fastapi/uvicorn 또는 trading_system.main 모듈 로드에 실패했습니다.
  echo 자세한 오류는 잠시 후 생성될 %LOG_FILE% 또는 Python 콘솔에서 확인해 주세요.
  pause
  exit /b 1
)
echo [4/5] 대시보드 실행 시작...
start "보스 AI 트레이딩 대시보드" /D "%CD%" cmd /c "\"%PY%\" -m trading_system.main --ui --config \"%CONFIG%\" --host %HOST% --port %PORT% >> \"%LOG_FILE%\" 2>&1"

echo [5/5] 포트 오픈 대기 후 브라우저 오픈을 시도합니다.

timeout /t 3 >nul
start "" "http://%HOST%:%PORT%"

echo 서버가 실행 중입니다: http://%HOST%:%PORT%
exit /b 0


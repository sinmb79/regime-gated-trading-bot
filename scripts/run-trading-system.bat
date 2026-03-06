@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ARG1=%~1"
set "ARG2=%~2"
set "ARG3=%~3"
set "ARG4=%~4"
set "ARG5=%~5"
set "ARG6=%~6"
set "ARG7=%~7"
set "ARG8=%~8"
set "ARG9=%~9"

set "MODE=%ARG1%"
if "%MODE%"=="" goto :usage

if /I "%MODE%"=="nogate" (
  set "TRADING_SYSTEM_SKIP_VALIDATION_GATE=1"
  set "MODE=!ARG2!"
  set "ARG2=!ARG3!"
  set "ARG3=!ARG4!"
  set "ARG4=!ARG5!"
  set "ARG5=!ARG6!"
  set "ARG6=!ARG7!"
  set "ARG7=!ARG8!"
  set "ARG8=!ARG9!"
  set "ARG9="
  if "!MODE!"=="" goto :usage
)

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"

set "CONFIG=configs\default.json"
set "LISTEN_HOST=127.0.0.1"
set "LISTEN_PORT=8000"
set "MULTI_CONFIG=configs\multi_accounts.sample.json"
set "MULTI_COMMAND=loop"
set "MULTI_INTERVAL=0"
set "MULTI_LIVE_TOKEN="
set "BACKUP_OUTPUT_DIR=backups"
set "INCLUDE_READINESS=0"
set "INCLUDE_LOGS=1"
set "RESTART_COOLDOWN=20"
set "SKIP_DEP_INSTALL=%TRADING_SYSTEM_SKIP_DEP_INSTALL%"
if not "!ARG9!"=="" set "SKIP_DEP_INSTALL=!ARG9!"

if /I "%MODE%"=="desktop" (
  if not "!ARG2!"=="" set "CONFIG=!ARG2!"
)
if /I "%MODE%"=="web" (
  if not "!ARG2!"=="" set "CONFIG=!ARG2!"
  if not "!ARG3!"=="" set "LISTEN_HOST=!ARG3!"
  if not "!ARG4!"=="" set "LISTEN_PORT=!ARG4!"
)
if /I "%MODE%"=="multi" (
  if not "!ARG2!"=="" set "MULTI_CONFIG=!ARG2!"
  if not "!ARG3!"=="" set "MULTI_COMMAND=!ARG3!"
  if not "!ARG4!"=="" set "MULTI_INTERVAL=!ARG4!"
  if not "!ARG5!"=="" set "MULTI_LIVE_TOKEN=!ARG5!"
)
if /I "%MODE%"=="multi-ui" (
  if not "!ARG2!"=="" set "MULTI_CONFIG=!ARG2!"
  if not "!ARG3!"=="" set "LISTEN_HOST=!ARG3!"
  if not "!ARG4!"=="" set "LISTEN_PORT=!ARG4!"
)
if /I "%MODE%"=="healthcheck" (
  if not "!ARG2!"=="" set "CONFIG=!ARG2!"
  if not "!ARG3!"=="" set "LISTEN_HOST=!ARG3!"
  if not "!ARG4!"=="" set "LISTEN_PORT=!ARG4!"
  if not "!ARG5!"=="" set "INCLUDE_READINESS=!ARG5!"
)
if /I "%MODE%"=="backup" (
  if not "!ARG2!"=="" set "BACKUP_OUTPUT_DIR=!ARG2!"
  if not "!ARG3!"=="" set "INCLUDE_LOGS=!ARG3!"
)
if /I "%MODE%"=="watchdog" (
  if not "!ARG2!"=="" set "CONFIG=!ARG2!"
  if not "!ARG3!"=="" set "LISTEN_HOST=!ARG3!"
  if not "!ARG4!"=="" set "LISTEN_PORT=!ARG4!"
  if not "!ARG5!"=="" set "MULTI_INTERVAL=!ARG5!"
  if not "!ARG6!"=="" set "RESTART_COOLDOWN=!ARG6!"
)

if /I not "%MODE%"=="desktop" if /I not "%MODE%"=="web" if /I not "%MODE%"=="multi" if /I not "%MODE%"=="multi-ui" if /I not "%MODE%"=="healthcheck" if /I not "%MODE%"=="backup" if /I not "%MODE%"=="watchdog" (
  echo [ERROR] Unknown mode: %MODE%
  goto :usage
)

if /I "%MODE%"=="desktop" (
  call :resolve_path "%CONFIG%" CONFIG_PATH
  if not exist "!CONFIG_PATH!" (
    echo [ERROR] Config not found: !CONFIG_PATH!
    exit /b 1
  )
)
if /I "%MODE%"=="web" (
  call :resolve_path "%CONFIG%" CONFIG_PATH
  if not exist "!CONFIG_PATH!" (
    echo [ERROR] Config not found: !CONFIG_PATH!
    exit /b 1
  )
)
if /I "%MODE%"=="multi" (
  call :resolve_path "%MULTI_CONFIG%" MULTI_CONFIG_PATH
  if not exist "!MULTI_CONFIG_PATH!" (
    echo [ERROR] Multi config not found: !MULTI_CONFIG_PATH!
    exit /b 1
  )
)
if /I "%MODE%"=="multi-ui" (
  call :resolve_path "%MULTI_CONFIG%" MULTI_CONFIG_PATH
  if not exist "!MULTI_CONFIG_PATH!" (
    echo [ERROR] Multi config not found: !MULTI_CONFIG_PATH!
    exit /b 1
  )
)
if /I "%MODE%"=="healthcheck" (
  call :resolve_path "%CONFIG%" CONFIG_PATH
  if not exist "!CONFIG_PATH!" (
    echo [ERROR] Config not found: !CONFIG_PATH!
    exit /b 1
  )
)
if /I "%MODE%"=="watchdog" (
  call :resolve_path "%CONFIG%" CONFIG_PATH
  if not exist "!CONFIG_PATH!" (
    echo [ERROR] Config not found: !CONFIG_PATH!
    exit /b 1
  )
  if "!MULTI_INTERVAL!"=="" set "MULTI_INTERVAL=15"
)

call :prepare_python
if errorlevel 1 exit /b !errorlevel!

set "PYTHONPATH=!ROOT!\src"

if /I "%MODE%"=="desktop" (
  echo Boss desktop dashboard start: config=!CONFIG_PATH!
  "!PY_EXE!" -m trading_system.main --ui-desktop --config "!CONFIG_PATH!"
  exit /b !errorlevel!
)
if /I "%MODE%"=="web" (
  echo Boss web dashboard start: config=!CONFIG_PATH! host=!LISTEN_HOST! port=!LISTEN_PORT!
  "!PY_EXE!" -m trading_system.main --ui --config "!CONFIG_PATH!" --host "!LISTEN_HOST!" --port !LISTEN_PORT!
  exit /b !errorlevel!
)
if /I "%MODE%"=="multi" (
  echo Boss multi runtime start: command=!MULTI_COMMAND! config=!MULTI_CONFIG_PATH! interval=!MULTI_INTERVAL!
  if not "!MULTI_INTERVAL!"=="0" (
    if not "!MULTI_LIVE_TOKEN!"=="" (
      "!PY_EXE!" -m trading_system.main --multi-config "!MULTI_CONFIG_PATH!" --multi-command "!MULTI_COMMAND!" --multi-interval !MULTI_INTERVAL! --multi-live-token "!MULTI_LIVE_TOKEN!"
    ) else (
      "!PY_EXE!" -m trading_system.main --multi-config "!MULTI_CONFIG_PATH!" --multi-command "!MULTI_COMMAND!" --multi-interval !MULTI_INTERVAL!
    )
  ) else (
    if not "!MULTI_LIVE_TOKEN!"=="" (
      "!PY_EXE!" -m trading_system.main --multi-config "!MULTI_CONFIG_PATH!" --multi-command "!MULTI_COMMAND!" --multi-live-token "!MULTI_LIVE_TOKEN!"
    ) else (
      "!PY_EXE!" -m trading_system.main --multi-config "!MULTI_CONFIG_PATH!" --multi-command "!MULTI_COMMAND!"
    )
  )
  exit /b !errorlevel!
)
if /I "%MODE%"=="multi-ui" (
  echo Boss multi dashboard start: config=!MULTI_CONFIG_PATH! host=!LISTEN_HOST! port=!LISTEN_PORT!
  "!PY_EXE!" -m trading_system.main --ui-multi --multi-config "!MULTI_CONFIG_PATH!" --host "!LISTEN_HOST!" --port !LISTEN_PORT!
  exit /b !errorlevel!
)
if /I "%MODE%"=="healthcheck" (
  set "READINESS_FLAG="
  if /I "!INCLUDE_READINESS!"=="1" set "READINESS_FLAG=--include-readiness"
  if /I "!INCLUDE_READINESS!"=="true" set "READINESS_FLAG=--include-readiness"
  if /I "!INCLUDE_READINESS!"=="yes" set "READINESS_FLAG=--include-readiness"
  echo Boss healthcheck: config=!CONFIG_PATH! host=!LISTEN_HOST! port=!LISTEN_PORT!
  if defined READINESS_FLAG (
    "!PY_EXE!" -m trading_system.ops_cli healthcheck --config "!CONFIG_PATH!" --listen-host "!LISTEN_HOST!" --listen-port !LISTEN_PORT! !READINESS_FLAG!
  ) else (
    "!PY_EXE!" -m trading_system.ops_cli healthcheck --config "!CONFIG_PATH!" --listen-host "!LISTEN_HOST!" --listen-port !LISTEN_PORT!
  )
  set "RC=!errorlevel!"
  exit /b !RC!
)
if /I "%MODE%"=="backup" (
  set "LOG_FLAG=--include-logs"
  if /I "!INCLUDE_LOGS!"=="0" set "LOG_FLAG=--no-include-logs"
  if /I "!INCLUDE_LOGS!"=="false" set "LOG_FLAG=--no-include-logs"
  if /I "!INCLUDE_LOGS!"=="no" set "LOG_FLAG=--no-include-logs"
  echo Boss backup: output=!BACKUP_OUTPUT_DIR! logs=!INCLUDE_LOGS!
  "!PY_EXE!" -m trading_system.ops_cli backup --output-dir "!BACKUP_OUTPUT_DIR!" !LOG_FLAG!
  exit /b !errorlevel!
)
if /I "%MODE%"=="watchdog" (
  echo Boss watchdog: config=!CONFIG_PATH! host=!LISTEN_HOST! port=!LISTEN_PORT! interval=!MULTI_INTERVAL! cooldown=!RESTART_COOLDOWN!
  "!PY_EXE!" -m trading_system.ops_cli watchdog --config "!CONFIG_PATH!" --listen-host "!LISTEN_HOST!" --listen-port !LISTEN_PORT! --check-interval-seconds !MULTI_INTERVAL! --restart-cooldown-seconds !RESTART_COOLDOWN!
  exit /b !errorlevel!
)

exit /b 0

:prepare_python
set "VENV_DIR=!ROOT!\.venv"
set "VENV_PY=!VENV_DIR!\Scripts\python.exe"
set "REQ_FILE=!ROOT!\requirements.txt"
set "PY_EXE="
set "SYS_PY_EXE="
set "SYS_PY_ARGS="

if defined TRADING_SYSTEM_PYTHON (
  if exist "!TRADING_SYSTEM_PYTHON!" (
    set "SYS_PY_EXE=!TRADING_SYSTEM_PYTHON!"
  ) else (
    echo [WARN] TRADING_SYSTEM_PYTHON ignored. Not found: !TRADING_SYSTEM_PYTHON!
  )
)

if exist "!VENV_PY!" (
  set "PY_EXE=!VENV_PY!"
  goto :deps
)

if not defined SYS_PY_EXE (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "SYS_PY_EXE=py"
    set "SYS_PY_ARGS=-3"
  )
)
if not defined SYS_PY_EXE (
  where python >nul 2>nul
  if not errorlevel 1 set "SYS_PY_EXE=python"
)
if not defined SYS_PY_EXE (
  echo [ERROR] Python launcher not found. Set TRADING_SYSTEM_PYTHON or install py/python.
  exit /b 1
)

echo [INFO] Creating virtual environment: !VENV_DIR!
"!SYS_PY_EXE!" !SYS_PY_ARGS! -m venv "!VENV_DIR!"
if errorlevel 1 (
  echo [ERROR] Failed to create venv.
  exit /b 1
)
if not exist "!VENV_PY!" (
  echo [ERROR] venv python not found: !VENV_PY!
  exit /b 1
)
set "PY_EXE=!VENV_PY!"

:deps
if /I "!SKIP_DEP_INSTALL!"=="1" exit /b 0

if not exist "!REQ_FILE!" (
  echo [ERROR] requirements.txt not found: !REQ_FILE!
  exit /b 1
)

"!PY_EXE!" -c "import importlib.util,sys;mods=['fastapi','uvicorn','pydantic','pandas','numpy','requests','ccxt'];missing=[m for m in mods if importlib.util.find_spec(m) is None];sys.exit(0 if not missing else 1)" >nul 2>nul
if errorlevel 1 (
  echo [INFO] Installing dependencies from requirements.txt ...
  "!PY_EXE!" -m pip install -r "!REQ_FILE!"
  if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    exit /b 1
  )
)
exit /b 0

:resolve_path
set "_raw=%~1"
if "%_raw%"=="" (
  set "%~2="
  exit /b 0
)
for %%I in ("%_raw%") do set "%~2=%%~fI"
exit /b 0

:usage
echo Usage: run-trading-system.bat ^<desktop^|web^|multi^|multi-ui^|healthcheck^|backup^|watchdog^> [args...]
echo        run-trading-system.bat nogate ^<desktop^|web^|multi^|multi-ui^> [args...]
echo   desktop [config]
echo   web [config] [host] [port]
echo   multi [multi_config] [command] [interval] [live_token]
echo   multi-ui [multi_config] [host] [port]
echo   healthcheck [config] [host] [port] [include_readiness]
echo   backup [output_dir] [include_logs]
echo   watchdog [config] [host] [port] [interval] [restart_cooldown]
exit /b 1

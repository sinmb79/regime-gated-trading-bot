@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "MODE=%~1"
set "CONFIG=%~2"
set "HOST=%~3"
set "PORT=%~4"
set "INTERVAL=%~5"
set "DEFAULT_CONFIG=%~dp0configs\default.json"

if /I "%MODE%"=="nogate" (
  set "TRADING_SYSTEM_SKIP_VALIDATION_GATE=1"
  set "MODE=%~2"
  set "CONFIG=%~3"
  set "HOST=%~4"
  set "PORT=%~5"
  set "INTERVAL=%~6"
)

if /I "%MODE%"=="web" (
  if "!CONFIG!"=="" set "CONFIG=%DEFAULT_CONFIG%"
  if "!HOST!"=="" set "HOST=127.0.0.1"
  if "!PORT!"=="" set "PORT=8000"
  call "%~dp0scripts\start-dashboard.bat" "!CONFIG!" "!HOST!" "!PORT!"
  exit /b !errorlevel!
)

if /I "%MODE%"=="desktop" (
  if "!CONFIG!"=="" set "CONFIG=%DEFAULT_CONFIG%"
  call "%~dp0scripts\start-desktop-dashboard.bat" "!CONFIG!"
  exit /b !errorlevel!
)

if /I "%MODE%"=="multi" (
  if "!CONFIG!"=="" set "CONFIG=%~dp0configs\multi_accounts.sample.json"
  if "!HOST!"=="" set "HOST=loop"
  if "!PORT!"=="" set "PORT=0"
  call "%~dp0scripts\start-multi-system.bat" "!CONFIG!" "!HOST!" "!PORT!" "!INTERVAL!"
  exit /b !errorlevel!
)

if /I "%MODE%"=="multi-ui" (
  if "!CONFIG!"=="" set "CONFIG=%~dp0configs\multi_accounts.sample.json"
  if "!HOST!"=="" set "HOST=127.0.0.1"
  if "!PORT!"=="" set "PORT=8100"
  call "%~dp0scripts\start-multi-dashboard.bat" "!CONFIG!" "!HOST!" "!PORT!"
  exit /b !errorlevel!
)

if /I "%MODE%"=="healthcheck" (
  if "!CONFIG!"=="" set "CONFIG=%DEFAULT_CONFIG%"
  if "!HOST!"=="" set "HOST=127.0.0.1"
  if "!PORT!"=="" set "PORT=8000"
  call "%~dp0scripts\run-trading-system.bat" healthcheck "!CONFIG!" "!HOST!" "!PORT!"
  exit /b !errorlevel!
)

if /I "%MODE%"=="rehearsal" (
  if "!CONFIG!"=="" set "CONFIG=%DEFAULT_CONFIG%"
  if "!HOST!"=="" (
    call "%~dp0scripts\run-trading-system.bat" rehearsal "!CONFIG!"
  ) else (
    call "%~dp0scripts\run-trading-system.bat" rehearsal "!CONFIG!" "!HOST!"
  )
  exit /b !errorlevel!
)

if /I "%MODE%"=="backup" (
  if "!CONFIG!"=="" set "CONFIG=backups"
  call "%~dp0scripts\run-trading-system.bat" backup "!CONFIG!"
  exit /b !errorlevel!
)

if /I "%MODE%"=="watchdog" (
  if "!CONFIG!"=="" set "CONFIG=%DEFAULT_CONFIG%"
  if "!HOST!"=="" set "HOST=127.0.0.1"
  if "!PORT!"=="" set "PORT=8000"
  if "!INTERVAL!"=="" set "INTERVAL=15"
  call "%~dp0scripts\run-trading-system.bat" watchdog "!CONFIG!" "!HOST!" "!PORT!" "!INTERVAL!"
  exit /b !errorlevel!
)

if "%MODE%"=="" (
  echo No mode specified. Starting desktop dashboard.
  call "%~dp0scripts\start-desktop-dashboard.bat" "%DEFAULT_CONFIG%"
  exit /b !errorlevel!
)

if /I "%MODE%"=="/h" (
  echo Usage:
  echo   start-system.bat [desktop^|web^|multi^|multi-ui^|healthcheck^|backup^|rehearsal^|watchdog] [config] [host] [port] [interval]
  echo   start-system.bat nogate [desktop^|web^|multi^|multi-ui] ...
  echo   start-system.bat                 => desktop dashboard
  echo   start-system.bat web             => web dashboard
  echo   start-system.bat web [config] [host] [port]
  echo   start-system.bat desktop [config]
  echo   start-system.bat multi [multi_config] [command] [interval] [live_token]
  echo   start-system.bat multi-ui [multi_config] [host] [port]
  echo   start-system.bat healthcheck [config] [host] [port]
  echo   start-system.bat backup [output_dir]
  echo   start-system.bat rehearsal [config] [output_path^|auto]
  echo   start-system.bat watchdog [config] [host] [port] [interval]
  echo   start-system.bat nogate web [config] [host] [port]   ^(validation gate bypass)
  exit /b 0
)

rem If first arg is a config path, treat as default desktop launch
if exist "%MODE%" (
  echo First argument treated as config path.
  call "%~dp0scripts\start-desktop-dashboard.bat" "%MODE%"
  exit /b !errorlevel!
)

echo Unknown mode: %MODE%
echo Use desktop, web, multi, multi-ui, healthcheck, backup, rehearsal, watchdog. If passing only a config path, use:
	echo start-system.bat "configs/default.json"
exit /b 1

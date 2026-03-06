@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PRESET=%~1"
set "TARGET=%~2"
set "HOST=%~3"
set "PORT=%~4"

if "%PRESET%"=="" goto :usage
if "%TARGET%"=="" set "TARGET=desktop"

set "CONFIG=%~dp0configs\presets\nogate_%PRESET%.json"
if exist "%CONFIG%" goto :config_ok
echo [ERROR] preset config not found: %CONFIG%
exit /b 1
:config_ok

if /I "%TARGET%"=="desktop" (
  call "%~dp0start-system.bat" nogate desktop "!CONFIG!"
  exit /b !errorlevel!
)

if /I "%TARGET%"=="web" (
  if "%HOST%"=="" set "HOST=127.0.0.1"
  if "%PORT%"=="" set "PORT=8000"
  call "%~dp0start-system.bat" nogate web "!CONFIG!" "!HOST!" "!PORT!"
  exit /b !errorlevel!
)

echo [ERROR] unknown target: %TARGET%
goto :usage

:usage
echo Usage:
echo   start-nogate-preset.bat ^<safe^|balanced^|aggressive^> [desktop^|web] [host] [port]
echo Examples:
echo   start-nogate-preset.bat safe
echo   start-nogate-preset.bat balanced web 127.0.0.1 8000
exit /b 1

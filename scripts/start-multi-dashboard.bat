@echo off
setlocal
set "MULTI_CONFIG=%~dp0..\configs\multi_accounts.sample.json"
if not "%~1"=="" set "MULTI_CONFIG=%~1"
set "HOST=127.0.0.1"
if not "%~2"=="" set "HOST=%~2"
set "PORT=8100"
if not "%~3"=="" set "PORT=%~3"
echo Boss multi dashboard start: config=%MULTI_CONFIG% host=%HOST% port=%PORT%
call "%~dp0run-trading-system.bat" multi-ui "%MULTI_CONFIG%" "%HOST%" "%PORT%"
exit /b %errorlevel%

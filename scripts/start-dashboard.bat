@echo off
setlocal
set "CONFIG=%~dp0..\configs\default.json"
if not "%~1"=="" set "CONFIG=%~1"
if "%~2"=="" set "HOST=127.0.0.1"
if not "%~2"=="" set "HOST=%~2"
if "%~3"=="" set "PORT=8000"
if not "%~3"=="" set "PORT=%~3"
echo Boss dashboard start: type=web config=%CONFIG% host=%HOST% port=%PORT%
call "%~dp0run-trading-system.bat" web "%CONFIG%" "%HOST%" "%PORT%"
exit /b %errorlevel%

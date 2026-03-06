@echo off
setlocal
set "CONFIG=%~dp0..\configs\default.json"
if not "%~1"=="" set "CONFIG=%~1"
echo Boss dashboard start: type=desktop config=%CONFIG%
call "%~dp0run-trading-system.bat" desktop "%CONFIG%"
exit /b %errorlevel%

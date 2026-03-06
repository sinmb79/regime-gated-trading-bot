@echo off
setlocal
set "MULTI_CONFIG=%~dp0configs\multi_accounts.sample.json"
if not "%~1"=="" set "MULTI_CONFIG=%~1"
set "MULTI_COMMAND=loop"
if not "%~2"=="" set "MULTI_COMMAND=%~2"
set "MULTI_INTERVAL=0"
if not "%~3"=="" set "MULTI_INTERVAL=%~3"
set "MULTI_LIVE_TOKEN="
if not "%~4"=="" set "MULTI_LIVE_TOKEN=%~4"
call "%~dp0scripts\start-multi-system.bat" "%MULTI_CONFIG%" "%MULTI_COMMAND%" "%MULTI_INTERVAL%" "%MULTI_LIVE_TOKEN%"

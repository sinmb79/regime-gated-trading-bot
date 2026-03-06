@echo off
setlocal
set "ROOT=%~dp0"
echo 보스 AI 트레이딩 시스템 로컬 설치를 시작합니다.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\install-trading-system.ps1" -InstallDir "%LOCALAPPDATA%\BossTradingSystem" -CreateDesktopShortcuts -OverwriteExisting
if errorlevel 1 (
  echo 설치 실패. 메시지를 확인해 주세요.
  pause
  exit /b 1
)
echo 설치 완료.
echo 설치 경로: %LOCALAPPDATA%\BossTradingSystem
pause
exit /b 0

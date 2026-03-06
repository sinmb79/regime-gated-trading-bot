[CmdletBinding()]
param(
    [string]$TaskName = "BossTradingWatchdog"
)

$ErrorActionPreference = "Stop"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "watchdog 작업 삭제 완료: $TaskName"
} else {
    Write-Host "watchdog 작업이 존재하지 않습니다: $TaskName"
}

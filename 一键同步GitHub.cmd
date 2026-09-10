@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync-github.ps1"
set "syncExitCode=%errorlevel%"
if "%syncExitCode%"=="0" (
    echo Sync successful.
) else (
    echo Sync failed. Please read the error above.
)
if /I not "%~1"=="--no-pause" pause
exit /b %syncExitCode%

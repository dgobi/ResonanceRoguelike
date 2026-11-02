@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1"
set "result=%errorlevel%"
echo.
pause
exit /b %result%

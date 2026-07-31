@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0project-hope.ps1" %*
exit /b %errorlevel%

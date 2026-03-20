@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0add.ps1" %*
exit /b %ERRORLEVEL%

@echo off
setlocal

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%install_windows.ps1

if not exist "%PS_SCRIPT%" (
  echo ERROR: install_windows.ps1 not found.
  exit /b 2
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
exit /b %ERRORLEVEL%

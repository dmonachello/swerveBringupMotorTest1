@echo off
setlocal

echo This compatibility launcher uses the repository Windows installer.
call "%~dp0..\..\install_windows.cmd" %*
exit /b %ERRORLEVEL%

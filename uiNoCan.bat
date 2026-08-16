@echo off
setlocal

cd /d "%~dp0"
call tools\can_nt\run_can_nt.cmd --ui --no-can %*

endlocal

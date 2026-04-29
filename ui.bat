@echo off
setlocal

cd /d "%~dp0"
python -m tools.can_nt.can_nt_bridge --ui --rio 172.22.11.2 %*

endlocal

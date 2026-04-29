@echo off
setlocal

cd /d "%~dp0"
python -m tools.can_topology.can_top_editor

endlocal

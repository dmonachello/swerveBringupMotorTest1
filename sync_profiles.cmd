@echo off
setlocal
set "REPO_ROOT=%~dp0"
set "PYTHONPATH=%REPO_ROOT%"
python "%REPO_ROOT%tools\sync_profiles.py" %*

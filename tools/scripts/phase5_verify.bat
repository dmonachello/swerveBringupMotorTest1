@echo off
setlocal

set REPO_ROOT=%USERPROFILE%\swerveBringupMotorTest1-main
set PYTHON_EXE=python
set BRIDGE_PATH=%REPO_ROOT%\tools\can_nt\can_nt_bridge.py
set SCRIPT_PATH=%REPO_ROOT%\tools\scripts\phase5_verify.cli
set RIO_HOST=172.22.11.2
set OUT_PATH=%REPO_ROOT%\b.b
set ARG_BATCH=--batch
set ARG_SCRIPT=--script
set ARG_CLI=--cli
set ARG_RIO=--rio

set CLI_ARGS=%ARG_BATCH% %ARG_SCRIPT% "%SCRIPT_PATH%" %ARG_CLI% %ARG_RIO% %RIO_HOST%

pushd "%REPO_ROOT%"
%PYTHON_EXE% "%BRIDGE_PATH%" %CLI_ARGS% > "%OUT_PATH%" 2>&1
popd

endlocal


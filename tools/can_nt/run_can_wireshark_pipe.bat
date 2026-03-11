@echo off
setlocal
REM Run from repo root so module imports work
set "START_DIR=%CD%"
pushd "%~dp0\..\.."

set "PIPE_NAME=FRC_CAN"
if not "%~1"=="" (
  set "PIPE_NAME=%~1"
  shift
)

set "EXTRA_ARGS=%*"

if not "%WIRESHARK_EXE%"=="" (
  set "WS_CMD=%WIRESHARK_EXE%"
) else (
  set "WS_CMD=wireshark"
)

echo Starting Wireshark live capture on \\.\pipe\%PIPE_NAME% ...
start "Wireshark" "%WS_CMD%" -k -i \\.\pipe\%PIPE_NAME%

echo.
echo Starting CAN diagnostics (live pipe)...
python -m tools.can_nt.can_nt_bridge ^
  --pcap-pipe %PIPE_NAME% ^
  %EXTRA_ARGS%

echo.
echo Stopped.
popd
endlocal & cd /d "%START_DIR%"
pause

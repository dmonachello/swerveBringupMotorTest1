@echo off
setlocal
REM Run from this script's directory so imports work
set "START_DIR=%CD%"
pushd "%~dp0"

if not exist logs (
    mkdir logs
)

REM Timestamp for log files (YYYYMMDD_HHMMSS)
set TS=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TS=%TS: =0%

echo Starting CAN diagnostics (robot profile)...
echo.

set CHANNEL=
if not "%~1"=="" (
  set CHANNEL=--channel %~1
)

python can_nt_bridge.py ^
  --profile robot ^
  --interface slcan ^
  %CHANNEL% ^
  --bitrate 1000000 ^
  --rio 172.22.11.2 ^
  --publish-can-summary ^
  --pcap logs\robot_%TS%.asc

echo.
echo Stopped.
popd
endlocal & cd /d "%START_DIR%"
pause

@echo off
cd /d "%~dp0\..\.."

if not exist tools\can_nt\logs (
    mkdir tools\can_nt\logs
)

set TS=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TS=%TS: =0%

echo Starting CAN diagnostics (demo_club profile)...
echo.

python -m tools.can_nt.can_nt_bridge ^
  --profile demo_club ^
  --interface slcan ^
  %* ^
  --bitrate 1000000 ^
  --rio 172.22.11.2 ^
  --publish-can-summary ^
  --pcap tools\can_nt\logs\demo_%TS%.asc

echo.
pause

@echo off
REM Update build metadata from git (Python + Java constants).
REM Usage:
REM   gitver
REM   gitver --dry-run

python tools\update_build_info.py %*

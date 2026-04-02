@echo off
REM One-word helper for version bumps/sets.
REM Usage:
REM   bump bridge_cli minor
REM   bump set bridge_cli minor 4

python tools\bump_version.py %*

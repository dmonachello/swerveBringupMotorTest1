@echo off
REM Repo resync: pull latest and show last commit summary.
git pull
if errorlevel 1 exit /b 1
git log -1 --stat
git log -1 --pretty="SUMMARY: %s"

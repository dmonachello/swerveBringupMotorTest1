@echo off
setlocal
REM Run from this script's directory so imports work
set "START_DIR=%CD%"
pushd "%~dp0"

if not "%~1"=="" (
  set "PY=%~1"
) else if not "%BRINGUP_TEST_PYTHON%"=="" (
  set "PY=%BRINGUP_TEST_PYTHON%"
) else (
  set "PY=python"
)

echo Starting bringup test template wizard...
%PY% copy_test_template.py %*

popd
endlocal & cd /d "%START_DIR%"
pause

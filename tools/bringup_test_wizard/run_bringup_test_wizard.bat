@echo off
setlocal
REM Run from repo root so module imports work
set "START_DIR=%CD%"
pushd "%~dp0\..\.."

if not "%~1"=="" (
  set "PY=%~1"
) else if not "%BRINGUP_TEST_PYTHON%"=="" (
  set "PY=%BRINGUP_TEST_PYTHON%"
) else (
  set "PY=python"
)

echo Starting bringup test wizard...
%PY% -m tools.bringup_test_wizard.gen_bringup_tests %*

popd
endlocal & cd /d "%START_DIR%"
pause

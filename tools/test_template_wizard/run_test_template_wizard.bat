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

echo Starting bringup test template wizard...
%PY% -m tools.test_template_wizard.copy_test_template %*

popd
endlocal & cd /d "%START_DIR%"
pause

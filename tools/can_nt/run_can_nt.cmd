@echo off
setlocal
set PYTHON_EXE=
set EXTRA_ARGS=

if not "%CAN_NT_PYTHON%"=="" set PYTHON_EXE=%CAN_NT_PYTHON%
if not "%~1"=="" (
  if "%~x1"==".exe" (
    set PYTHON_EXE=%~1
    shift
  )
)

if "%PYTHON_EXE%"=="" (
  for /f "delims=" %%p in ('where python 2^>nul') do (
    if "%PYTHON_EXE%"=="" set PYTHON_EXE=%%p
  )
)

if "%PYTHON_EXE%"=="" set PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe

set EXTRA_ARGS=%*

echo Using Python: %PYTHON_EXE%
pushd "%~dp0\..\.."
"%PYTHON_EXE%" -m tools.can_nt.can_nt_bridge --rio 172.22.11.2 %EXTRA_ARGS%
popd
endlocal

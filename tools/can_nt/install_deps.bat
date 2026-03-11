REM @echo off
REM Installs dependencies needed by this tool.
REM Run in an Administrator shell only if your Python install requires it.

cd /d "%~dp0"

echo Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found on PATH.
    echo Install Python 3 and make sure "python" works from cmd.
    pause
    exit /b 1
)

echo Checking for pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip not available.
    echo Try: python -m ensurepip --upgrade
    pause
    exit /b 1
)

echo Upgrading pip (safe)...
python -m pip install --upgrade pip

echo Installing python-can and pyserial...
python -m pip install --upgrade python-can pyserial

echo Installing NetworkTables client (preferred): pyntcore
python -m pip install --upgrade pyntcore

echo Installing fallback NetworkTables client: pynetworktables
python -m pip install --upgrade pynetworktables

echo.
echo Done.
echo If you see Windows DLL errors for pyntcore, install the VS 2022 redistributable.
pause

@echo off
set PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe

if not "%CAN_NT_PYTHON%"=="" set PYTHON_EXE=%CAN_NT_PYTHON%
if not "%~1"=="" set PYTHON_EXE=%~1

"%PYTHON_EXE%" tools\can_nt_bridge.py --rio 172.22.11.2

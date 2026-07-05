@echo off
title Tomato VBook Server - Local LAN Mode
cd /d "%~dp0"

echo ===================================================================
echo             TOMATO VBOOK PYTHON SERVER - LOCAL LAN RUNNER
echo ===================================================================
echo.

:: Detect Python executable
set "PYTHON_EXE=python"
where python >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe" (
        set "PYTHON_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python310\python.exe"
    ) else if exist "C:\Program Files\LibreOffice\program\python.exe" (
        set "PYTHON_EXE=C:\Program Files\LibreOffice\program\python.exe"
    ) else (
        echo [-] LOI: Khong tim thay Python tren may tinh!
        echo [+] Vui long chay file setup_new_computer.bat de tu dong cai dat Python.
        echo.
        pause
        exit /b
    )
)

echo [+] Dang khoi dong HTTP Server (Python) bang %PYTHON_EXE%...
echo.
"%PYTHON_EXE%" vbook_server.py
pause

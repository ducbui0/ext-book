@echo off
title Tomato VBook Server - Tailscale Mode
cd /d "%~dp0"

echo ===================================================================
echo             TOMATO VBOOK PYTHON SERVER - TAILSCALE RUNNER
echo ===================================================================
echo.

:: 1. Detect Python executable
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

:: 2. Detect Tailscale executable
set "TAILSCALE_EXE="
where tailscale >nul 2>&1
if %errorlevel% equ 0 (
    set "TAILSCALE_EXE=tailscale"
) else (
    if exist "C:\Program Files\Tailscale\tailscale.exe" (
        set "TAILSCALE_EXE=C:\Program Files\Tailscale\tailscale.exe"
    )
)

:: 3. Get Tailscale IP
set "TS_IP="
if defined TAILSCALE_EXE (
    for /f "tokens=*" %%i in ('"%TAILSCALE_EXE%" ip -4 2^>nul') do set "TS_IP=%%i"
)

:: 4. Print instructions
if not defined TS_IP (
    echo [-] CANH BAO: Khong tim thay IP Tailscale hoac Tailscale chua duoc bat/dang nhap.
    echo [+] Huong dan bat dau:
    echo   1. Tai va cai dat Tailscale tu: https://tailscale.com/download
    echo   2. Dang nhap cung mot tai khoan tren ca PC nay va dien thoai.
    echo   3. Mo Tailscale len va ket noi.
    echo   4. Chay lai file nay de lay IP tu dong.
    echo.
    echo [*] Server van se khoi dong tai cong 18423...
) else (
    echo [+] Da phat hien IP Tailscale: %TS_IP%
    echo.
    echo ===================================================================
    echo [HUONG DAN KET NOI VBOOK]
    echo 1. IP Tailscale co dinh cua may tinh nay la: %TS_IP%
    echo 2. Sao chep dong ma sau va dan vao muc "Ma bo sung" tren VBook:
    echo.
    echo    var CONFIG_URL = "http://%TS_IP%:18423";
    echo.
    echo [!] LUU Y: Hay dam bao dien thoai va PC dang cung bat Tailscale!
    echo ===================================================================
)
echo.

echo [+] Dang khoi dong HTTP Server (Python) bang %PYTHON_EXE%...
"%PYTHON_EXE%" vbook_server.py
pause

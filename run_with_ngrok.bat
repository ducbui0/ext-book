@echo off
title Tomato VBook Server with Ngrok Tunnel
cd /d "%~dp0"
set PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python310;%PATH%
echo ===================================================================
echo             TOMATO VBOOK PYTHON SERVER WITH NGROK
echo ===================================================================
echo.

:: Check if ngrok is authenticated
if exist "%USERPROFILE%\AppData\Local\ngrok\ngrok.yml" goto start_server
if exist "%APPDATA%\ngrok\ngrok.yml" goto start_server

echo [-] Ban chua cau hinh Token cho ngrok.
echo [+] Vui long truy cap trang web: https://dashboard.ngrok.com/get-started/your-authtoken
echo [+] Sao chep dong "Your Authtoken" va dan vao duoi day:
echo.
set /p token="Token cua ban: "
if "%token%"=="" (
    echo [-] Token khong hop le. Khong the tiep tuc.
    pause
    exit /b
)
ngrok.exe config add-authtoken %token%

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

:start_server

echo.
echo [+] Dang khoi dong HTTP Server trung gian (Python) bang %PYTHON_EXE%...
start "" /B "%PYTHON_EXE%" vbook_server.py

echo [+] Dang khoi dong duong ham Ngrok Tunnel voi ten mien co dinh...
echo.
echo ===================================================================
echo [HUONG DAN DU KET NOI]
echo 1. Ten mien co dinh cua ban la: https://opt-cartel-ominous.ngrok-free.dev
echo 2. Sao chep va dan dong ma sau vao muc "Ma bo sung" tren VBook:
echo.
echo    var CONFIG_URL = "https://opt-cartel-ominous.ngrok-free.dev";
echo.
echo [!] LUU Y: Ke tu gio, ban se khong can phai sua lai link tren VBook nua!
echo ===================================================================
echo.

ngrok.exe http 18423 --url opt-cartel-ominous.ngrok-free.dev
pause

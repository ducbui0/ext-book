@echo off
title Tomato VBook Server - Setup Helper
cd /d "%~dp0"

echo ===================================================================
echo             TOMATO VBOOK SERVER - SETUP FOR NEW COMPUTER
echo ===================================================================
echo.

:: 1. Check & Install Python
echo [+] [BUOC 1/3] Dang kiem tra moi truong Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [-] Khong tim thay Python. Dang tien hanh tai va cai dat tu dong...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Write-Host '   -> Dang tai Python...' -ForegroundColor Yellow; ^
         Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe' -OutFile 'python_installer.exe'; ^
         Write-Host '   -> Dang cai dat Python am tham (vui long cho)...' -ForegroundColor Yellow; ^
         Start-Process -FilePath '.\python_installer.exe' -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1' -Wait; ^
         Remove-Item -Path 'python_installer.exe' -Force; ^
         Write-Host '   -> Cai dat Python hoan tat!' -ForegroundColor Green"

    :: Refresh path variable locally so current script can call python
    set PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python310;%PATH%
) else (
    echo [+] Python da duoc cai dat san tren may.
)
echo.

:: 2. Choose tunnel method
echo ===================================================================
echo [BUOC 2/3] Chon phuong thuc ket noi tu xa:
echo.
echo   1. Tailscale  ^(Khuyen dung - Bao mat, co dinh, mien phi^)
echo   2. Ngrok      ^(Ket noi qua ten mien cong khai^)
echo   3. Khong can  ^(Chi dung trong mang LAN noi bo^)
echo.
set /p choice="Nhap lua chon (1/2/3): "

if "%choice%"=="1" goto setup_tailscale
if "%choice%"=="2" goto setup_ngrok
goto finished_no_tunnel

:: ===================================================================
:setup_tailscale
echo.
echo [+] [BUOC 3/3] Huong dan cai dat Tailscale...
echo.
echo     Tailscale tao mot mang LAN ao bia mat (WireGuard VPN) giua
echo     PC va dien thoai cua ban, khong lo bi hack hay doi dia chi.
echo.
echo     Cac buoc:
echo       1. Tai va cai Tailscale: https://tailscale.com/download/windows
echo       2. Dang nhap bang Google / Microsoft (dung chung 1 tai khoan
echo          tren ca PC nay lan dien thoai Android/iOS cua ban).
echo       3. Bat Tailscale len tren ca 2 thiet bi.
echo       4. Chay run_with_tailscale.bat de lay IP ket noi chinh xac
echo          va khoi dong server.
echo.
echo [+] Dang mo trang tai Tailscale...
start "" "https://tailscale.com/download/windows"
goto finished

:: ===================================================================
:setup_ngrok
echo.
echo [+] [BUOC 3/3] Dang cai dat Ngrok...
if not exist "ngrok.exe" (
    echo [-] Khong tim thay ngrok.exe. Dang tai ve tu dong...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Write-Host '   -> Dang tai ngrok...' -ForegroundColor Yellow; ^
         Invoke-WebRequest -Uri 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile 'ngrok.zip'; ^
         Write-Host '   -> Dang giai nen...' -ForegroundColor Yellow; ^
         Expand-Archive -Path 'ngrok.zip' -DestinationPath '.' -Force; ^
         Remove-Item -Path 'ngrok.zip' -Force; ^
         Write-Host '   -> Tai va giai nen ngrok thanh cong!' -ForegroundColor Green"
) else (
    echo [+] Da co san file ngrok.exe.
)
echo.
echo [+] Dang kiem tra Token ngrok...
if exist "%USERPROFILE%\AppData\Local\ngrok\ngrok.yml" goto ngrok_done
if exist "%APPDATA%\ngrok\ngrok.yml" goto ngrok_done

echo [-] Chua cau hinh Token cho ngrok tren may tinh nay.
echo [+] Vui long truy cap: https://dashboard.ngrok.com/get-started/your-authtoken
echo [+] Sao chep Authtoken va dan vao duoi day:
echo.
set /p token="Token cua ban: "
if not "%token%"=="" (
    ngrok.exe config add-authtoken %token%
    echo [+] Token da duoc luu thanh cong!
) else (
    echo [-] Token khong hop le. Vui long chay lai script nay de cau hinh.
)

:ngrok_done
echo [+] Ngrok da san sang. Chay run_with_ngrok.bat de bat dau.
goto finished

:: ===================================================================
:finished_no_tunnel
echo.
echo [+] Khong cai them gi. Chay run_local.bat de ket noi qua mang LAN.

:finished
echo.
echo ===================================================================
echo [+] HOAN TAT CAI DAT HE THONG!
echo.
echo   Chay file tuong ung voi lua chon ket noi cua ban:
echo.
echo   run_with_tailscale.bat  -^>  Dung Tailscale ^(khuyen dung^)
echo   run_with_ngrok.bat      -^>  Dung Ngrok
echo   run_local.bat           -^>  Dung trong mang LAN
echo.
echo ===================================================================
echo.
pause

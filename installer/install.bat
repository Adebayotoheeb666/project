@echo off
setlocal enabledelayedexpansion
title LSIA School Computer Installer
echo ========================================================
echo   Local-First School Intelligence System (LSIA)
echo   Windows School Computer Installer
echo ========================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Requesting administrative privileges...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

set ROOT_DIR=%~dp0..
cd /d "%ROOT_DIR%"

echo [1/5] Checking Python installation...
where python.exe >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 3.11+ is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [2/5] Setting up virtual environment...
if not exist "server\.venv\Scripts\python.exe" (
    echo Creating virtual environment in server\.venv...
    python -m venv server\.venv
)

echo Installing dependencies...
server\.venv\Scripts\python.exe -m pip install --upgrade pip
server\.venv\Scripts\pip.exe install -e "server[dev]"

echo [3/5] Verifying admin dashboard web assets...
if not exist "admin\dist\index.html" (
    echo Building administration frontend assets...
    where npm.cmd >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        cd admin
        call npm.cmd install
        call npm.cmd run build
        cd "%ROOT_DIR%"
    )
)

echo [4/5] Configuring Windows Defender Firewall for LAN access...
netsh advfirewall firewall show rule name="LSIA School Server" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Firewall rule already exists.
) else (
    echo Adding inbound firewall rule for TCP port 8080 (School LAN)...
    netsh advfirewall firewall add rule name="LSIA School Server" dir=in action=allow protocol=TCP localport=8080 profile=private,domain
)

echo [5/5] Creating Desktop Shortcut and Startup Task...
set SHORTCUT_PATH=%USERPROFILE%\Desktop\LSIA School Computer.url
echo [InternetShortcut] > "%SHORTCUT_PATH%"
echo URL=http://127.0.0.1:8080 >> "%SHORTCUT_PATH%"
echo IconFile=%ROOT_DIR%\admin\public\vite.svg >> "%SHORTCUT_PATH%"
echo IconIndex=0 >> "%SHORTCUT_PATH%"

:: Create Scheduled Task for Auto-Startup on Boot
schtasks /query /tn "LSIA_School_Computer" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Configuring automatic background startup task...
    schtasks /create /tn "LSIA_School_Computer" /tr "\"%ROOT_DIR%\scripts\start-school-computer.bat\"" /sc onlogon /rl highest /f >nul 2>&1
)

echo.
echo ========================================================
echo   [SUCCESS] LSIA School Computer Installation Complete!
echo ========================================================
echo.
echo - School Computer Desk:  http://127.0.0.1:8080
echo - Desktop Shortcut:      %SHORTCUT_PATH%
echo - Startup:               Configured to run automatically on logon.
echo - LAN Sync:              Teachers on the school Wi-Fi can sync on port 8080.
echo.
set /p START_NOW="Do you want to start the LSIA server now? (Y/N): "
if /i "%START_NOW%"=="Y" (
    start "" "%ROOT_DIR%\scripts\start-school-computer.bat"
)

pause

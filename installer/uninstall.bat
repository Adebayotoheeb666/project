@echo off
title LSIA Uninstaller
echo ========================================================
echo   Local-First School Intelligence System (LSIA)
echo   Uninstaller
echo ========================================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Requesting administrative privileges...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

echo Removing automatic startup task...
schtasks /delete /tn "LSIA_School_Computer" /f >nul 2>&1

echo Removing firewall rule...
netsh advfirewall firewall delete rule name="LSIA School Server" >nul 2>&1

echo Removing desktop shortcut...
if exist "%USERPROFILE%\Desktop\LSIA School Computer.url" (
    del "%USERPROFILE%\Desktop\LSIA School Computer.url"
)

echo.
echo [NOTE] Your database and keys in server\data\ have been preserved.
echo If you wish to delete all school records, delete the server\data directory manually.
echo.
echo Uninstallation completed.
pause

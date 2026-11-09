@echo off
title LSIA School Computer
echo ========================================================
echo   Local-First School Intelligence System (LSIA)
echo   School Computer Administration Server
echo ========================================================
echo.

:: Detect if running from install directory or developer scripts directory
if exist "%~dp0server\lsia" (
    cd /d "%~dp0server"
) else if exist "%~dp0..\server\lsia" (
    cd /d "%~dp0..\server"
) else (
    cd /d "%~dp0"
)

:: Check for Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in PATH.
    echo Please install Python 3.10+ from https://www.python.org/ or the Microsoft Store.
    pause
    exit /b 1
)

:: Check or create virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] First-time setup: Initializing local Python virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Installing LSIA server dependencies...
    .venv\Scripts\pip install -e .
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Starting LSIA server on http://0.0.0.0:8080 ...
echo The administration dashboard is accessible at http://127.0.0.1:8080
echo Teachers on the school LAN can sync at http://^<YOUR-LAN-IP^>:8080
echo.
.venv\Scripts\uvicorn lsia.main:create_app --factory --host 0.0.0.0 --port 8080
pause

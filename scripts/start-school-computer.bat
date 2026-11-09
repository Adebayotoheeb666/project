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
    set "IS_INSTALLED=1"
) else if exist "%~dp0..\server\lsia" (
    cd /d "%~dp0..\server"
    set "IS_INSTALLED=0"
) else (
    cd /d "%~dp0"
    set "IS_INSTALLED=0"
)

:: Check for Python in PATH or common Windows install paths
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "SYS_PYTHON=python"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "SYS_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "C:\Python312\python.exe" (
    set "SYS_PYTHON=C:\Python312\python.exe"
) else if exist "C:\Python311\python.exe" (
    set "SYS_PYTHON=C:\Python311\python.exe"
) else (
    echo [ERROR] Python was not found in PATH.
    echo Please install Python 3.10+ from https://www.python.org/ or the Microsoft Store.
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)

:: Decide virtual environment and data location
:: When installed in Program Files, Program Files is read-only for normal users.
:: We store the user's venv and database in %LOCALAPPDATA%\LSIA.
if "%IS_INSTALLED%"=="1" (
    set "VENV_DIR=%LOCALAPPDATA%\LSIA\venv"
    set "LSIA_DATA_DIR=%LOCALAPPDATA%\LSIA\data"
    if not exist "%LOCALAPPDATA%\LSIA" mkdir "%LOCALAPPDATA%\LSIA" >nul 2>&1
) else if exist ".venv\Scripts\python.exe" (
    set "VENV_DIR=%CD%\.venv"
) else (
    set "VENV_DIR=%CD%\.venv"
)

:: Check or create virtual environment
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] First-time setup: Initializing Python environment...
    echo Location: %VENV_DIR%
    "%SYS_PYTHON%" -m venv "%VENV_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo Please ensure you have write permissions to %LOCALAPPDATA%.
        pause
        exit /b 1
    )
    echo [INFO] Installing LSIA server dependencies...
    "%VENV_DIR%\Scripts\pip.exe" install -e .
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install server dependencies.
        pause
        exit /b 1
    )
)

echo Starting LSIA server on http://0.0.0.0:8080 ...
echo The administration dashboard is accessible at http://127.0.0.1:8080
echo Teachers on the school LAN can sync at http://^<YOUR-LAN-IP^>:8080
echo.
"%VENV_DIR%\Scripts\uvicorn.exe" lsia.main:create_app --factory --host 0.0.0.0 --port 8080
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Server exited with code %ERRORLEVEL%.
)
pause

@echo off
title LSIA Android APK Builder
echo ========================================================
echo   LSIA Teacher Android App - APK Builder
echo ========================================================
echo.

cd /d "%~dp0"

where java.exe >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if "%JAVA_HOME%"=="" (
        echo [ERROR] Java JDK is not found in PATH or JAVA_HOME.
        echo.
        echo To build the Android APK:
        echo 1. Install Java JDK 17 or higher (or Android Studio).
        echo 2. Set JAVA_HOME or run this project from Android Studio.
        echo.
        echo Alternatively, open this folder in Android Studio:
        echo   File -> Open -> %~dp0
        echo   Build -> Build Bundle(s) / APK(s) -> Build APK(s)
        echo.
        pause
        exit /b 1
    )
)

echo Building Android APK...
call gradlew.bat assembleDebug

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] APK built successfully!
    echo Location: app\build\outputs\apk\debug\app-debug.apk
    echo.
) else (
    echo.
    echo [ERROR] Build failed. Please inspect the log above or open in Android Studio.
    echo.
)

pause

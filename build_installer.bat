@echo off
echo ============================================
echo   Building Installer (Inno Setup)
echo ============================================
echo.

REM Check if Inno Setup is installed
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo Inno Setup not found!
    echo.
    echo Download free from: https://jrsoftware.org/isdl.php
    echo Install it, then run this script again.
    echo.
    pause
    exit /b 1
)

echo Using: %ISCC%
echo.

REM Build installer
%ISCC% installer.iss

if errorlevel 1 (
    echo BUILD FAILED!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   INSTALLER CREATED!
echo ============================================
echo.
echo   File: dist\ProductPhotoManager-Setup.exe
echo.
echo   Send this single file to anyone.
echo   They double-click to install with shortcuts.
echo.
pause

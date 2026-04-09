@echo off
echo ============================================
echo   Product Photo Manager - Build .EXE
echo ============================================
echo.

REM Clean previous build
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

echo [1/3] Building with PyInstaller...
pyinstaller ProductPhotoManager.spec --noconfirm

if errorlevel 1 (
    echo.
    echo BUILD FAILED!
    pause
    exit /b 1
)

echo.
echo [2/3] Copying extra files...
copy /y "requirements.txt" "dist\ProductPhotoManager\"
copy /y "app_icon.ico" "dist\ProductPhotoManager\"
if exist "products.csv" copy /y "products.csv" "dist\ProductPhotoManager\"

echo.
echo [3/3] Creating portable ZIP...
powershell -Command "Compress-Archive -Path 'dist\ProductPhotoManager\*' -DestinationPath 'dist\ProductPhotoManager-Portable.zip' -Force"

echo.
echo ============================================
echo   BUILD SUCCESS!
echo ============================================
echo.
echo   EXE:      dist\ProductPhotoManager\ProductPhotoManager.exe
echo   Portable: dist\ProductPhotoManager-Portable.zip
echo.
echo   To distribute:
echo     Option 1: Send the ZIP file (portable, no install needed)
echo     Option 2: Run build_installer.bat to create Setup.exe
echo.
pause

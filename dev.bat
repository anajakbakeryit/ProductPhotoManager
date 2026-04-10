@echo off
title ProductPhotoManager - Dev Mode
color 0A

echo.
echo  ====================================================
echo   Product Photo Manager - Dev Mode
echo  ====================================================
echo.

:: Check Docker
docker info >nul 2>&1
if errorlevel 1 (
    echo  [!] Docker Desktop ไม่ได้เปิด - กรุณาเปิด Docker Desktop ก่อน
    echo.
    pause
    exit /b 1
)

:: Start PostgreSQL
echo  [1/3] Starting PostgreSQL...
docker-compose up -d db
if errorlevel 1 (
    echo  [!] PostgreSQL start failed
    pause
    exit /b 1
)

:: Wait for PostgreSQL to be ready
echo  [*] Waiting for PostgreSQL...
:wait_pg
docker-compose exec -T db pg_isready -U ppm_user -d productphotomanager >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_pg
)
echo  [OK] PostgreSQL ready

:: Install Python deps if needed
if not exist "backend\__installed__" (
    echo.
    echo  [2/3] Installing Python dependencies (first time only)...
    pip install -r backend\requirements.txt -q
    echo. > backend\__installed__
) else (
    echo  [2/3] Python dependencies OK
)

:: Install frontend deps if needed
if not exist "frontend\node_modules" (
    echo.
    echo  [3/3] Installing frontend dependencies (first time only)...
    cd frontend
    call npm install
    cd ..
) else (
    echo  [3/3] Frontend dependencies OK
)

echo.
echo  ====================================================
echo   Starting servers...
echo  ====================================================
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo.
echo   Login: admin / admin1234
echo.
echo   Press Ctrl+C to stop all servers
echo  ====================================================
echo.

:: Open browser after 3 seconds
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5173"

:: Start backend and frontend in parallel
start "PPM-Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.api.main:app --reload --port 8000"
start "PPM-Frontend" cmd /k "cd /d %~dp0\frontend && npx vite --host 0.0.0.0"

echo  Servers started! Check the new terminal windows.
echo  Press any key to stop all servers...
pause >nul

:: Cleanup
echo.
echo  Stopping servers...
taskkill /FI "WINDOWTITLE eq PPM-Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq PPM-Frontend*" /F >nul 2>&1
docker-compose stop db >nul 2>&1
echo  Done!

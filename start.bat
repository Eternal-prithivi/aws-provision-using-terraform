@echo off
REM ═══════════════════════════════════════════════
REM start.bat — Launch the application (Windows)
REM ═══════════════════════════════════════════════
REM
REM Usage:
REM   Double-click this file, OR run: start.bat
REM   To stop: start.bat --stop
REM
REM Prerequisites: Run setup.bat first!
REM ═══════════════════════════════════════════════

setlocal
title AWS Provisioner

REM ── Stop mode ──
if "%1"=="--stop" (
    echo Stopping servers...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING" 2^>nul') do (
        taskkill /PID %%a /F >nul 2>&1
    )
    echo [OK] Backend stopped
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000.*LISTENING" 2^>nul') do (
        taskkill /PID %%a /F >nul 2>&1
    )
    echo [OK] Frontend stopped
    exit /b 0
)

REM ── Check setup ──
if not exist ".venv" (
    echo [X] Virtual environment not found. Run setup.bat first!
    pause
    exit /b 1
)
if not exist "web-ui\frontend\node_modules" (
    echo [X] Node modules not found. Run setup.bat first!
    pause
    exit /b 1
)

REM ── Kill any existing servers ──
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo ╔══════════════════════════════════════════╗
echo ║  AWS Provisioner — Starting...           ║
echo ╚══════════════════════════════════════════╝
echo.

REM ── Start Backend in a new window ──
echo Starting backend API server (port 8000)...
start "AWS Provisioner - Backend" cmd /k "cd /d %~dp0web-ui\api && %~dp0.venv\Scripts\uvicorn.exe server:app --reload --port 8000"

REM Wait for backend
echo Waiting for backend to start...
timeout /t 4 /nobreak >nul

REM ── Start Frontend in a new window ──
echo Starting frontend dev server (port 3000)...
start "AWS Provisioner - Frontend" cmd /k "cd /d %~dp0web-ui\frontend && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ══════════════════════════════════════════
echo   [OK] Application is running!
echo ══════════════════════════════════════════
echo.
echo   Open:  http://localhost:3000
echo   API:   http://localhost:8000/docs
echo.
echo   Login: Eternal-prithivi (no password)
echo.
echo   Two new windows opened for the servers.
echo   Close them to stop, or run: start.bat --stop
echo.

REM Open browser automatically
start http://localhost:3000

pause

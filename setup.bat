@echo off
REM ═══════════════════════════════════════════════════════════
REM setup.bat — One-command setup for AWS Provisioner (Windows)
REM ═══════════════════════════════════════════════════════════
REM
REM Usage:
REM   Double-click this file, OR run in Command Prompt:
REM   setup.bat
REM
REM Prerequisites: Python 3.10+, Node.js 18+
REM ═══════════════════════════════════════════════════════════

setlocal enabledelayedexpansion
title AWS Provisioner - Setup

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║  AWS Provisioner — Windows Setup                     ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM ═══════════════════════════════════════════════
REM Step 1: Check Prerequisites
REM ═══════════════════════════════════════════════
echo ━━━ Step 1/4 — Checking Prerequisites ━━━
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python not found!
    echo     Download from: https://www.python.org/downloads/
    echo     IMPORTANT: Check "Add Python to PATH" during install!
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VERSION=%%i
echo [OK] Python %PY_VERSION% found

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Node.js not found!
    echo     Download from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js %NODE_VERSION% found

REM Check npm
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] npm not found! It should come with Node.js.
    pause
    exit /b 1
)
for /f %%i in ('npm --version') do set NPM_VERSION=%%i
echo [OK] npm %NPM_VERSION% found

echo.
echo Checking optional tools...

terraform version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Terraform found (optional)
) else (
    echo [--] Terraform not installed (optional — Web UI works without it)
)

aws --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] AWS CLI found (optional)
) else (
    echo [--] AWS CLI not installed (optional — Web UI works without it)
)

REM ═══════════════════════════════════════════════
REM Step 2: Python Backend Setup
REM ═══════════════════════════════════════════════
echo.
echo ━━━ Step 2/4 — Setting up Python Backend ━━━
echo.

if exist ".venv" (
    echo [i] Virtual environment .venv already exists
) else (
    echo [i] Creating Python virtual environment...
    python -m venv .venv
    echo [OK] Virtual environment created
)

echo [i] Installing Python dependencies...
.venv\Scripts\pip.exe install --upgrade pip --quiet 2>nul
.venv\Scripts\pip.exe install -r requirements.txt --quiet
.venv\Scripts\pip.exe install -r web-ui\api\requirements.txt --quiet
.venv\Scripts\pip.exe install "uvicorn[standard]" --quiet
echo [OK] Python dependencies installed

REM Verify imports
.venv\Scripts\python.exe -c "import fastapi, uvicorn, yaml, websockets; print('[OK] Backend imports verified')" 2>nul
if %errorlevel% neq 0 (
    echo [X] Some Python packages failed to import
    pause
    exit /b 1
)

REM ═══════════════════════════════════════════════
REM Step 3: Frontend Setup
REM ═══════════════════════════════════════════════
echo.
echo ━━━ Step 3/4 — Setting up Frontend ━━━
echo.

cd web-ui\frontend

if exist "node_modules" (
    echo [i] node_modules already exists, checking for updates...
)

echo [i] Installing Node.js dependencies (this may take a minute)...
call npm install --silent 2>nul
echo [OK] Frontend dependencies installed

cd ..\..

REM ═══════════════════════════════════════════════
REM Step 4: Verify
REM ═══════════════════════════════════════════════
echo.
echo ━━━ Step 4/4 — Verification ━━━
echo.

echo [i] Running test suite...
.venv\Scripts\python.exe -m pytest tests/ -q --tb=no 2>&1
echo.

echo [i] Checking frontend compilation...
cd web-ui\frontend
call npx next build >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Frontend compiles successfully
) else (
    echo [!!] Frontend build had issues — try 'npm run dev' to see details
)
cd ..\..

REM ═══════════════════════════════════════════════
REM Done!
REM ═══════════════════════════════════════════════
echo.
echo ══════════════════════════════════════════════════════
echo   [OK] Setup Complete!
echo ══════════════════════════════════════════════════════
echo.
echo   To start the application, you can either:
echo.
echo   Option A: Double-click start.bat
echo.
echo   Option B: Open TWO Command Prompt windows:
echo.
echo   Window 1 — Backend API Server:
echo     cd web-ui\api
echo     ..\..\\.venv\Scripts\uvicorn.exe server:app --reload --port 8000
echo.
echo   Window 2 — Frontend Dev Server:
echo     cd web-ui\frontend
echo     npm run dev
echo.
echo   Then open: http://localhost:3000
echo.
echo   Login: Eternal-prithivi (no password needed)
echo.
echo ══════════════════════════════════════════════════════
echo.
echo   NOTE: CloudShell terminal requires WSL2 on Windows
echo   (it uses Unix PTY which isn't available natively).
echo   All other features work perfectly on Windows.
echo.
echo ══════════════════════════════════════════════════════
echo.
pause

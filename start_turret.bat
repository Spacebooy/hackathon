@echo off
REM Nerf Turret Startup Script for Windows
REM Run this: start_turret.bat

echo ========================================
echo   NERF TURRET STARTING (Windows)...
echo ========================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/update dependencies
echo Checking dependencies...
pip install -q opencv-python numpy

echo.
echo Starting proximity shooter...
echo NOTE: Motor control disabled on Windows (simulation mode)
echo.
echo Controls:
echo   CLICK - Set shooting point
echo   l     - Toggle lead compensation
echo   +/-   - Adjust fire distance
echo   q     - Quit
echo.

REM Run the shooter
python proximity_shooter.py

pause


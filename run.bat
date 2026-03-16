@echo off
echo ===================================
echo     GROMACS-GUI Startup
echo ===================================
echo.

echo [1/2] Installing dependencies (PyQt6)...
pip install -r requirements.txt

echo.
echo [2/2] Starting GROMACS-GUI...
python src\main.py

pause

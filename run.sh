#!/usr/bin/env bash
set -e

echo "==================================="
echo "     GROMACS-GUI Startup"
echo "==================================="
echo ""

echo "[1/2] Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "[2/2] Starting GROMACS-GUI..."
python3 src/main.py

echo ""
echo "GROMACS-GUI exited."

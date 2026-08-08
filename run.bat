@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem ── 检查 Python ──
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 未找到，请先安装 Python 3.10+ 并加入 PATH。
    pause
    exit /b 1
)

rem ── 依赖检查：缺失时才安装（避免每次启动刷 pip 输出） ──
python -c "import PyQt6, matplotlib, numpy" >nul 2>nul
if errorlevel 1 (
    echo [1/2] Installing dependencies ...
    pip install -r requirements.txt
) else (
    echo [1/2] Dependencies OK
)

rem ── 用 pythonw 启动 GUI（不显示控制台窗口，避免启动时闪黑窗） ──
where pythonw >nul 2>nul
if errorlevel 1 (
    python src\main.py
) else (
    start "" pythonw src\main.py
)

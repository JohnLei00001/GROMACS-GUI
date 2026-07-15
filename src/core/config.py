import os
import shutil
import json

# 配置文件路径：~/.gromacs-gui/config.json
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".gromacs-gui")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

_cached_gmx_path = None


def _detect_from_path():
    """从系统 PATH 中自动检测 gmx 可执行文件"""
    # Linux/macOS 上通常是 "gmx"，Windows 上可能是 "gmx.exe"
    candidates = ["gmx", "gmx_mpi", "gmx_d"]
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    return None


def _load_saved_path():
    """从配置文件读取已保存的路径"""
    try:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved = data.get("gmx_path", "")
            if saved and (os.path.isfile(saved) or shutil.which(saved)):
                return saved
    except Exception:
        pass
    return None


def get_gmx_path():
    """
    获取 GROMACS 可执行文件路径。
    优先级：已缓存的路径 > 配置文件保存的路径 > PATH 自动检测 > None
    """
    global _cached_gmx_path
    if _cached_gmx_path:
        return _cached_gmx_path

    # 1. 尝试加载已保存的路径
    saved = _load_saved_path()
    if saved:
        _cached_gmx_path = saved
        return saved

    # 2. 尝试从 PATH 自动检测
    detected = _detect_from_path()
    if detected:
        _cached_gmx_path = detected
        # 自动保存检测到的路径
        save_gmx_path(detected)
        return detected

    return None


def save_gmx_path(path):
    """保存 GROMACS 路径到配置文件"""
    global _cached_gmx_path
    _cached_gmx_path = path
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"gmx_path": path}, f, indent=2)
    except Exception as e:
        print(f"警告：无法保存配置文件: {e}")


def needs_configuration():
    """检查是否需要首次配置 GROMACS 路径"""
    return get_gmx_path() is None

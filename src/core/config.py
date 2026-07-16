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


def get_gmx_top_dir():
    """
    获取 GROMACS 力场拓扑文件目录 (GMXLIB)。
    优先级：GMXLIB 环境变量 > GMXDATA 环境变量 > 从 gmx 路径推导 > None
    
    GROMACS 需要 GMXLIB 指向 share/gromacs/top 才能找到力场文件。
    如果用户已设置该环境变量，直接沿用；否则尝试从 gmx 可执行文件
    路径推导（假定 <prefix>/bin/gmx → <prefix>/share/gromacs/top）。
    """
    # 1. 优先读取用户已设置的环境变量
    for var in ("GMXLIB", "GMXDATA"):
        env_val = os.environ.get(var, "")
        if env_val and os.path.isdir(env_val):
            return env_val

    # 2. 从 gmx 可执行文件路径推导
    gmx_path = get_gmx_path()
    if gmx_path:
        gmx_bin_dir = os.path.dirname(gmx_path)
        gmx_prefix = os.path.dirname(gmx_bin_dir)
        derived = os.path.join(gmx_prefix, "share", "gromacs", "top")
        if os.path.isdir(derived):
            return derived

    return None


def get_gmx_env():
    """
    构建包含正确 GMXLIB 设置的子进程环境变量字典。
    调用方应使用此字典传递给 subprocess 的 env 参数。
    """
    env = os.environ.copy()
    top_dir = get_gmx_top_dir()
    if top_dir:
        env["GMXLIB"] = top_dir
    return env


def needs_configuration():
    """检查是否需要首次配置 GROMACS 路径"""
    return get_gmx_path() is None


# 水模型 → 溶剂模板文件映射（GROMACS 标准约定）
WATER_TO_SOLVENT = {
    "spce":  "spc216.gro",
    "tip3p": "tip3p.gro",
    "tip4p": "tip4p.gro",
    "tip5p": "tip5p.gro",
}


def get_solvent_template(water_model):
    """
    根据水模型名称返回对应的溶剂模板文件名。
    如果 GMXLIB 中存在对应文件则返回，否则回退到 spc216.gro。
    """
    filename = WATER_TO_SOLVENT.get(water_model, "spc216.gro")
    top_dir = get_gmx_top_dir()
    if top_dir and os.path.isfile(os.path.join(top_dir, filename)):
        return filename
    return "spc216.gro"

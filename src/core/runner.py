import subprocess
import sys
from .config import get_gmx_path, get_gmx_env
from .worker import GromacsWorker

# Windows 下隐藏子进程控制台窗口（gmx.exe 是控制台程序，不隐藏会弹出黑色 CMD 窗口）
def _no_console_kwargs():
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}

class GromacsRunner:
    def __init__(self):
        self.gmx_path = get_gmx_path()

    def is_ready(self):
        """检查 GROMACS 路径是否已配置"""
        return self.gmx_path is not None

    def update_path(self):
        """重新读取配置中的 GROMACS 路径（用于用户首次配置后）"""
        from .config import get_gmx_path as _get
        self.gmx_path = _get()

    def run_command(self, args, cwd=None, input_text=None):
        """
        同步执行 GROMACS 命令并返回输出 (保留用于快速、无阻塞的命令)
        :param args: 参数列表
        :param cwd: 工作目录
        :param input_text: 标准输入内容
        :return: (bool, str) 成功与否，以及输出日志
        """
        if self.gmx_path is None:
            return False, "GROMACS 路径未配置，请先设置 GROMACS 可执行文件路径。"
        cmd = [self.gmx_path] + args
        
        # 设置 GMXLIB 使 GROMACS 能找到力场文件
        env = get_gmx_env()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                input=input_text,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True,
                env=env,
                **_no_console_kwargs()
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"命令执行失败，返回码: {e.returncode}\n\n输出详情:\n{e.output}"
        except Exception as e:
            return False, f"执行出现异常: {str(e)}"

    def create_worker(self, args, cwd=None, input_text=None):
        """
        创建一个异步 Worker 用于执行耗时命令
        """
        return GromacsWorker(self.gmx_path, args, cwd, input_text)

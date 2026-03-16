import subprocess
import os
from .config import get_gmx_path

class GromacsRunner:
    def __init__(self):
        self.gmx_path = get_gmx_path()

    def run_command(self, args, cwd=None):
        """
        执行 GROMACS 命令并返回输出
        :param args: 参数列表，例如 ['pdb2gmx', '-f', 'protein.pdb', '-o', 'processed.gro', '-water', 'spce']
        :param cwd: 工作目录，如果为None则在当前目录执行
        :return: (bool, str) 成功与否，以及输出日志
        """
        cmd = [self.gmx_path] + args
        try:
            # 运行命令，捕获标准输出和标准错误
            result = subprocess.run(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # 将stderr合并到stdout
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"命令执行失败，返回码: {e.returncode}\n\n输出详情:\n{e.output}"
        except Exception as e:
            return False, f"执行出现异常: {str(e)}"

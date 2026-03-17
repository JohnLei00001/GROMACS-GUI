import subprocess
import os
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class GromacsWorker(QThread):
    # 信号定义
    output_signal = pyqtSignal(str)     # 实时输出信号
    finished_signal = pyqtSignal(bool, str)  # 完成信号 (success, final_message)
    
    def __init__(self, gmx_path, args, cwd=None, input_text=None):
        super().__init__()
        self.gmx_path = gmx_path
        self.args = args
        self.cwd = cwd
        self.input_text = input_text

    def run(self):
        cmd = [self.gmx_path] + self.args
        self.output_signal.emit(f">>> 正在后台执行: {' '.join(self.args)}\n")
        
        try:
            # 准备 Popen 参数
            popen_args = {
                "args": cmd,
                "cwd": self.cwd,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "encoding": 'utf-8',  # 显式指定编码，Windows下可能需要根据环境调整，但UTF-8通常兼容性好
                "errors": 'replace',
                "bufsize": 1
            }
            
            if self.input_text:
                popen_args["stdin"] = subprocess.PIPE
                
            process = subprocess.Popen(**popen_args)
            
            # 如果有输入，先写入 (注意：对于需要持续交互的程序，这种一次性写入可能不够，但GROMACS通常是一次性输入)
            if self.input_text:
                try:
                    process.stdin.write(self.input_text)
                    process.stdin.close()
                except Exception as e:
                    pass # 可能进程已经退出了

            # 实时读取输出
            while True:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                self.output_signal.emit(line.strip())

            return_code = process.poll()
            
            if return_code == 0:
                self.finished_signal.emit(True, "命令执行成功")
            else:
                self.finished_signal.emit(False, f"命令执行失败，返回码: {return_code}")
                
        except Exception as e:
            self.finished_signal.emit(False, f"执行异常: {str(e)}")


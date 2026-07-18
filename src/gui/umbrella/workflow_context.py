"""Umbrella Sampling 工作流上下文 —— 替代裸 cwd 字符串的结构化状态传递"""

from dataclasses import dataclass, field
import os


@dataclass
class UmbrellaContext:
    """伞形取样 pipeline 上下文，每步完成后更新并传递给下游"""
    cwd: str = ""

    # ── Build 输出 ──
    structure_file: str = ""       # solvated_ions.gro
    topology_file: str = ""        # topol.top

    # ── EM 输出 ──
    em_gro: str = "em.gro"

    # ── NVT 输出 ──
    nvt_gro: str = "nvt.gro"
    nvt_cpt: str = "nvt.cpt"

    # ── NPT 输出 ──
    npt_gro: str = "npt.gro"
    npt_cpt: str = "npt.cpt"

    # ── Pull 输出 ──
    pullx_xvg: str = "pullx.xvg"

    # ── Window 输出 ──
    windows: list = field(default_factory=list)  # [(start_dist, ref_dist, dir_name)]

    # ── 辅助方法 ──
    def resolve(self, filename: str) -> str:
        """将相对文件名解析为绝对路径"""
        if not self.cwd or not filename:
            return ""
        return os.path.join(self.cwd, filename)

    def validate_files(self, *filenames: str) -> list[str]:
        """验证文件是否存在，返回缺失文件列表"""
        missing = []
        for f in filenames:
            path = self.resolve(f)
            if not path or not os.path.exists(path):
                missing.append(f)
        return missing

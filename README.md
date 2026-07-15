# GROMACS-GUI

[中文](./README.md) | [English](./README.en.md)

GROMACS-GUI 是一个基于 Python 与 PyQt6 的桌面工具，用于将常见的 GROMACS 分子动力学流程组织为更清晰的图形界面操作。

项目当前重点覆盖两类工作流：标准溶液体系模拟，以及蛋白-配体复合物体系构建与后续模拟。

## 项目概览

### Solution Simulator

面向常规溶液体系，当前支持以下流程：

- 拓扑生成与模拟盒定义
- 能量最小化
- NVT / NPT 平衡
- 生产模拟
- 轨迹处理与基础分析

其中能量最小化、平衡和生产阶段均提供 MDP 参数编辑能力；分析模块支持 `RMSD`、`RMSF`、`gyrate` 计算与绘图。

### Ligand Simulator

面向蛋白-配体复合物体系，当前支持以下流程：

- 导入外部工具生成的配体拓扑与结构文件，如 `CGenFF`、`ATB`、`ACPYPE`
- 受体蛋白 `pdb2gmx` 处理
- 蛋白与配体坐标合并
- `topol.top` 自动更新
- 溶剂化与离子添加
- 与后续 EM、EQ、MD、分析流程衔接

## 当前状态

当前已实现的核心模块：

- `Solution Simulator`
- `Ligand Simulator`

计划中的模块：

- `Membrane Simulator`
- `Polymer Simulator`

## 技术栈

- Python 3
- PyQt6
- Matplotlib
- GROMACS

## 安装

### 环境要求

1. 安装 Python 3.8 或更高版本
2. 安装可用的 GROMACS 环境

### 安装步骤

```bash
git clone https://github.com/JohnLei00001/GROMACS-GUI.git
cd GROMACS-GUI
pip install -r requirements.txt
```

## 配置

运行前请先在 [`src/core/config.py`](./src/core/config.py) 中设置本地 `gmx.exe` 路径：

```python
GMX_PATH = r"C:\path\to\your\gmx.exe"
```

## 运行

Windows:

```bash
run.bat
```

或直接执行：

```bash
python src/main.py
```

## License

[MIT License](LICENSE)

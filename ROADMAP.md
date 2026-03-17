# 🗺️ GROMACS-GUI 开发路线图 (Roadmap)

我们已经成功完成了 **Phase 1: 基础水溶液蛋白模拟 (Solution Simulator)** 的核心功能。基于 "Simulator" 的产品定位，未来的开发将围绕**复杂体系构建**与**高级模拟功能**展开。

以下是详细的未来规划：

## 🚀 Phase 2: 配体与药物设计 (Ligand Simulator) - *Next Priority*
**目标**: 解决 GROMACS 最大的痛点——小分子配体拓扑生成的繁琐性，实现“蛋白-配体”复合物模拟的自动化。

*   **[核心] 小分子拓扑自动生成**:
    *   集成 `ACPYPE` (AnteChamber PYthon Parser interfacE) 或 `OpenBabel`。
    *   支持从 `.mol2` / `.sdf` 文件直接生成 `.itp` 和 `.gro` 文件。
    *   自动处理电荷分配 (GAFF 力场)。
*   **[流程] 复合物构建**:
    *   自动将配体插入蛋白结合位点 (或读取已对接好的结构)。
    *   修改 `topol.top` 以包含配体拓扑。
*   **[分析] 相互作用分析**:
    *   配体 RMSD。
    *   MMPBSA 结合自由能计算接口 (gmx_MMPBSA)。

## 🌊 Phase 3: 膜蛋白模拟 (Membrane Simulator)
**目标**: 构建复杂的磷脂双分子层体系，支持膜蛋白模拟。

*   **[构建] 膜构建器**:
    *   支持常见脂质类型 (POPC, DPPC, DMPC 等)。
    *   自动生成双分子层结构。
*   **[嵌入] 蛋白嵌入**:
    *   使用 `gmx membed` 或类似算法将蛋白定向插入膜中。
    *   去除与蛋白重叠的脂质分子。
*   **[分析] 膜性质分析**:
    *   膜厚度、面积/脂质、序参数 (Order Parameters)。

## 🧬 Phase 4: 聚合物与材料 (Polymer Simulator)
**目标**: 拓展至非生物体系，支持长链聚合物与材料科学模拟。

*   **[拓扑] 聚合物拓扑**:
    *   支持重复单元的自动连接。
    *   定制化力场支持 (OPLS-AA, GROMOS 等)。

## ⚡ Phase 5: 高级功能与 HPC 集成
**目标**: 从“桌面工具”进化为“生产力平台”。

*   **HPC 任务提交**:
    *   一键生成 Slurm / PBS / LSF 作业脚本。
    *   支持断点续传 (`-cpi`) 的脚本配置。
*   **远程执行**:
    *   通过 SSH 连接远程超算，提交任务并回传日志。
*   **交互式 3D 可视化**:
    *   尝试在 PyQt 中集成 `OpenGL` 或 `py3Dmol`，实现简单的结构实时预览，减少对外部软件的依赖。

## 🛠️ 持续优化 (General Improvements)
*   **力场管理**: 提供更直观的力场选择与自定义力场导入功能。
*   **多链支持**: 优化 Solution Simulator 以更好地支持多聚体蛋白 (Multimers) 和核酸 (DNA/RNA)。
*   **错误诊断**: 建立常见 GROMACS 报错知识库，提供更智能的报错建议（不仅仅是显示日志）。

# 2026-10-31 全量案例维护核查

[协作记录](collaboration.md) · [证据核查](../../references/ch04-evidence.md)

执行者：代码助手；这不是组员独立复现的签认。检查版本：`e2467027f37de204303787d87e6936fadcd992ac`。运行平台Linux，Python 3.12.14；存档指标记录Python 3.12.13。两次numpy均为2.3.5、scikit-learn均为1.8.0；本次pandas 2.2.3、scipy 1.17.0。没有据此认定Python补丁版本就是差异原因。

实际运行命令（输出目录位于仓库外，不覆盖存档结果）：

```bash
python -u code/ch04_exercises/rruff_full/reproduce.py --output /workspace/scratch/00495f44dcd1/audit_reproduced
```

完成训练、最终全量拟合、核验及导出，进程退出码0。最终日志：

```text
PASS: 7215 checks; 5228 source rows, 5218 final training rows, 3419 held-out rows per model.
Exported figures and offline browser data.
PASS: all usable records fitted; held-out metrics independently verified; display exported.
```

| 检查项 | 实际结果 |
|---|---|
| 验证组分折与协议 | `group_folds.csv`内容一致；每条谱的fold一致；`protocol.json`逐字节一致 |
| 多数类、余弦近邻、SVM | 各模型逐谱预测表与存档一致 |
| PCA8＋逻辑回归 | 存档839/1789＝46.8977%；本次833/1789＝46.5623%；30/3419条谱、25/1789组预测标签不同 |
| PCA宏F1 | 存档0.3540876310；本次0.3500107077 |
| 非模型元数据 | `spectrum_folds.csv`中21条axis_min在CSV往返后出现约10⁻¹³量级差异；分折未变 |
| 内置检查的含义 | 核对当前运行的内部一致性；通过不等于与历史存档的每个预测都相同 |

另运行 `node code/ch04_exercises/raman/test_interactive.cjs`，输出：`PASS: 8 split views and 15 panel confusion matrices match exported data.` 这属于导出数据/计算检查，不等于实际浏览器演示通过。本环境的浏览器可执行文件缺失，页面操作与汇报电脑检查待组员完成。

本分支新增误判解释脚本，实际导出3个案例并验证参考谱来自对应训练折。近邻误判536组，六对选定关系涉及19组，237组被预测为仅训练类别。此处只复查并解释已有结果，不更新原模型成绩。

后续由YYY独立运行并保存自己的日志；PCA差异需要定位数值环境、求解过程或其他因素后再决定是否更新基准。维护检查不替代成员对方法和限制的理解。

## 2026-11-01补充检查

基于最新主分支`6a34450f978baa3c0c215d1e6ef71f166327bc0c`建立`ch04/evidence-review-20261101`。保留其14页汇报结构、原图与交互讲解，更新正文、页内结论与备注；没有再次训练四个主模型，也未覆盖存档指标。

- 实际运行`explain_errors.py --output /workspace/scratch/00495f44dcd1/evidence_check_20261101`，3例存档误判均复现近邻标签、训练参考与验证组隔离；5个误判解释输出与前次结果逐字节一致。
- 再次运行`node code/ch04_exercises/raman/test_interactive.cjs`，8个划分视图与15个混淆矩阵数据检查通过。本次没有新的实际浏览器操作。
- 核查14页PPT的全部文字替换与讲稿，保留4张原生表格和全部原图数据；逐页渲染查看，无文字裁切。PPTX结构、字体、尺寸与导入检查通过；未在Microsoft PowerPoint实机打开。
- 核查Python语法、修改文档的相对文件链接与第4章33项书目。生成器的文字修订与来源PPT逐项匹配；原生成器依赖macOS Chrome路径及指定字体，本次未宣称完整运行该生成器。

新增解释保留两个边界：第10页全库平均谱不等于折外个例；第9页Wilson近似区间未校正类别内及交叉验证依赖。组员复核状态仍由本人实际执行后填写。

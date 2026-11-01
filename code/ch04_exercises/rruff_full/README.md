# 全量RRUFF案例与误判解释

[方法与数据范围](../../../docs/ch04.md) · [来源清单](data/manifest.csv) · [来源元数据](data/provenance.json) · [结论与引文](../../../resources/annual/2026-2027/references/ch04-evidence.md)

固定数据：DTU存档v1（DOI：10.11583/DTU.20222331.v1，CC BY 4.0）；来源5,228条，隔离10条，最终训练5,218条。原始数据库为RRUFF；已处理谱由Li、Schmidt、Alstrøm存档，本项目插值到304–852 cm⁻¹后建模。原始归属与存档说明另见[ATTRIBUTION](../rruff_real/ATTRIBUTION.md)。

## 运行

从仓库根目录安装锁定依赖，再运行：

```bash
python -m pip install -r code/ch04_exercises/raman/requirements.txt
python code/ch04_exercises/rruff_full/reproduce.py
python code/ch04_exercises/rruff_full/explain_errors.py
```

第一条实验命令把重新训练的结果写到`rruff_full/reproduced/`，不自动覆盖已归档结果。第二条读取`outputs/`中的存档近邻折外预测，重新检索各案例所属折的训练近邻，输出误判解释材料；它不重新计算或替换四模型总成绩。

## 误判解释的选择规则

`mineral_relations.json`列六对由文献支持矿物学关系的案例及来源。本组尚未对所有错误建立完整家族标注，不能将这六对视为全局最高频错误或宣称同族错误占多数。

图示固定使用Amblygonite→Montebrasite、Pyrope→Almandine、Grossular→Andradite。每对按验证组ID、谱ID字典序取首个符合存档误判的谱，比较其在该折训练集中的最近谱和最近同类别谱；不按图形相似程度选例。脚本会拒绝同组泄漏、参考类缺失或无法复现的存档近邻标签。

输出：`mineral_error_pairs.csv`（计数与文献）、`error_examples.csv`（身份与相似度）、`error_example_spectra.csv`（逐点绘图数据）、`error_examples.svg`（可编辑图）、`error_evidence.json`（选择规则和输入SHA-256）。

## 结果解释

评分覆盖606类/1,789组，参考库覆盖1,669类；单组类别只参与训练。六对选定误判共19/536组。矿物学关系支持提出解释，不证明特定样本错误的成因。完整限制见正文4.8.7–4.8.8。

2026-10-31维护复现中PCA结果与存档有差异，详见[运行记录](../../../resources/annual/2026-2027/student-reports/ch04/validation-2026-10-31.md)；其他三个模型预测一致。`verify.py`验证内部一致性，不自动保证跨环境与存档逐项相同。

## 汇报结论与讲稿

`build_report.py`保留原14页版式，保存前由`apply_report_evidence.py`应用`report_evidence.json`中的核查修订，覆盖页面文字和备注讲稿。替换目标必须在指定页出现一次，否则中止，提示先复核新的结果与表述；避免更新数字后继续沿用旧结论。可用 `python code/ch04_exercises/rruff_full/build_report.py` 在具备原脚本所需python-pptx、matplotlib、指定字体及Chrome的环境重新生成。原脚本的Chrome路径仍为macOS路径；其他系统需先调整。本次未声称完整运行该生成器。

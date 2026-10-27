# 智能分析化学 · G04 小组工作区

我们负责第4章机器学习，当前主案例使用DTU存档中的**全部5,228条实测拉曼谱来源记录**，讲清数据质量审查、矿物分类与分组验证。原来的52条三分类案例保留为入门演示，模拟实验用于说明数据泄漏和仪器变化。

## 先看这些材料

- **课堂汇报：** [全量版PPT](resources/annual/2026-2027/student-reports/ch04/G04-Raman-Full-Report-new.pptx)，逐字讲稿与答辩准备在每页备注中。
- **教材正文：** [第4章](docs/ch04.md)，全量实测案例在4.8.7节。
- **代码与数据：** [全量代码与输出](code/ch04_exercises/rruff_full/)，方法见第4章4.8.7节。
- **交互演示：** [全量页面](assets/interactive/ch04-full.html)、[三分类入门](assets/interactive/ch04-real.html)、[模拟泄漏](assets/interactive/ch04.html)。
- **组内协作：** [要求对照](resources/annual/2026-2027/student-reports/ch04/README.md)、[分工与复现说明](resources/annual/2026-2027/student-reports/ch04/collaboration.md)。

## 全量实验用了多少数据

| 范围 | 数量与用途 |
|---|---|
| 来源记录 | 5,228条谱，2,858个标本ID，1,674类 |
| 冲突隔离 | 10条记录，原因保留在完整清单中 |
| 最终训练 | 5,218条谱，2,853个标本，1,669类；四个模型均已完成拟合 |
| 五折验证 | 3,419条谱，1,790个标本合为1,789组，覆盖606类 |
| 仅训练类别 | 1,063类只有一个验证组，没有同类新标本的验证分数 |

谱来自[DTU作者存档v1](https://doi.org/10.11583/DTU.20222331.v1)，许可CC BY 4.0，原始数据库RRUFF。光谱已由来源方处理，本组没有新做仪器测量。为让所有可用谱具有共同输入，本实验使用304–852 cm⁻¹的275点网格，不外推、不补零。共同区间之外的峰没有参与分类。

| 固定模型 | 组级正确率 | 宏F1 |
|---|---:|---:|
| 多数类基线 | 1.06% | 0.000035 |
| 余弦近邻 | 70.04% | 0.677584 |
| PCA8＋逻辑回归 | 46.90% | 0.354088 |
| RBF-SVM | 71.10% | 0.671116 |

这些是606个可验证类别的数据库内分组成绩，没有独立外部实验室测试。SVM正确率略高，近邻宏F1略高；本次没有调参或差异显著性检验。最终模型用全部5,218条可训练谱重新拟合，其训练分数不作为测试成绩。

## 打开交互页面

只看演示不需要安装Python。下载或复制**整个项目目录**，保留相邻文件，双击 `assets/interactive/ch04-full.html`。选择矿物、光谱与模型，查看来源身份和折外预测。单组类别会明确显示“仅参与训练”。页面离线读取实际计算结果，不在浏览器中重新训练。

建议演示顺序：Quartz的折外预测与模型切换；Abelsonite的仅训练提示；打开 `ch04.html` 对比随机和按标本划分。GitHub的HTML文件页面显示源码，需要完整下载后打开。

## 复现全量实验

在仓库根目录，使用Python 3.12虚拟环境并安装依赖：

```bash
python -m venv .venv
# Windows：.venv\Scripts\activate
# macOS/Linux：source .venv/bin/activate
python -m pip install -r code/ch04_exercises/raman/requirements.txt
python code/ch04_exercises/rruff_full/reproduce.py
```

输出放入 `rruff_full/reproduced/`，其中包括预测、图表和四个最终模型。默认读取附带数值矩阵，无需重新下载来源ZIP。[第4章4.8.7节](docs/ch04.md)解释记录排除、相同输入合组、折分配和评价范围。

完整教材预览：`python -m http.server 8000`，访问 `http://localhost:8000/#/docs/ch04`。完整教材依赖外部脚本，需要联网；独立交互页面可离线使用。

## 作业材料与提交

按课程截图，总评为大作业70%＋汇报30%。现有材料包括正文、可编辑图解、24项来源与3张前沿卡、8道传承题及答案、可运行代码、全量与模拟交互，以及8页全量汇报。模型数量和数据量不是单独的评分指标，具体要求见[评分对照](resources/annual/2026-2027/student-reports/ch04/README.md)。

当前仍在小组仓库完善材料。实际分工、组员理解、课堂排练、正式Issue/PR与交叉评审按真实完成情况落实。课程主分支由教师或助教审核合并。

本项目基于[课程原仓库](https://github.com/Oaham725/intelligent-analytical-chemistry)。旧 `G04-Raman-Real-Report` 为52条三分类入门课件，`G04-Raman-Report` 为模拟课件，当前课堂主稿是 `G04-Raman-Full-Report`。

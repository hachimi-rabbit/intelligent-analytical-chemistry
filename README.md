# 智能分析化学 · G04 小组工作区

我们负责第4章机器学习，以**真实拉曼谱的矿物分类与按标本验证**为主案例，讲清机器学习怎样预测未见样品、如何避免数据泄漏。另保留受控模拟，用于解释仪器变化与泛化失败。本仓库基于[课程原仓库](https://github.com/Oaham725/intelligent-analytical-chemistry)的教材底稿继续完善，小组新增工作集中在第4章及其配套资源。

**当前阶段：在自己的仓库完善材料。** 已核验成果汇总在本仓库 [`main`](https://github.com/hachimi-rabbit/intelligent-analytical-chemistry/tree/main) 主分支，打开仓库首页即可阅读。暂不创建或重新开启课程仓库的 Issue / PR；正式提交由作者确认后安排。

## 第一次打开，从这里开始

1. **想知道最终交什么、现在缺什么：** 阅读[要求对照与待办清单](resources/annual/2026-2027/student-reports/ch04/README.md)。
2. **想理解专题内容：** 阅读[第4章正文](docs/ch04.md)，再看[汇报PDF](resources/annual/2026-2027/student-reports/ch04/G04-Raman-Real-Report.pdf)。
3. **想体验互动：** 按下方“打开互动页面”的步骤操作。
4. **负责代码复现：** 阅读[真实谱运行说明](code/ch04_exercises/rruff_real/README.md)，其中有安装命令、输出解释和检查方法。

GitHub仓库可以理解为带修改历史的网上项目文件夹；README就是这份使用说明。`.md`是文字材料，`.py`是Python程序，`.csv`是数据表，`.svg`是可编辑图，`.html`是网页，`.pptx`和`.pdf`是汇报文件。

## 最后要交的成果，以及现在已有的材料

按本次课程评分截图，总评为**大作业70%＋课堂汇报30%**。完整权重与验收条件见[要求对照](resources/annual/2026-2027/student-reports/ch04/README.md)。

| 成果 | 打开材料 | 当前状态 |
|---|---|---|
| 第4章教材内容 | [正文](docs/ch04.md) | 4.1–4.9节已有初稿，覆盖基础方法、验证、解释、案例和前沿 |
| 图解与结果图 | [知识图谱](assets/graphs/ch04.svg)、[验证流程图](assets/graphs/ch04-validation.svg)、[真实谱实验输出](code/ch04_exercises/rruff_real/outputs/) | 已有可编辑SVG；正文分别嵌入实测谱与分组结果、模拟对照图 |
| 参考文献与前沿 | [年度第4章引文](resources/annual/2026-2027/references/README.md#ch04)、[正文前沿卡](docs/ch04.md) | 24项来源、3张前沿卡；已统一书目格式；重点来源已复核，仍需组员核读 |
| 传承题与答案 | [第4章题目](resources/annual/2026-2027/questions/README.md#ch04) | 已有6道题及评分要点 |
| 可复现代码与数据说明 | [真实谱代码说明](code/ch04_exercises/rruff_real/README.md)、[52条谱来源清单](code/ch04_exercises/rruff_real/data/manifest.csv) | 已有一条命令复现、分步日志和结果一致性检查，待组员独立复现 |
| 互动学习模块 | [真实谱互动页面](assets/interactive/ch04-real.html) | 查看52条实测谱、来源身份和四个模型；另保留模拟交互 |
| 课堂汇报 | [PPTX](resources/annual/2026-2027/student-reports/ch04/G04-Raman-Real-Report.pptx)、[PDF](resources/annual/2026-2027/student-reports/ch04/G04-Raman-Real-Report.pdf)、[讲稿](resources/annual/2026-2027/student-reports/ch04/speaker-notes-real.md) | 已有12页初稿，待分工、排练和实际汇报 |
| 协作与正式提交 | [课程流程](docs/course/workflow.md) | 已有个人分支提交记录；正式提交、真人交叉评审和教师审核尚未完成 |

上述数量是现有材料数量，不是教师规定的篇数、题数或页数。材料齐备和自动检查通过，不等于已经获得课程评分或完成课堂汇报。

## 打开互动页面

GitHub中的HTML文件链接通常展示源文件，不会直接运行交互。只看互动模块，不需要安装Python：

1. 在仓库左上方分支菜单确认当前为 `main`。
2. 点击绿色 **Code → Download ZIP**，下载并完整解压当前分支。
3. 在解压后的文件夹中，依次打开 `assets` → `interactive`，双击 `ch04-real.html`。
4. 选择矿物谱与模型，查看RRUFF ID、激光波长、折外预测及标本级混淆矩阵。模拟扩展另打开 `ch04.html`。

保留整个解压目录，页面需要相邻的CSS和JS文件。模块使用已有Python计算结果，浏览器负责交互展示，不会现场重新训练模型，也不需要联网下载数据。

若要预览完整教材，安装Python后，在包含本README的仓库根目录打开终端并运行：

```bash
python -m http.server 8000
```

Windows也可使用 `py -m http.server 8000`。随后访问 `http://localhost:8000/#/docs/ch04`。完整教材依赖外部网页脚本，需要联网；独立互动页可离线使用。

## 接下来小组先做什么

- [ ] 确认组员和实际分工，在个人工作记录中写清负责人及对应修改。
- [ ] 由另一位组员按运行说明独立复现，记录环境、命令、结果和遇到的问题。
- [ ] 核读正文与已嵌入的结果图，试做传承题，检查论述是否得到文献和数据支持。
- [ ] 在汇报用电脑上演示互动页面，准备PPT分工并排练答辩。
- [ ] 作者确认可以正式提交后，再按课程流程办理任务登记、Issue、PR和交叉评审。

建议按“正文与公式、代码与复现、文献与题目、图表与汇报”分工，每人从个人仓库的 `main` 建立任务分支。具体操作见[组内协作与复现记录](resources/annual/2026-2027/student-reports/ch04/collaboration.md)。组员姓名和贡献按实际工作填写。

## 数据范围与使用限制

**真实主案例：** 从[DTU作者存档v1](https://doi.org/10.11583/DTU.20222331.v1)取得52条来源方已处理的实测RRUFF谱，包含石英10、方解石10、石膏2个标本ID。已保留来源、CC BY 4.0归属和数据校验和，按ID做22折留一验证。三个分类模型的标本宏F1均为1.0000，多数类基线为0.2083。石膏标本太少且尚无外部测试，高分只描述当前小数据集。不同激光波长不能当作不同仪器，本次不作真实跨仪器结论。

**模拟教学对照：** `code/ch04_exercises/raman/`仍全部为生成数据，包括90个模拟标本、540条谱、四个基线、199次标签置换及五种子的预处理比较。模拟的A/B下降和arPLS改善不属于真实数据结果。历史[模拟汇报](resources/annual/2026-2027/student-reports/ch04/G04-Raman-Report.pdf)保留供参考，当前课堂稿使用上方真实数据汇报。

详细来源、方法、结果和限制见[真实谱说明](code/ch04_exercises/rruff_real/README.md)及[模拟说明](code/ch04_exercises/raman/README.md)。

## 教材来源与发布状态

保留的其他章节、课程流程和原始目录来自[课程原仓库](https://github.com/Oaham725/intelligent-analytical-chemistry)。可查看[全书阅读说明](docs/README.md)、[课程任务地图](docs/course/task-map.md)和[课程量规](docs/course/rubric.md)。本页介绍G04个人工作区，不代表课程维护方的正式公告。

仓库已有Pages工作流，`main` 推送符合其触发条件；是否成功发布取决于本仓库的Actions与Pages设置，不能仅凭推送成功判断网站已更新。原有 `publish_github.sh` 是发布工具，不属于阅读或复现实验的步骤；本阶段先使用上述文件与本地预览方式。

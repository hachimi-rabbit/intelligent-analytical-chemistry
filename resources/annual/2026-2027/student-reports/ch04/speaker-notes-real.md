# G04 真实拉曼谱汇报讲稿

当前主案例使用52条实测谱、22个标本ID。建议12分钟，根据实际要求调整。

## 第1页

来源：Li, Schmidt & Alstrøm，DTU数据集v1，DOI:10.11583/DTU.20222331.v1，CC BY 4.0。论文DOI:10.1039/D2AN00403H。原始RRUFF归属见ATTRIBUTION.md。 本稿为学生汇报初稿。建议12分钟，组员根据教师要求调整。主案例已实际运行，但不等于学生已独立复现或完成课堂汇报。

## 第2页

完整章节见docs/ch04.md。基础来源：Hastie et al., DOI:10.1007/978-0-387-84858-7。输入为固定区间的谱强度，目标为三个矿物标签，部署目标暂限定到数据库内未见ID。

## 第3页

来源：Li, Schmidt & Alstrøm，DTU数据集v1，DOI:10.11583/DTU.20222331.v1，CC BY 4.0。论文DOI:10.1039/D2AN00403H。原始RRUFF归属见ATTRIBUTION.md。 作者存档是历史RRUFF衍生数据。先按raw==0过滤元数据并重置索引，按作者实现匹配5228条谱，选取三类全部记录。manifest记录每条谱的来源、标本及校验和。

## 第4页

来源：Li, Schmidt & Alstrøm，DTU数据集v1，DOI:10.11583/DTU.20222331.v1，CC BY 4.0。论文DOI:10.1039/D2AN00403H。原始RRUFF归属见ATTRIBUTION.md。 展示各类按来源顺序排列的第一条谱，不按分类效果挑选。每条谱在200–1200 cm^-1线性插值，L2归一化。完整52条谱见交互页。无新增测量点或合成样本。

## 第5页

来源：rruff_real/run.py及outputs/folds.json。每折留出一个ID，训练侧21个ID。RRUFF ID只作为当前分组代理，尚未排除共同产地或母岩依赖。

## 第6页

来源：rruff_real/outputs/protocol.json。所有候选均报告，没有基于本轮分数选优。PCA8_LR的标准化和PCA在训练折内拟合。大量调参应改用嵌套分组验证或新外部留出。

## 第7页

来源：rruff_real/outputs/metrics.json、specimen_predictions.csv。宏F1在汇总全部折外标本预测后计算，非对单类验证折得分取平均。三个非平凡模型逐谱也为52/52正确。

## 第8页

来源：数据manifest及metrics.json的限制项。石膏只有2个ID，留出一个后仅另一个ID供训练。未来调参不能反复使用当前折外分数冒充外部检验。

## 第9页

来源：raman/outputs/metrics.json与extensions_summary.json。种子2026是已查看的历史教学基准。模拟A/B均为生成仪器，不是实测设备；处理前后同时改变基线扣除与归一化。

## 第10页

从完整仓库解压后双击assets/interactive/ch04-real.html。程序命令：python code/ch04_exercises/rruff_real/reproduce.py 。安装依赖见真实谱README。页面只展示预计算结果。

## 第11页

REFORMS: Kapoor et al., Science Advances 2024, DOI:10.1126/sciadv.adk3452。Lilek et al., Journal of Raman Spectroscopy 2025, DOI:10.1002/jrs.6842。TabPFN: Hollmann et al., Nature 2025, DOI:10.1038/s41586-024-08328-6。完整来源与证据边界见年度引文。六道传承题供课后讨论，其中题5和题6对应真实数据。

## 第12页

来源：Li, Schmidt & Alstrøm，DTU数据集v1，DOI:10.11583/DTU.20222331.v1，CC BY 4.0。论文DOI:10.1039/D2AN00403H。原始RRUFF归属见ATTRIBUTION.md。 当前仅完善hachimi-rabbit/intelligent-analytical-chemistry主分支。上游Issue和PR暂缓，正式提交、真人交叉评审和课堂汇报尚未完成。
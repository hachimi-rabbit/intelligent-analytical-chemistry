# G04 汇报讲稿

## 第1页

建议汇报总时长12分钟。本报告是第4章的案例讲解，不代表实测矿物鉴定。学生汇报稿，尚未经教师审核。

## 第2页

重点不是比较热门模型排名，而是把表达能力、化学假设与验证成本联系起来。基础来源：Hastie et al., The Elements of Statistical Learning, DOI:10.1007/978-0-387-84858-7。详细推导见docs/ch04.md。

## 第3页

数据来源：exercise.py，固定种子2026，outputs/simulation_config.json、metadata.csv。90×2×3=540。独立统计对象是物理标本。601个波数变量。开发B谱保留在数据中但不参与分析。

## 第4页

按标本分组StratifiedGroupKFold四折。Scaler、PCA在训练折内拟合。候选固定为Dummy、1NN、PCA_LR、RBF_SVC。CV分数参与选模，最终性能看未见标本。大量调参时使用嵌套分组CV。来源：Cawley & Talbot, JMLR 2010, https://www.jmlr.org/papers/v11/cawley10a.html 。

## 第5页

来源：outputs/model_comparison.csv；汇总72个标本的四折折外预测，宏F1。逐谱随机只作为反例。其事后投票不能消除训练阶段已经存在的身份信息。

## 第6页

来源：extensions.py、outputs/permutation_scores.csv。固定随机源20261023，199次均衡标本级标签置换，1NN；同一标本三条扫描共享随机标签。分位数仅描述此置换过程，不是矿物识别置信区间，也没有计算正式显著性p值。

## 第7页

来源：outputs/holdout_sample_predictions.csv、metrics.json。通过开发分组CV选择RBF-SVC，冻结后在同一18个标本的A/B谱上预测。A/B并非36个独立标本。此种子2026结果已被查看，仅作为历史教学基准。

## 第8页

来源：extensions.py，outputs/preprocessing_panel.csv。五个固定种子1101—1105，全部候选与结果均报告。处理为arPLS(lambda=1e5,max_iter=30,tol=1e-3)与L2归一化，再SVC(C=10,gamma=scale)。原始流程含变量标准化。方法：Baek et al., Analyst 2015, DOI:10.1039/C4AN01061B。

## 第9页

来源：03_probability_calibration.py、outputs/calibration.json；独立二分类模拟2400个样本，与拉曼数据分开。拟合1440、校准480、阈值验证240、测试240。阈值在验证集上按FN/FP代价选择，冻结后测试。Guo et al., ICML2017 https://proceedings.mlr.press/v70/guo17a.html 。

## 第10页

REFORMS: Kapoor et al., Science Advances 2024, DOI:10.1126/sciadv.adk3452。Lilek et al., Journal of Raman Spectroscopy 2025, DOI:10.1002/jrs.6842。TabPFN: Hollmann et al., Nature 2025, DOI:10.1038/s41586-024-08328-6。正式来源和完整作者见年度引文。

## 第11页

离线页面assets/interactive/ch04.html保留相邻CSS/JS即可使用；展示真实Python预计算结果，不在浏览器训练。四道传承题含评分要点，见resources/annual/2026-2027/questions/README.md#ch04。

## 第12页

完整交付见docs/ch04.md、code/ch04_exercises/raman/README.md。当前成果：https://github.com/hachimi-rabbit/intelligent-analytical-chemistry/tree/main 。材料在个人仓库完善，课程Issue与PR暂缓。实验数据全部为模拟。真实配对验证需独立标本、仪器元数据、固定流程与新留出集，不应使用历史测试结果反复优化。
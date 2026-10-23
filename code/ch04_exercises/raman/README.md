# G04 拉曼分类与泛化验证

本练习支撑第4章机器学习的整章教学，核心问题是重复扫描如何影响验证，以及模型怎样应对新仪器。全部谱图为教学模拟，没有使用实测矿物数据或RRUFF谱图。运行无须GPU、API密钥或网络数据下载。

## 从干净环境运行

建议Python 3.12，从仓库根目录执行。依赖文件锁定本次实际运行的版本。首次安装需要访问PyPI。

```bash
python -m venv .venv-g04
# Linux/macOS
.venv-g04/bin/python -m pip install -r code/ch04_exercises/raman/requirements.txt
.venv-g04/bin/python code/ch04_exercises/raman/exercise.py
.venv-g04/bin/python code/ch04_exercises/raman/extensions.py
.venv-g04/bin/python code/ch04_exercises/03_probability_calibration.py --output code/ch04_exercises/raman/outputs/calibration.json
.venv-g04/bin/python code/ch04_exercises/raman/export_interactive.py
.venv-g04/bin/python code/ch04_exercises/raman/verify.py
```

Windows把`.venv-g04/bin/python`换为`.venv-g04\Scripts\python.exe`。也可激活虚拟环境后直接使用`python`。若只阅读，已有小型输出和离线交互页可直接使用。完整执行通常为数分钟，取决于CPU和线性代数线程设置。

## 数据与实验规则

90个模拟物理标本，每类30个；每台仪器每个标本3次扫描，合计540条601维谱。72个开发标本只使用A谱，18个留出标本同时在A、B上测量。开发标本的B谱不参与拟合、选模或评价。详细字段见`outputs/data_dictionary.txt`。

`exercise.py`保留种子2026的历史基准：4个固定候选，4折逐谱/分组比较，按开发分组宏F1选出RBF-SVC。A/B留出宏F1约0.8364/0.2081。这个已被查看的基准不能再当作未查看的测试集去优化。

`extensions.py`预先写入五个种子1101–1105和固定处理参数，所有候选、种子和留出结果均报告。比较原始变量标准化SVC、arPLS与L2归一化SVC、多数类。选择先于留出预测，只依据开发分组结果；留出上报告全部固定候选用于配对流程对照。原始与处理后B宏F1均值约0.2783/0.9888，属于简化模拟，并非真实迁移证据。

`ArPLS`为逐谱基线估计，λ=1e5、最多30轮、相对权重收敛阈值1e-3，之后L2归一化。没有利用真实模拟峰移做逆变换，也没有波数轴校准。算法来源：[Baek et al., Analyst 2015](https://doi.org/10.1039/C4AN01061B)。当前比较同时改变基线处理与归一化，不能单独归因。

负对照固定随机源20261023，对72个开发标本做199次均衡标签置换，同一标本重复谱继承标签。逐谱随机/按标本分组宏F1均值约0.9818/0.3335。分位数是该随机标签过程的描述，不是正任务置信区间。

## 输出和追溯

| 文件 | 内容 |
|---|---|
| `simulation_config.json`、`metrics.json` | 数据设定、软件版本、主指标和限制 |
| `metadata.csv`、`specimen_metadata.csv` | 扫描与物理标本的身份和用途 |
| `row_oof.csv`、`sample_oof.csv` | 各扫描折外预测及标本投票 |
| `split_audit.json` | 每折标本交集与类别计数 |
| `holdout_*_predictions.csv` | 冻结模型的A/B配对预测 |
| `preprocessing_panel.csv`、`panel_sample_predictions.csv` | 五个种子的所有流程结果及留出预测 |
| `permutation_scores.csv`、`extensions_summary.json` | 每次置换、处理对照汇总与规则 |
| `spectra.csv`、`spectra.npz` | 运行时生成的完整模拟光谱，未提交大矩阵 |
| `calibration.json` | 独立校准练习的分区及概率、阈值评价 |

`export_interactive.py`从以上文件生成`assets/js/ch04-results.js`。数值有变化时须重新运行导出，不要手改网页中的分数。交互结果为预计算数据，页面的分组计数和混淆矩阵汇总在浏览器执行。

## 阅读与交互

在仓库根目录运行`python -m http.server 8000`，访问`http://localhost:8000/#/docs/ch04`；也可直接用浏览器打开`assets/interactive/ch04.html`，保留相邻CSS和JS文件。网页没有外部接口、遥测或学生信息上传。

## 验收

`verify.py`独立复算CV和留出指标，核对分组隔离、配对标本、种子完整性、逐谱转换独立性，以及拟合/校准/阈值/测试四组互斥。`node code/ch04_exercises/raman/test_interactive.cjs`使用Node内置断言检查网页划分计数和全部面板混淆矩阵。另有可选的`test_interactive_browser.cjs`检查真实DOM交互，需要单独安装Playwright及其Chromium浏览器。脚本检查不能替代同学交叉评审，不能证明模拟的物理真实性。

## 实际实验扩展

先取得矿物身份参考、独立标本来源和配对仪器谱图，再固定预处理和验证方案。应记录波数轴、激光波长、分辨率、积分时间、日期及母岩/产地等元数据。18个留出标本不代表广泛外部有效性，更多重复扫描也不会增加独立化学覆盖。

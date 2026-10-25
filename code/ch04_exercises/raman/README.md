# G04 拉曼分类与泛化验证

[返回仓库使用说明](../../../README.md) · [成果与要求对照](../../../resources/annual/2026-2027/student-reports/ch04/README.md) · [第4章正文](../../../docs/ch04.md)

本练习支撑第4章机器学习的整章教学，核心问题是重复扫描如何影响验证，以及模型怎样应对新仪器。全部谱图为教学模拟，没有使用实测矿物数据或RRUFF谱图。运行无须GPU、API密钥或网络数据下载。

## 先选择要做的事

- **只读结果：** 打开[结果目录](outputs/)，或下载完整 `main` 分支并解压，双击 `assets/interactive/ch04.html`。不需要运行Python。
- **独立复现：** 按下面的环境安装和运行步骤执行，从模拟生成到结果核验完整跑一遍。
- **修改模型或参数：** 先理解“数据与实验规则”，记录修改；重新生成输出和网页数据，再运行检查。当前工作仅在个人仓库的任务分支进行。

请先确认下载或切换的是个人仓库的 `main` 分支。下列命令均在仓库根目录执行，也就是能同时看到 `README.md`、`docs`、`code` 和 `assets` 的文件夹。

## 一条命令完成复现

先按下一节创建Python 3.12虚拟环境并安装依赖，然后选择自己系统的命令：

```bash
# Linux / macOS
.venv-g04/bin/python code/ch04_exercises/raman/reproduce.py
```

```powershell
# Windows PowerShell
.\.venv-g04\Scripts\python.exe code/ch04_exercises/raman/reproduce.py
```

脚本按顺序执行主实验、199次随机标签置换与五种子扩展、独立校准、网页数据导出和核验，共5步。缺少依赖或版本不符时会停止并提示；不会自动安装软件。每步日志位于 `outputs/reproduction_logs/`，运行记录位于 `outputs/reproduction_record.json`。仅当5步全部成功，记录的 `status` 才是 `passed`；失败后先读对应日志。

默认命令会重新生成 `outputs/` 和网页数据。若要在独立目录复现，在上述命令末尾加 `--output code/ch04_exercises/raman/reproduced`。此时网页数据保存为该目录内的 `ch04-results.js`，不会修改网站使用的文件。脚本支持含中文或空格的目录；路径含空格时加引号。记录如何填写见[组内复现模板](../../../resources/annual/2026-2027/student-reports/ch04/collaboration.md)。

## 从干净环境运行

建议Python 3.12。依赖文件锁定本次实际运行的版本。首次安装需要访问PyPI，生成模拟谱与训练模型不需要下载外部数据。

下列分步命令与一条命令复现是两种运行方式，不必重复执行。

Linux / macOS：

```bash
python -m venv .venv-g04
.venv-g04/bin/python -m pip install -r code/ch04_exercises/raman/requirements.txt
.venv-g04/bin/python code/ch04_exercises/raman/exercise.py
.venv-g04/bin/python code/ch04_exercises/raman/extensions.py
.venv-g04/bin/python code/ch04_exercises/03_probability_calibration.py --output code/ch04_exercises/raman/outputs/calibration.json
.venv-g04/bin/python code/ch04_exercises/raman/export_interactive.py
.venv-g04/bin/python code/ch04_exercises/raman/verify.py
```

Windows PowerShell（已安装Python 3.12及其`py`启动器）：

```powershell
py -3.12 -m venv .venv-g04
.\.venv-g04\Scripts\python.exe -m pip install -r code/ch04_exercises/raman/requirements.txt
.\.venv-g04\Scripts\python.exe code/ch04_exercises/raman/exercise.py
.\.venv-g04\Scripts\python.exe code/ch04_exercises/raman/extensions.py
.\.venv-g04\Scripts\python.exe code/ch04_exercises/03_probability_calibration.py --output code/ch04_exercises/raman/outputs/calibration.json
.\.venv-g04\Scripts\python.exe code/ch04_exercises/raman/export_interactive.py
.\.venv-g04\Scripts\python.exe code/ch04_exercises/raman/verify.py
```

上述命令直接调用虚拟环境中的Python，无须先激活环境。若没有`py`启动器，可以在确认`python --version`显示3.12后，用`python -m venv .venv-g04`创建环境。完整执行通常为数分钟，取决于CPU和线性代数线程设置。

成功标志：当前版本的`verify.py`输出JSON，其中`passed`为83；主案例A/B标本宏F1约为0.8364/0.2081。具体结果解释见下文。建议独立复现者记录操作系统、Python版本、执行命令、输出数值和遇到的问题，作为组内核验材料。

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

`verify.py`独立复算CV和留出指标，核对分组隔离、配对标本、种子完整性、逐谱转换独立性，以及拟合/校准/阈值/测试四组互斥，并拒绝缺失的模型/种子组合、重复标本记录和未更新的网页数据。`node code/ch04_exercises/raman/test_interactive.cjs`使用Node内置断言检查网页划分计数和全部面板混淆矩阵。另有可选的`test_interactive_browser.cjs`检查真实DOM交互，需要单独安装Playwright及其Chromium浏览器。脚本检查不能替代同学交叉评审，不能证明模拟的物理真实性。

若修改了核验或导出逻辑，可运行 `python code/ch04_exercises/raman/test_verification.py`。这些回归测试在临时副本中故意删除一组预测、复制一条预测及改坏网页导出，确认核验会报错，不会改动仓库结果。

## 常见问题

- `No module named ...` 或依赖版本不符：用当前虚拟环境的Python执行 `-m pip install -r code/ch04_exercises/raman/requirements.txt`，避免安装到另一套Python。
- 找不到脚本：确认终端位于包含 `README.md`、`docs`、`code`、`assets` 的仓库根目录。
- 提示 `browser export matches Python results`：数值文件与网页导出不一致，重新执行完整复现，或对同一输出目录执行导出和核验。
- GitHub上HTML显示源代码：下载并解压完整目录，双击 `assets/interactive/ch04.html`。
- 数值与本仓库略有差异：先比较依赖、种子、参数和分区，保留日志；不要通过换种子挑出相同或更高的分数。

## 实际实验扩展

先取得矿物身份参考、独立标本来源和配对仪器谱图，再固定预处理和验证方案。应记录波数轴、激光波长、分辨率、积分时间、日期及母岩/产地等元数据。18个留出标本不代表广泛外部有效性，更多重复扫描也不会增加独立化学覆盖。

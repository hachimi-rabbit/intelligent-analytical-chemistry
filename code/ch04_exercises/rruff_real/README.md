# 实测拉曼谱：石英、方解石与石膏分类

这是G04的**真实数据主案例**：从公开存档取得实测拉曼谱，保留来源及标本身份，训练四个固定基线，检查对未见RRUFF标本的预测。没有新做湿实验，也没有用生成谱冒充实测谱。原来的[模拟实验](../raman/README.md)继续用于演示泄漏与受控仪器变化。

## 数据从哪里来

使用 Li、Schmidt、Alstrøm 发布于丹麦技术大学（DTU）的[论文配套数据，v1](https://doi.org/10.11583/DTU.20222331.v1)，许可为[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。该存档收录历史RRUFF衍生数据。本次取 `mineral_preprocess` 中由来源方处理过的实测谱，并非原始探测器信号或当前RRUFF完整导出。归属与改动见 [ATTRIBUTION.md](ATTRIBUTION.md)。

下载的 `public_dataset.zip` 为135,377,870字节，SHA-256为 `90f029cda4380f74d7f51b0295532e68cf196b1de8afa3c6a9dd225f9bad398f`。原压缩包不入库，仓库附带可离线复现的三类子集。选择条件为：按作者代码先筛选元数据 `raw == 0` 并重置索引，确认与5228条谱一一对应，再保留全部Quartz、Calcite、Gypsum记录。没有按模型得分筛选谱图。

| 矿物 | 光谱条数 | 不同RRUFF ID数 |
|---|---:|---:|
| 石英 Quartz | 21 | 10 |
| 方解石 Calcite | 26 | 10 |
| 石膏 Gypsum | 5 | 2 |
| 合计 | 52 | 22 |

`data/manifest.csv`逐条记录标本、矿物、激光波长、来源文件及索引、RRUFF链接、点数和数值校验和。`data/measured_processed_spectra.npz`保存来源存档中的完整波数—强度对，不含插值补造的新观察。`data/provenance.json`保存数据版本、归属、筛选规则和限制。NPZ可用 `np.load(path, allow_pickle=False)` 读取；键名为 `s` 加 `spectrum_id`。

## 一条命令复现

在仓库根目录，用Python 3.12新建虚拟环境，安装锁定依赖：

```bash
python -m venv .venv
# Windows：.venv\Scripts\activate
# macOS/Linux：source .venv/bin/activate
python -m pip install -r code/ch04_exercises/raman/requirements.txt
python code/ch04_exercises/rruff_real/reproduce.py
```

最后一条命令会重新训练并执行结果核验，默认无需联网。为保留仓库基准，可使用：

```bash
python code/ch04_exercises/rruff_real/reproduce.py --output code/ch04_exercises/rruff_real/reproduced
python code/ch04_exercises/rruff_real/test_integrity.py
```

需要重新获取来源压缩包时运行 `reproduce.py --redownload`，约下载135MB，校验SHA-256后才解析。原格式含NumPy pickle对象，下载脚本仅允许数值数组所需的三个类型，不允许任意对象反序列化。也可用 `prepare_data.py --archive /path/to/public_dataset.zip` 从已下载存档重新提取。网络不可用时仍可运行已附带的子集。

## 固定实验方案

1. 每条谱独立插值到200–1200 cm⁻¹，步长2 cm⁻¹，共501变量。所有谱覆盖此区间，禁止外推。建模和展示使用L2归一化。
2. 按RRUFF ID做留一标本验证，共22折。每折将一个ID的所有谱放在验证侧，另21个ID训练。重复谱不会跨两侧。
3. 四个模型在首次评估前固定：多数类Dummy；余弦距离1近邻；L2＋训练折标准化＋PCA(8)＋逻辑回归(C=1)；L2＋RBF-SVC(C=10, gamma=scale)。PCA及所有跨样本变换在训练折内拟合。未用增强数据。
4. 汇总全部折外预测，再算宏F1和平衡准确率。主结果按标本多数投票，每个ID权重相同；同票时按Quartz、Calcite、Gypsum顺序取先者。另报告逐谱指标。没有对只含一类的单个验证折计算宏F1后取平均。
5. 全部候选均报告，不根据这轮分数选择“最佳模型”。本次没有独立外部测试集；后续若据此调参，须引入新的留出数据或嵌套分组验证。

## 实际结果与解释

| 固定模型 | 标本级宏F1 | 标本级平衡准确率 | 正确标本数 |
|---|---:|---:|---:|
| Dummy | 0.2083 | 0.3333 | 10/22 |
| Cosine_1NN | 1.0000 | 1.0000 | 22/22 |
| PCA8_LR | 1.0000 | 1.0000 | 22/22 |
| RBF_SVC | 1.0000 | 1.0000 | 22/22 |

三个非平凡模型的逐谱预测也为52/52正确。结果表明当前已处理、三类小子集容易区分，尚不能证明复杂模型优于简单谱匹配，更不能推断真实部署达到100%。

![三类来源方已处理的实测谱](outputs/measured_spectra.svg)

![22个标本的折外混淆矩阵](outputs/confusion_matrices.svg)

**必须随结果一起报告的限制：** 石膏只有2个标本，留出其中一个时仅剩另一个供训练；RRUFF ID尚未解析母岩或共同产地依赖；来源方的处理早于本项目，不能把它当作本项目完成的原始信号预处理验证；激光波长不等于仪器身份。本数据没有确认配对双仪器测试，也不能验证旧模拟中的arPLS增益。这里做的是按ID隔离的数据库内验证。

## 查看结果、核对与交接

下载完整仓库后双击 [`assets/interactive/ch04-real.html`](../../../assets/interactive/ch04-real.html)，可离线选择52条实测谱，查看标本、波长、折外预测及四个模型的混淆矩阵。页面读取Python生成的结果，不现场训练。旧[模拟交互](../../../assets/interactive/ch04.html)单独保留。

- `outputs/protocol.json`：固定参数与评价规则。
- `outputs/folds.json`：逐折训练/验证标本名单。
- `outputs/row_predictions.csv` / `specimen_predictions.csv`：逐谱及逐标本的全部折外预测。
- `outputs/metrics.json`：指标、版本、类别顺序及限制。
- `verify.py`：校验身份、数值哈希、折隔离，独立重算投票和指标，检查网页数据一致性。
- `test_integrity.py`：5项检查，包括重复谱身份、哈希被修改、错误折号及陈旧网页数据会被拒绝。

组员仍需在自己的电脑独立复现并记录实际输出，核读来源和方法，练习解释高分的边界。自动运行不代表全组已完成实验理解或课堂汇报。

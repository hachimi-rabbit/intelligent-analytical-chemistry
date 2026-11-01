"""Build the G04 full-RRUFF report deck from this module's data and outputs, on the G04 slide master.

Run from the repository root (needs python-pptx, matplotlib, and Google Chrome for the demo screenshot):
    python code/ch04_exercises/rruff_full/build_report.py
Writes resources/annual/2026-2027/student-reports/ch04/G04-Raman-Full-Report-new.pptx
"""
import json
import subprocess
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPORTS = ROOT / 'resources/annual/2026-2027/student-reports/ch04'
TEMPLATE = REPORTS / 'G04-Raman-Real-Report.pptx'
OUT = REPORTS / 'G04-Raman-Full-Report-new.pptx'
FONT_FILE = ROOT / '.ppt-build/fonts/NotoSansCJKsc-Regular.otf'
CHROME = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
FONT = 'Noto Sans CJK SC'
FOOTER = 'G04 · 人工智能化学分析 · 第 4 章 机器学习'
HEX = dict(green='1E5B3F', mid='4C8C6A', pale='EEF3EF', ink='1F2A30', grey='6B7378', rule='C9D6CD',
           blue='2F6690', ochre='B8642A', light='A9B4AE')
C = {k: RGBColor.from_string(v) for k, v in HEX.items()}
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MODELS = {'Dummy': '多数类基线', 'Cosine_1NN': '余弦 1-NN', 'PCA8_LR': 'PCA + 逻辑回归', 'RBF_SVC': 'RBF-SVM'}
# Mineralogical relation of the most frequent cosine-1NN confusions shown in the error table.
RELATIONS = {
    ('Amblygonite', 'Montebrasite'): ('锂磷铝石 → 羟磷锂铝石', 'F–OH 固溶体'),
    ('Pyrope', 'Almandine'): ('镁铝榴石 → 铁铝榴石', '石榴子石族'),
    ('Grossular', 'Andradite'): ('钙铝榴石 → 钙铁榴石', '石榴子石族'),
    ('Tremolite', 'Actinolite'): ('透闪石 → 阳起石', '角闪石族，Mg–Fe'),
    ('Richterite', 'Fluororichterite'): ('钠透闪石 → 氟钠透闪石', '角闪石族，OH–F'),
    ('Fluoruvite', 'Dravite'): ('氟钙镁电气石 → 镁电气石', '电气石族'),
    ('Manganite', 'Groutite'): ('水锰矿 → 斜方水锰矿', 'MnOOH 同质多象'),
}
REFERENCES = [
    'Lafuente, B.; Downs, R. T.; Yang, H.; Stone, N. The power of databases: the RRUFF project. In Highlights in Mineralogical Crystallography, pp. 1–30 (2015). doi:10.1515/9783110417104-003',
    'Li, B.; Schmidt, M. N.; Alstrøm, T. S. Datasets for replicating the paper "Raman Spectrum Matching with Contrastive Representation Learning". Technical University of Denmark, v1 (2022), CC BY 4.0. doi:10.11583/DTU.20222331.v1',
    'Pedregosa, F.; Varoquaux, G.; Gramfort, A.; et al. Scikit-learn: Machine learning in Python. J. Mach. Learn. Res. 12, 2825–2830 (2011).',
    'Wilson, E. B. Probable inference, the law of succession, and statistical inference. J. Am. Stat. Assoc. 22, 209–212 (1927). doi:10.1080/01621459.1927.10502953',
    'Kapoor, S.; Narayanan, A. Leakage and the reproducibility crisis in machine-learning-based science. Patterns 4, 100804 (2023). doi:10.1016/j.patter.2023.100804',
    'Kapoor, S.; Cantrell, E. M.; Peng, K.; et al. REFORMS: Consensus-based recommendations for machine-learning-based science. Sci. Adv. 10, eadk3452 (2024). doi:10.1126/sciadv.adk3452',
    'Lilek, D.; Zimmermann, D.; Steininger, L.; et al. Machine learning of Raman spectroscopic data: Comparison of different validation strategies. J. Raman Spectrosc. 56, 867–877 (2025). doi:10.1002/jrs.6842',
    'Hollmann, N.; Müller, S.; Purucker, L.; et al. Accurate predictions on small data with a tabular foundation model. Nature 637, 319–326 (2025). doi:10.1038/s41586-024-08328-6',
]

# ---------------------------------------------------------------- data
metrics = json.loads((HERE / 'outputs/metrics.json').read_text())
M = metrics['metrics']
manifest = pd.read_csv(HERE / 'data/manifest.csv', dtype={'spectrum_id': str})
usable = manifest[manifest.status.eq('usable')].reset_index(drop=True)
with np.load(HERE / 'data/features.npz', allow_pickle=False) as z:
    X, axis = z['X'], z['axis']
groups = pd.read_csv(HERE / 'outputs/group_predictions.csv')
folds = pd.read_csv(HERE / 'outputs/group_folds.csv')
groups['ok'] = groups.true_mineral.eq(groups.predicted_mineral)
per_class = folds.groupby('mineral').validation_group.nunique()
single = set(per_class[per_class.eq(1)].index)
groups['support'] = groups.true_mineral.map(per_class).clip(upper=6)
fold_acc = groups.groupby(['model', 'fold']).ok.mean().unstack()
support = groups.groupby(['model', 'support']).ok.agg(['sum', 'count'])
hist = per_class.clip(upper=5).value_counts().sort_index()
cos = groups[groups.model.eq('Cosine_1NN')]
cos_err = cos[~cos.ok]
to_single = int(cos_err.predicted_mineral.isin(single).sum())
pairs = cos_err.groupby(['true_mineral', 'predicted_mineral']).size().sort_values(ascending=False)
svm = groups[groups.model.eq('RBF_SVC')].set_index('validation_group')
agree = float(cos.set_index('validation_group').predicted_mineral.eq(svm.predicted_mineral).mean())
spread = {m: (fold_acc.loc[m].min(), fold_acc.loc[m].max()) for m in MODELS}
excluded = {k: metrics[f'source_{k}'] - metrics[f'usable_{k}'] for k in ('spectra', 'specimens', 'classes')}
assert usable.axis_min.max() <= axis[0] and usable.axis_max.min() >= axis[-1]


def acc(model):
    return M[model]['group']['accuracy']


def pct(x, d=1):
    return f'{100 * x:.{d}f}%'


def wilson(k, n, z=1.96):
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def demo_facts():
    """What the two demo pages display for the clicks scripted on the demo slide; fails if the pages' data changed."""
    page = json.loads((HERE / 'outputs/browser-data.js').read_text().split('=', 1)[1].rstrip().rstrip(';'))
    names = page['classes']
    quartz = [r for r in page['spectra'] if r['mineral'] == 'Quartz']
    first = [r for r in quartz if r['specimen'] == quartz[0]['specimen']]
    cosine = [names[r['predictions']['Cosine_1NN']] for r in first]
    dummy = {names[r['predictions']['Dummy']] for r in quartz}
    abelsonite = [r for r in page['spectra'] if r['mineral'] == 'Abelsonite']
    sim = json.loads((ROOT / 'assets/js/ch04-results.js').read_text().split('var data=', 1)[1].split('; if(typeof', 1)[0])
    shared = {split: sum(len({x == 1 for x in r['folds']}) > 1 for r in sim['folds'][split]) for split in ('row_random', 'specimen_group')}
    assert names[0] == 'Abelsonite' and len(abelsonite) == 1 and abelsonite[0]['fold'] < 0
    assert [r['laser'] for r in first] == [514, 532, 780] and cosine == ['Sodalite', 'Quartz', 'Quartz'] and first[0]['fold'] == 0
    assert dummy == {'Grossular'} and shared == {'row_random': 44, 'specimen_group': 0}
    return first[0]['specimen']


QUARTZ_SPECIMEN = demo_facts()

# ---------------------------------------------------------------- figures
if not FONT_FILE.exists():
    raise FileNotFoundError(f'CJK font for figures not found: {FONT_FILE}')
font_manager.fontManager.addfont(str(FONT_FILE))
plt.rcParams.update({'font.family': font_manager.FontProperties(fname=FONT_FILE).get_name(), 'font.size': 13,
                     'axes.edgecolor': '#6B7378', 'axes.labelcolor': '#1F2A30', 'xtick.color': '#1F2A30',
                     'ytick.color': '#1F2A30', 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.unicode_minus': False, 'savefig.dpi': 220})
H = {k: '#' + v for k, v in HEX.items()}
FIG = Path(tempfile.mkdtemp(prefix='g04-figures-'))
WAVENUMBER = '拉曼位移 / cm$^{-1}$'


def save(fig, name):
    path = FIG / f'{name}.png'
    fig.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return path


def spectrum(mineral, laser=532):
    rows = usable.index[usable.mineral.eq(mineral) & usable.laser_nm.eq(laser)]
    return X[rows[0]]


def fig_examples():
    fig, ax = plt.subplots(figsize=(6.0, 4.4))
    for i, (name, label, color, x, ha) in enumerate([('Gypsum', '石膏 Gypsum', H['ochre'], axis[-1] - 4, 'right'),
                                                      ('Calcite', '方解石 Calcite', H['blue'], axis[0] + 8, 'left'),
                                                      ('Quartz', '石英 Quartz', H['green'], axis[-1] - 4, 'right')]):
        y = spectrum(name)
        ax.plot(axis, y / y.max() + 1.15 * i, color=color, lw=1.6)
        ax.text(x, 1.15 * i + 0.32, label, ha=ha, color=color)
    ax.set(xlabel=WAVENUMBER, ylabel='归一化强度（纵向平移）', xlim=(axis[0], axis[-1]), yticks=[])
    return save(fig, 'examples')


def fig_support_hist():
    fig, ax = plt.subplots(figsize=(6.2, 4.3))
    labels = ['1', '2', '3', '4', '≥5']
    bars = ax.bar(labels, hist.values, color=[H['light']] + [H['green']] * 4, width=0.65)
    ax.bar_label(bars, padding=3)
    ax.set(xlabel='每种矿物的独立标本（验证组）数', ylabel='矿物种数', ylim=(0, hist.max() * 1.15))
    ax.text(0.33, hist.iloc[0] * 0.92, '仅作参考库', color=H['grey'], ha='left')
    return save(fig, 'support_hist')


def fig_coverage():
    fig, ax = plt.subplots(figsize=(6.2, 4.3))
    grid = np.arange(0, 4301, 2.0)
    lo, hi = usable.axis_min.to_numpy()[:, None], usable.axis_max.to_numpy()[:, None]
    covered = ((lo <= grid) & (hi >= grid)).mean(axis=0)
    ax.axvspan(axis[0], axis[-1], color=H['ochre'], alpha=0.2, lw=0)
    ax.plot(grid, covered, color=H['blue'], lw=2)
    ax.text((axis[0] + axis[-1]) / 2, 1.04, f'{axis[0]:.0f}–{axis[-1]:.0f} cm$^{{-1}}$\n100% 覆盖', ha='center', va='bottom', color=H['ochre'])
    ax.set(xlabel=WAVENUMBER, ylabel='覆盖该位移的光谱比例', xlim=(0, 4300), ylim=(0, 1.25))
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    return save(fig, 'coverage')


def fig_accuracy():
    fig, ax = plt.subplots(figsize=(6.3, 4.4))
    xs = np.arange(len(MODELS))
    colors = [H['light'], H['blue'], H['light'], H['ochre']]
    bars = ax.bar(xs, [acc(m) for m in MODELS], color=colors, width=0.6, alpha=0.9)
    for x, m in zip(xs, MODELS):
        f = fold_acc.loc[m].to_numpy()
        ax.scatter(x + np.linspace(-0.16, 0.16, len(f)), f, s=22, color=H['ink'], zorder=3)
    for x, m in zip(xs, MODELS):
        ax.text(x, max(acc(m), fold_acc.loc[m].max()) + 0.03, pct(acc(m)), ha='center', va='bottom')
    ax.set(xticks=xs, xticklabels=list(MODELS.values()), ylabel='组级正确率', ylim=(0, 1))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    return save(fig, 'accuracy')


def fig_support_curve():
    fig, ax = plt.subplots(figsize=(6.6, 4.5))
    ks = sorted(support.loc['Cosine_1NN'].index)
    for model, color, dx in [('Cosine_1NN', H['blue'], -0.07), ('RBF_SVC', H['ochre'], 0.07)]:
        s = support.loc[model]
        p = (s['sum'] / s['count']).to_numpy()
        lo, hi = np.array([wilson(k, n) for k, n in zip(s['sum'], s['count'])]).T
        ax.errorbar(np.arange(len(ks)) + dx, p, yerr=[p - lo, hi - p], color=color, marker='o', ms=6, lw=2,
                    capsize=4, label=MODELS[model])
    n = support.loc['Cosine_1NN', 'count'].to_numpy()
    ax.set_xticks(range(len(ks)), [f'{k if k < 6 else "≥6"}\n(n={c})' for k, c in zip(ks, n)])
    ax.set(xlabel='该矿物的独立标本数（n 为验证组数）', ylabel='组级正确率', ylim=(0.4, 1.0))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.legend(frameon=False, loc='lower right')
    return save(fig, 'support_curve')


def fig_confused():
    fig, axes = plt.subplots(2, 1, figsize=(6.0, 4.3), sharex=True, gridspec_kw={'hspace': 0.35})
    for ax, (a, b) in zip(axes, [('Amblygonite', 'Montebrasite'), ('Pyrope', 'Almandine')]):
        name_a, name_b = RELATIONS[a, b][0].split(' → ')
        for mineral, label, color, style in [(a, name_a, H['blue'], '-'), (b, name_b, H['ochre'], '--')]:
            mean = X[usable.mineral.eq(mineral).to_numpy()].mean(axis=0)
            ax.plot(axis, mean / mean.max(), color=color, ls=style, lw=1.6, label=f'{label} {mineral}')
        ax.set(yticks=[], ylabel='平均强度')
        ax.legend(frameon=False, fontsize=11, loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2, borderaxespad=0.1, handlelength=1.6)
    axes[-1].set(xlabel=WAVENUMBER, xlim=(axis[0], axis[-1]))
    return save(fig, 'confused')


def fig_error_targets():
    fig, ax = plt.subplots(figsize=(5.9, 1.55))
    parts = [(to_single, '判为单标本矿物', H['ochre']), (len(cos_err) - to_single, '判为其他可验证矿物', H['light'])]
    left = 0
    for n, label, color in parts:
        ax.barh(0, n, left=left, color=color, height=0.55)
        ax.text(left + n / 2, 0, f'{label}\n{n}（{n / len(cos_err):.0%}）', ha='center', va='center', fontsize=12)
        left += n
    ax.set(xlim=(0, len(cos_err)), yticks=[], xlabel=f'余弦 1-NN 的错误验证组（共 {len(cos_err)} 个）')
    ax.spines['left'].set_visible(False)
    return save(fig, 'error_targets')


def demo_screenshot():
    if not CHROME.exists():
        raise FileNotFoundError(f'Google Chrome is required for the demo screenshot: {CHROME}')
    shot = FIG / 'demo_full.png'
    subprocess.run([str(CHROME), '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--user-data-dir={FIG / "chrome"}',
                    '--window-size=1200,1500', f'--screenshot={shot}', (ROOT / 'assets/interactive/ch04-full.html').as_uri()],
                   check=True, capture_output=True, timeout=120)
    path = FIG / 'demo.png'
    Image.open(shot).crop((64, 330, 1136, 1090)).save(path)
    return path


FIGURES = {f.__name__[4:]: f() for f in (fig_examples, fig_support_hist, fig_coverage, fig_accuracy, fig_support_curve, fig_confused, fig_error_targets)}
DEMO = demo_screenshot()

# ---------------------------------------------------------------- slide helpers
prs = Presentation(TEMPLATE)
ids = prs.slides._sldIdLst
for sld in list(ids):
    prs.part.drop_rel(sld.rId)
    ids.remove(sld)
BLANK = next(l for l in prs.slide_layouts if l.name == 'Blank')
figure_no = 0


def set_typeface(rpr):
    for tag in ('a:latin', 'a:ea', 'a:cs'):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set('typeface', FONT)


def style(run, size, color=C['ink'], bold=False):
    run.font.size, run.font.bold, run.font.color.rgb = Pt(size), bold, color
    set_typeface(run._r.get_or_add_rPr())


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT, space=6, bullet=False):
    """paras: (text, size, color, bold) per paragraph, or a list of such runs for one paragraph."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap, tf.vertical_anchor = True, anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment, p.space_after = align, Pt(space)
        runs = para if isinstance(para, list) else [para]
        if bullet and runs[0][0]:
            pPr = p._p.get_or_add_pPr()
            pPr.set('marL', str(Inches(0.24)))
            pPr.set('indent', str(-Inches(0.24)))
            bu = pPr.makeelement(qn('a:buChar'), {'char': '•'})
            pPr.append(bu)
        for t, size, color, bold in runs:
            r = p.add_run()
            r.text = t
            style(r, size, color, bold)
    return box


def bullets(slide, x, y, w, h, items, size=17, space=10):
    return text(slide, x, y, w, h, [(t, size, C['ink'], False) if isinstance(t, str) else t for t in items], space=space, bullet=True)


def rect(slide, x, y, w, h, color, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = color
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb, s.line.width = line, Pt(1)
    s.shadow.inherit = False
    return s


def hline(slide, x, y, w, color, weight=1.25):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(y), Inches(x + w), Inches(y))
    ln.line.color.rgb, ln.line.width = color, Pt(weight)


def new_slide(section, title, notes):
    slide = prs.slides.add_slide(BLANK)
    text(slide, 0.6, 0.32, 9.0, 0.3, [(section, 13, C['mid'], True)])
    text(slide, 0.6, 0.6, 12.1, 0.7, [(title, 28, C['green'], True)], anchor=MSO_ANCHOR.MIDDLE)
    hline(slide, 0.6, 1.38, 12.13, C['rule'])
    hline(slide, 0.6, 7.0, 12.13, C['rule'], 0.75)
    text(slide, 0.6, 7.08, 10.0, 0.26, [(FOOTER, 11, C['grey'], False)])
    text(slide, 11.73, 7.08, 1.0, 0.26, [(str(len(prs.slides)), 11, C['grey'], False)], align=PP_ALIGN.RIGHT)
    slide.notes_slide.notes_text_frame.text = notes
    return slide


def figure(slide, path, x, y, w, caption):
    global figure_no
    figure_no += 1
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w))
    bottom = y + pic.height / 914400
    text(slide, x, bottom + 0.08, w, 0.5, [(f'图 {figure_no}  {caption}', 12, C['grey'], False)])
    return figure_no


def table(slide, x, y, col_w, rows, row_h=0.44, size=14, align=None):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y),
                                   Inches(sum(col_w)), Inches(row_h * len(rows)))
    tb = shape.table
    for j, cw in enumerate(col_w):
        tb.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        tb.rows[i].height = Inches(row_h)
        for j, value in enumerate(row):
            cell = tb.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = C['green'] if i == 0 else (C['pale'] if i % 2 == 0 else WHITE)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            p = cell.text_frame.paragraphs[0]
            p.alignment = (align or [PP_ALIGN.LEFT] * len(row))[j]
            r = p.add_run()
            r.text = value
            style(r, size, WHITE if i == 0 else C['ink'], i == 0)
    return tb


SECTIONS = ['研究背景与问题', '数据与预处理', '验证设计与方法', '结果', '误差分析与讨论', '结论与展望']


def sec(i):
    return f'{i:02d}  {SECTIONS[i - 1]}'


R = PP_ALIGN.RIGHT
L = PP_ALIGN.LEFT

# ---------------------------------------------------------------- 1 cover
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, 13.333, 4.55, C['green'])
text(s, 0.9, 1.0, 11.5, 0.4, [('人工智能化学分析 · 第 4 章 机器学习 · 小组汇报', 16, RGBColor(0xD5, 0xE4, 0xD9), False)])
text(s, 0.9, 1.95, 11.5, 1.9, [('全量 RRUFF 实测拉曼光谱的矿物分类', 38, WHITE, True),
                              ('基于按标本分组五折验证的方法比较', 24, RGBColor(0xD5, 0xE4, 0xD9), False)], space=14)
text(s, 0.9, 5.05, 11.5, 1.6, [('G04 组', 20, C['green'], True),
                              ('汇报人：________________', 18, C['ink'], False),
                              ('2026–2027 学年', 16, C['grey'], False)], space=10)
s.notes_slide.notes_text_frame.text = (
    '【本讲稿逐字照念；方括号内为动作提示，不要念出来。全程约 12 分钟。】\n'
    '各位老师、同学好，我们是 G04 组。我们汇报的题目是：全量 RRUFF 实测拉曼光谱的矿物分类，'
    '重点是基于按标本分组的五折验证，对几种方法进行比较。【翻页】')

# ---------------------------------------------------------------- 2 contents
s = new_slide('', '目录', '汇报分为六个部分：研究背景与问题、数据与预处理、验证设计与方法、结果、误差分析与讨论，最后是结论与展望。【翻页】')
for i, name in enumerate(SECTIONS):
    col, row = divmod(i, 3)
    x, y = 0.9 + col * 6.1, 1.95 + row * 1.5
    rect(s, x, y, 0.95, 0.95, C['green'])
    text(s, x, y, 0.95, 0.95, [(f'{i + 1:02d}', 26, WHITE, True)], anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
    text(s, x + 1.25, y, 4.6, 0.95, [(name, 24, C['ink'], False)], anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 3 background
s = new_slide(sec(1), '研究背景与问题',
    '首先是研究背景。拉曼光谱反映分子和晶格的振动，不同矿物的峰位和峰形不同，因此可以作为矿物的“指纹”。\n'
    '【指向图 1】图 1 是石英、方解石和石膏在本研究所用波段内的代表性光谱，三者的特征峰位置明显不同。\n'
    '【指向左侧文字】我们使用的数据来自 RRUFF 数据库，它的特点是每条光谱都对应一个有编号的实物标本。\n'
    '在前期的三类案例中，我们只用了 52 条谱、22 个标本，三种方法的正确率都是百分之百，无法比较方法的优劣。\n'
    '因此，本研究的问题是：当类别扩展到整个数据库时，模型能否识别训练中没有出现过的标本。【翻页】')
bullets(s, 0.6, 1.75, 5.7, 4.0, [
    '拉曼光谱反映分子与晶格振动，峰位和峰形可作为矿物“指纹”',
    'RRUFF 数据库：每条光谱对应一个有编号的实物标本 [1]',
    '前期三类案例（52 条谱、22 个标本）：三种方法正确率均为 100%，无法区分方法'])
rect(s, 0.6, 5.0, 5.7, 1.55, C['pale'])
text(s, 0.85, 5.12, 5.25, 1.35, [('研究问题', 17, C['green'], True),
                               ('类别扩展至全库后，模型能否识别训练中未出现的标本？', 17, C['ink'], False)], space=6)
figure(s, FIGURES['examples'], 6.75, 1.6, 5.95, '三种矿物的代表性拉曼光谱（532 nm 激发，304–852 cm⁻¹）')

# ---------------------------------------------------------------- 4 data
s = new_slide(sec(2), '数据来源与质量审查',
    f'第二部分是数据。【指向表格】DTU 存档中共有 {metrics["source_spectra"]:,} 条谱，来自 {metrics["source_specimens"]:,} 个标本、'
    f'{metrics["source_classes"]:,} 种矿物。我们逐条审查后，隔离了 {metrics["excluded_spectra"]} 条标签冲突的记录，'
    f'例如同一标本编号对应两个矿物名。剩下 {metrics["usable_spectra"]:,} 条谱、{metrics["usable_classes"]:,} 种矿物用于训练。\n'
    f'【指向图 2】图 2 是每种矿物拥有的独立标本数。灰色柱表示只有一个标本的矿物，共 {hist.iloc[0]:,} 种。'
    '这些矿物无法检验“识别新标本”的能力，所以只放在参考库中，不参与评分。\n'
    f'【指向表格最后两行】真正可以验证的是 {metrics["evaluated_classes"]} 种矿物、{metrics["evaluated_groups"]:,} 个验证组。【翻页】')
table(s, 0.6, 1.75, [2.3, 1.1, 1.1, 1.1], [
    ['', '光谱', '标本', '矿物种类'],
    ['来源存档 [2]', f'{metrics["source_spectra"]:,}', f'{metrics["source_specimens"]:,}', f'{metrics["source_classes"]:,}'],
    ['隔离（标签冲突）', f'{excluded["spectra"]}', f'{excluded["specimens"]}', f'{excluded["classes"]}'],
    ['用于训练', f'{metrics["usable_spectra"]:,}', f'{metrics["usable_specimens"]:,}', f'{metrics["usable_classes"]:,}'],
    ['可验证（≥2 个标本）', f'{metrics["evaluated_spectra"]:,}', f'{metrics["evaluated_specimens"]:,}', f'{metrics["evaluated_classes"]}'],
    ['仅作参考库', f'{metrics["training_only_spectra"]:,}', f'{metrics["usable_specimens"] - metrics["evaluated_specimens"]:,}', f'{metrics["training_only_classes"]:,}'],
], row_h=0.5, size=15, align=[L, R, R, R])
text(s, 0.6, 4.95, 5.6, 1.6, [
    (f'可验证部分共 {metrics["evaluated_groups"]:,} 个验证组；相同输入的跨标本谱合并为一组。', 14, C['grey'], False),
    ('数据：DTU 存档 v1（CC BY 4.0），原始来源 RRUFF [1, 2]。', 14, C['grey'], False)], space=6)
figure(s, FIGURES['support_hist'], 6.65, 1.6, 6.05, '每种矿物拥有的独立标本数（共 1,669 种）')

# ---------------------------------------------------------------- 5 preprocessing
s = new_slide(sec(2), '光谱预处理',
    '接下来是预处理。【指向图 3】图 3 的横轴是拉曼位移，纵轴是覆盖这一位移的光谱比例。不同光谱的测量范围差别很大，只有中间一段被全部光谱覆盖。'
    f'为了不外推、不补造数据，我们只取所有光谱共同覆盖的 {axis[0]:.0f} 到 {axis[-1]:.0f} 波数这一段，也就是阴影部分。\n'
    f'【指向右侧文字】在这个区间内，我们按 2 个波数的间隔线性插值，得到 {len(axis)} 个变量，再对每条光谱做 L2 归一化。'
    '代价是区间以外的峰没有被利用，例如方解石在 1086 波数附近的主峰。【翻页】')
figure(s, FIGURES['coverage'], 0.6, 1.6, 6.3, f'{metrics["usable_spectra"]:,} 条可用光谱对各拉曼位移的覆盖比例；阴影为共同覆盖区间')
lasers = usable.laser_nm.value_counts()
bullets(s, 7.35, 1.8, 5.35, 4.8, [
    [('共同覆盖区间：', 17, C['green'], True), (f'{axis[0]:.0f}–{axis[-1]:.0f} cm⁻¹，所有光谱均完整覆盖，不外推', 17, C['ink'], False)],
    [('插值：', 17, C['green'], True), (f'2 cm⁻¹ 间隔线性插值，共 {len(axis)} 个变量', 17, C['ink'], False)],
    [('归一化：', 17, C['green'], True), ('逐谱 L2 归一化', 17, C['ink'], False)],
    [('激发波长：', 17, C['green'], True), (' / '.join(f'{k:.0f}' for k in lasers.index) + ' nm（' + ' / '.join(f'{v:,}' for v in lasers.values) + ' 条）', 17, C['ink'], False)],
    [('代价：', 17, C['ochre'], True), ('区间外的峰不参与分类，如方解石约 1086 cm⁻¹ 的主峰', 17, C['ink'], False)]], space=12)

# ---------------------------------------------------------------- 6 validation
s = new_slide(sec(3), '按标本分组的五折验证',
    '第三部分是验证设计，这是本研究的核心。【指向上方五个方框】我们把同一个标本的全部光谱作为一个验证组，整组只能出现在训练侧或验证侧，不会拆开。'
    '如果两个不同编号的标本光谱完全相同，也合并为一组。\n'
    '验证组按类别均衡地分配到五个折中，每一轮留出一折作为验证，其余四折用于训练。被留出的矿物，在训练侧都还有同种矿物的其他标本。\n'
    f'【指向下方灰色长条】只有一个标本的 {metrics["training_only_classes"]:,} 种矿物，每一轮都只在训练侧。\n'
    '【指向右侧文字】另外，标准化和主成分分析都只在训练折内拟合；每个验证组内的光谱多数投票，得到一个预测；'
    '所有超参数事先固定，没有根据验证结果调整。这样做是为了避免数据泄漏 [5]。【翻页】')
text(s, 0.6, 1.7, 6.6, 0.4, [('第 1 轮（共 5 轮，各折轮流作为验证集）', 15, C['grey'], False)])
for i in range(5):
    x = 0.6 + i * 1.33
    rect(s, x, 2.15, 1.2, 1.05, C['ochre'] if i == 0 else C['green'])
    text(s, x, 2.15, 1.2, 1.05, [(f'第 {i + 1} 折', 16, WHITE, True), ('验证' if i == 0 else '训练', 14, WHITE, False)],
         anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, space=2)
rect(s, 0.6, 3.4, 6.53, 0.7, C['pale'], line=C['rule'])
text(s, 0.8, 3.4, 6.2, 0.7, [(f'参考库：{metrics["training_only_classes"]:,} 种单标本矿物，每轮均只在训练侧', 15, C['ink'], False)],
     anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.6, 4.4, 6.6, 2.3, [
    ('验证组', 16, C['green'], True),
    ('同一标本的全部光谱 = 1 个验证组；输入完全相同的跨标本光谱合并为同组', 15, C['ink'], False),
    ('分配', 16, C['green'], True),
    ('各类别的验证组均衡分配到 5 折；留出时训练侧仍有同类其他标本', 15, C['ink'], False)], space=5)
rect(s, 7.6, 1.7, 5.13, 4.0, C['pale'])
text(s, 7.85, 1.9, 4.7, 0.4, [('防止泄漏的约束 [5]', 17, C['green'], True)])
bullets(s, 7.85, 2.45, 4.7, 4.1, [
    '标准化、PCA 仅在训练折内拟合',
    '组内光谱多数投票，得到一个预测；平票取字母序靠前者',
    '每个验证组等权计分',
    '超参数预先固定，不依据验证结果调整',
    '最终模型用全部可用光谱重新拟合，其训练分数不作为性能'], size=15, space=10)

# ---------------------------------------------------------------- 7 methods
s = new_slide(sec(3), '对比方法与评价指标',
    '我们比较了四种方法。【指向表格】多数类基线不使用光谱，总是预测训练集中最常见的矿物，用来给出性能下限。'
    '余弦一近邻，寻找与待测光谱余弦距离最小的训练光谱，沿用它的标签。PCA 加逻辑回归，先降到 8 个主成分，再做逻辑回归。'
    'RBF 核支持向量机，惩罚系数 C 取 10。所有方法都用 scikit-learn 实现 [3]。\n'
    f'【指向下方】评价指标有三个：组级正确率；宏平均 F1，也就是 {metrics["evaluated_classes"]} 个类别等权平均；以及平衡准确率。【翻页】')
table(s, 0.6, 1.75, [2.6, 4.7, 4.83], [
    ['方法', '处理流程', '固定参数'],
    ['多数类基线', '不使用光谱', '预测训练集中最常见的类别'],
    ['余弦 1-NN', 'L2 归一化 → 最近邻', 'k = 1，余弦距离'],
    ['PCA + 逻辑回归', 'L2 归一化 → 标准化 → PCA → 逻辑回归', '8 个主成分，C = 1'],
    ['RBF-SVM', 'L2 归一化 → RBF 核支持向量机', 'C = 10，γ = scale'],
], row_h=0.55, size=16)
text(s, 0.6, 4.75, 12.1, 0.4, [('评价指标（均在验证组层面计算）', 17, C['green'], True)])
for i, (head, body) in enumerate([('组级正确率', '预测正确的验证组比例'),
                                  ('宏平均 F1', f'{metrics["evaluated_classes"]} 个可验证类别的 F1 等权平均'),
                                  ('平衡准确率', '各类别召回率的平均值')]):
    x = 0.6 + i * 4.07
    rect(s, x, 5.25, 3.9, 1.3, C['pale'])
    text(s, x + 0.2, 5.38, 3.5, 1.1, [(head, 16, C['ink'], True), (body, 14, C['grey'], False)], space=4)
text(s, 0.6, 6.62, 12.1, 0.3, [(f'实现：scikit-learn {metrics["versions"]["sklearn"]}，Python {metrics["versions"]["python"]} [3]', 12, C['grey'], False)])

# ---------------------------------------------------------------- 8 overall results
s = new_slide(sec(4), '总体分类性能',
    f'第四部分是结果。【指向表格】余弦一近邻的组级正确率是 {pct(acc("Cosine_1NN"))}，RBF 支持向量机是 {pct(acc("RBF_SVC"))}，'
    f'PCA 加逻辑回归是 {pct(acc("PCA8_LR"))}，多数类基线只有 {pct(acc("Dummy"))}。\n'
    '【指向图 4】图 4 中，柱子是合并全部验证组的结果，圆点是每一折的结果。'
    f'余弦近邻各折在 {pct(spread["Cosine_1NN"][0])} 到 {pct(spread["Cosine_1NN"][1])} 之间，'
    f'支持向量机在 {pct(spread["RBF_SVC"][0])} 到 {pct(spread["RBF_SVC"][1])} 之间。'
    '两者相差约一个百分点，小于折间波动，我们也没有做显著性检验，因此只能认为两者性能相当。'
    f'另外，两种方法在 {agree:.0%} 的验证组上给出相同的预测。\n'
    'PCA 加逻辑回归明显落后，我们认为主要原因是只保留 8 维，对上千个类别而言信息损失过大。【翻页】')
rows = [['方法', '正确率', '宏 F1', '平衡准确率', '五折范围']]
for m, label in MODELS.items():
    g = M[m]['group']
    rows.append([label, pct(g['accuracy']), f'{g["macro_f1"]:.3f}', f'{g["balanced_accuracy"]:.3f}',
                 f'{100 * spread[m][0]:.1f}–{100 * spread[m][1]:.1f}%'])
table(s, 0.6, 1.75, [1.75, 1.0, 0.85, 1.15, 1.35], rows, row_h=0.52, size=14, align=[L, R, R, R, R])
text(s, 0.6, 4.55, 6.1, 2.2, [
    (f'{metrics["evaluated_classes"]} 类、{metrics["evaluated_groups"]:,} 个验证组的折外结果。', 14, C['grey'], False),
    (f'余弦 1-NN 与 RBF-SVM 相差 {100 * (acc("RBF_SVC") - acc("Cosine_1NN")):.1f} 个百分点，小于折间波动；未做显著性检验。', 15, C['ink'], False),
    (f'两者在 {agree:.0%} 的验证组上预测相同。', 15, C['ink'], False)], space=8)
figure(s, FIGURES['accuracy'], 6.95, 1.6, 5.75, '组级正确率：柱为全部验证组合并结果，点为各折结果')

# ---------------------------------------------------------------- 9 support
cs, ss = support.loc['Cosine_1NN'], support.loc['RBF_SVC']
cos_p, svm_p = (cs['sum'] / cs['count']), (ss['sum'] / ss['count'])
s = new_slide(sec(4), '类别标本数与正确率',
    '【指向图 5】图 5 按矿物拥有的独立标本数分组，纵轴是正确率，误差线是 95% 的 Wilson 置信区间 [4]，横轴下方标出了每组的验证组数。\n'
    f'只有 2 个标本时，训练侧只有 1 个同类标本可参考，余弦近邻正确率为 {cos_p.iloc[0]:.0%}，支持向量机为 {svm_p.iloc[0]:.0%}。'
    f'标本数达到 6 个及以上时，分别升至 {cos_p.iloc[-1]:.0%} 和 {svm_p.iloc[-1]:.0%}。\n'
    '【指向右侧文字】这说明，在当前数据下，每种矿物的标本覆盖程度是限制性能的主要因素。【翻页】')
figure(s, FIGURES['support_curve'], 0.6, 1.6, 6.9, '按类别独立标本数分组的组级正确率（误差线：95% Wilson 区间 [4]）')
rect(s, 7.95, 1.75, 4.78, 4.85, C['pale'])
text(s, 8.2, 1.95, 4.3, 4.5, [
    ('2 个标本', 17, C['green'], True),
    (f'训练侧仅 1 个同类标本：余弦 1-NN {cos_p.iloc[0]:.0%}，RBF-SVM {svm_p.iloc[0]:.0%}', 15, C['ink'], False),
    ('≥6 个标本', 17, C['green'], True),
    (f'余弦 1-NN {cos_p.iloc[-1]:.0%}，RBF-SVM {svm_p.iloc[-1]:.0%}', 15, C['ink'], False),
    ('解释', 17, C['green'], True),
    ('当前数据下，每类的标本覆盖是性能的主要限制因素', 15, C['ink'], False)], space=7)

# ---------------------------------------------------------------- 10 confusions
rows = [['真实 → 预测', '关系', '组数']]
for (t, p), n in pairs.items():
    if (t, p) in RELATIONS:
        rows.append([RELATIONS[t, p][0], RELATIONS[t, p][1], str(int(n))])
    if len(rows) == 7:
        break
assert rows[1][0] == RELATIONS['Amblygonite', 'Montebrasite'][0]
s = new_slide(sec(5), '同族矿物间的混淆',
    '第五部分是误差分析。【指向右侧表格】表中列出了余弦近邻最常见的混淆。排在前面的几乎都是同一固溶体系列或同一矿物族的矿物，'
    '例如锂磷铝石与羟磷锂铝石、镁铝榴石与铁铝榴石。\n'
    '【指向图 6】图 6 是其中两对矿物的平均光谱。两条曲线的主要峰位基本重合，差别主要在相对强度和个别峰的位置上。'
    '这类矿物结构相同，只是部分离子发生替换，仅凭这一段拉曼光谱很难区分，需要结合化学成分等信息。【翻页】')
figure(s, FIGURES['confused'], 0.6, 1.6, 5.9, '两对易混淆矿物的平均光谱（各自最大值归一化）')
table(s, 7.15, 1.75, [2.8, 2.0, 0.78], rows, row_h=0.52, size=14, align=[L, L, R])
text(s, 7.15, 5.5, 5.58, 1.2, [(f'余弦 1-NN 最常见的混淆对（共 {len(cos_err)} 个错误组）。'
                               '同族矿物结构相同、仅部分离子替换，拉曼峰位接近。', 14, C['grey'], False)])

# ---------------------------------------------------------------- 11 discussion
s = new_slide(sec(5), '讨论与局限',
    '下面是讨论与局限。【指向左栏】主要发现有三点：第一，最简单的余弦近邻与支持向量机性能相当；第二，误差集中在同族矿物之间；'
    f'第三，【指向图 7】余弦近邻的 {len(cos_err)} 个错误中，有 {to_single} 个，也就是 {to_single / len(cos_err):.0%}，被判为只有一个标本的矿物，'
    '说明这些无法验证的类别同样会参与竞争。\n'
    f'【指向右栏】本研究也有四点局限：第一，{metrics["training_only_classes"]:,} 种单标本矿物没有验证分数；'
    '第二，共同区间以外的光谱信息没有使用；第三，这是数据库内部验证，没有跨实验室、跨仪器的外部测试，'
    '而已有研究指出，验证方式会改变模型的排序；第四，方法之间的差异没有做显著性检验。【翻页】')
for x, head, color, items in [
        (0.6, '主要发现', C['green'], [
            '余弦 1-NN 与 RBF-SVM 性能相当，降至 8 维的 PCA + 逻辑回归明显落后',
            '误差集中于同族与固溶体矿物，304–852 cm⁻¹ 光谱的区分度有限',
            '无法验证的单标本类别同样参与竞争（图 7）']),
        (6.8, '局限', C['ochre'], [
            f'{metrics["training_only_classes"]:,} 种单标本矿物没有验证分数',
            '共同区间以外的光谱信息未使用',
            '仅数据库内部验证，无跨实验室、跨仪器的外部测试；验证方式会改变模型排序 [7]',
            '方法间差异未做显著性检验'])]:
    rect(s, x, 1.75, 5.93, 0.06, color)
    text(s, x, 1.95, 5.93, 0.45, [(head, 19, color, True)])
    bullets(s, x, 2.55, 5.93, 2.4, items, size=16, space=12)
figure(s, FIGURES['error_targets'], 0.6, 4.45, 5.6, '余弦 1-NN 错误预测的去向')

# ---------------------------------------------------------------- 12 demo
s = new_slide(sec(5), '交互演示：折外预测与参考库',
    '【提前在浏览器打开两个页面：assets/interactive/ch04-full.html 和 assets/interactive/ch04.html。】\n'
    '下面用交互页面演示两个具体例子。【切换到 ch04-full.html，不要动任何下拉框】\n'
    f'第一个例子。页面默认选中石英，模型是余弦近邻。【指向“预测”那一行】这是石英标本 {QUARTZ_SPECIMEN} 用 514 纳米激光测得的光谱。'
    '页面显示，余弦近邻预测为 Sodalite，即方钠石，与参考标签不一致，也就是说，单看这一条光谱，模型判错了。\n'
    '【在“实测光谱”下拉框选第二项，532 nm】换成同一标本 532 纳米的光谱，预测为 Quartz，正确。'
    '【再选第三项，780 nm】780 纳米的光谱也预测正确。该标本三条光谱中两条正确，投票结果为石英。这说明了按标本投票计分的作用。\n'
    '【在“固定模型”下拉框选“多数类基线”】换成多数类基线，它预测 Grossular，即钙铝榴石，因为这是训练集中最常见的矿物。\n'
    '【在“矿物类别”下拉框选第一项 Abelsonite】第二个例子是卟啉镍石，它只有一个标本。'
    '页面显示：本类别只有一个验证组，本谱只参与训练，没有验证预测。这就是前面所说的参考库。\n'
    '【切换到 ch04.html】最后，这个页面用模拟数据说明为什么要按标本划分。'
    '【“划分方式”选“逐谱随机划分（反例）”，“验证折”选 1】如果把光谱随机打乱划分，第 1 折中训练和验证两侧共享了 44 个标本，'
    '同一标本同时出现在训练和验证中，这就是数据泄漏。'
    '【“划分方式”改选“按物理标本分组”】按标本分组后，共享标本数为 0。这一页是模拟数据，不计入实测结果。\n'
    '【如果网页打不开：不做操作，指着本页右侧三个方框，依次念出每个方框的内容】\n'
    '【切回 PPT，翻页】')
figure(s, DEMO, 0.6, 1.6, 6.6, '全量交互页（assets/interactive/ch04-full.html）')
for i, (head, body) in enumerate([
        ('① 石英 Quartz（默认）', '514 nm 光谱被判为方钠石；同一标本另两条光谱正确，投票结果为石英'),
        ('② 卟啉镍石 Abelsonite', '仅一个标本：只在参考库中，没有验证预测'),
        ('③ 模拟页：两种划分', '逐谱随机划分时第 1 折两侧共享 44 个标本；按标本分组后为 0')]):
    y = 1.75 + i * 1.6
    rect(s, 7.6, y, 5.13, 1.4, C['pale'])
    text(s, 7.8, y + 0.15, 4.75, 1.15, [(head, 16, C['green'], True), (body, 14, C['ink'], False)], space=4)

# ---------------------------------------------------------------- 13 conclusion
s = new_slide(sec(6), '结论与展望',
    '最后是结论。【逐条指向】第一，在 606 类、1,789 个验证组的按标本分组验证中，最好的组级正确率约为 71%。'
    '第二，余弦一近邻与 RBF 支持向量机性能相当，误差主要来自同族和固溶体矿物。'
    '第三，正确率随每类独立标本数增加而提高，数据覆盖是当前的主要限制。\n'
    '【指向展望】下一步，一是为同一矿物收集更多不同产地的标本；二是补充跨实验室、跨仪器的外部验证，并按照 REFORMS 规范报告；'
    '三是尝试 TabPFN 等新的基线方法。\n'
    '我们的汇报到此结束，谢谢各位老师和同学，欢迎提问。【翻到参考文献页，停留等待提问】')
text(s, 0.6, 1.7, 12.1, 0.45, [('结论', 19, C['green'], True)])
for i, body in enumerate([
        f'在 {metrics["evaluated_classes"]} 类、{metrics["evaluated_groups"]:,} 个验证组的按标本分组验证中，最好的组级正确率约为 {acc("RBF_SVC"):.0%}',
        '余弦 1-NN 与 RBF-SVM 性能相当；误差主要来自同族和固溶体矿物',
        '正确率随每类独立标本数增加而提高，数据覆盖是当前的主要限制']):
    y = 2.25 + i * 0.85
    rect(s, 0.6, y, 0.55, 0.55, C['green'])
    text(s, 0.6, y, 0.55, 0.55, [(str(i + 1), 18, WHITE, True)], anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
    text(s, 1.4, y, 11.3, 0.55, [(body, 18, C['ink'], False)], anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.6, 4.85, 12.1, 0.45, [('展望', 19, C['ochre'], True)])
for i, body in enumerate(['为同一矿物收集更多不同产地的独立标本',
                          '补充跨实验室、跨仪器的外部验证，按 REFORMS 规范报告 [6]',
                          '尝试 TabPFN 等新的基线方法 [8]']):
    x = 0.6 + i * 4.07
    rect(s, x, 5.4, 3.9, 1.2, C['pale'])
    text(s, x + 0.2, 5.4, 3.5, 1.2, [(body, 16, C['ink'], False)], anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 14 references
spread_pp = [100 * (hi - lo) for lo, hi in (spread['Cosine_1NN'], spread['RBF_SVC'])]
s = new_slide('', '参考文献',
    '【本页在提问环节保持显示。以下是可能被问到的问题和回答，被问到时照念对应的回答。】\n'
    '问：SVM 的正确率更高，为什么说两者相当？\n'
    f'答：两者只差约一个百分点；而同一种方法在不同折之间，正确率就相差 {min(spread_pp):.0f} 到 {max(spread_pp):.0f} 个百分点。'
    '差距在波动范围之内，我们也没有做显著性检验，所以不能说谁更好。\n'
    '问：为什么只用 304 到 852 这一段波数？\n'
    '答：不同光谱的测量范围不一样，304 到 852 是所有光谱都完整覆盖的共同区间。我们没有外推，也没有补造缺失的数据。\n'
    '问：只有一个标本的矿物为什么不计分？\n'
    '答：我们要检验的是模型能否识别没有见过的标本。只有一个标本的矿物，把它留出验证后，训练侧就没有同种矿物了，无法检验。\n'
    '问：为什么不调参？\n'
    '答：参数事先固定，是为了避免根据验证成绩选择参数，导致成绩偏高。\n'
    '问：为什么不用更复杂的模型？\n'
    '答：本研究的目标是先在按标本验证的规则下给出可信的基线结果。结果表明，瓶颈主要在每种矿物的标本数量，更复杂的模型不一定能解决。\n'
    '问：被问到不会的问题时\n'
    '答：这个问题我们这次没有研究，会后查证后再回复您。')
text(s, 0.6, 1.65, 12.1, 5.2, [[(f'[{i}] ', 13, C['green'], True), (ref, 13, C['ink'], False)] for i, ref in enumerate(REFERENCES, 1)], space=7)

prs.save(OUT)
print('wrote', OUT, len(prs.slides), 'slides; figures in', FIG)

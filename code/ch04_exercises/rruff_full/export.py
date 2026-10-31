"""Export a compact offline reader and scientific plots from saved predictions."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from run import HERE, MODEL_NAMES, load_data


def export(output):
    out = Path(output)
    _, meta, X, _, classes, axis = load_data()
    result = json.loads((out/'metrics.json').read_text())
    rows = pd.read_csv(out/'row_predictions.csv', dtype={'spectrum_id':str})
    folds = pd.read_csv(out/'spectrum_folds.csv', dtype={'spectrum_id':str}).set_index('spectrum_id')
    groups = pd.read_csv(out/'group_predictions.csv')
    plt.rcParams.update({'svg.fonttype':'none'})
    fig, ax = plt.subplots(figsize=(10, 4.8), constrained_layout=True)
    xx = np.arange(4)
    ax.bar(xx-.19, [result['metrics'][n]['group']['accuracy'] for n in MODEL_NAMES], .38, label='Group accuracy', color='#326a91')
    ax.bar(xx+.19, [result['metrics'][n]['group']['macro_f1'] for n in MODEL_NAMES], .38, label='Macro-F1 (eligible classes)', color='#c47d29')
    ax.set(xticks=xx, xticklabels=['Majority','Cosine 1NN','PCA8 + LR','RBF SVM'], ylim=(0,1), ylabel='Score',
           title=f"Five-fold grouped validation: {result['evaluated_groups']} groups / {result['evaluated_classes']} classes")
    ax.legend();ax.spines[['top','right']].set_visible(False)
    for bars in ax.containers:ax.bar_label(bars, fmt='%.3f', padding=3)
    fig.savefig(out/'model_comparison.svg');plt.close(fig)
    norms = X / np.linalg.norm(X, axis=1, keepdims=True)
    pred = {n:rows[rows.model.eq(n)].set_index('spectrum_id').predicted_class.to_dict() for n in MODEL_NAMES}
    spectra=[]
    for i,r in enumerate(meta.itertuples()):
        spectra.append({'id':r.spectrum_id,'specimen':r.specimen_id,'group':r.validation_group,'mineral':r.mineral,
                        'laser':float(r.laser_nm),'fold':int(folds.loc[r.spectrum_id,'fold']),
                        'y':[float(f'{v:.5g}') for v in norms[i,::2]],
                        'predictions':{n:int(pred[n][r.spectrum_id]) for n in MODEL_NAMES if r.spectrum_id in pred[n]}})
    browser={'summary':{k:v for k,v in result.items() if k not in ['timings','warnings']},'classes':classes,
             'axis':axis[::2].tolist(),'spectra':spectra}
    (out/'browser-data.js').write_text('window.RRUFF_FULL='+json.dumps(browser,ensure_ascii=False,separators=(',',':'))+';\n')
    counts = pd.read_csv(HERE/'data/class_counts.csv')
    fig,ax=plt.subplots(figsize=(9,4),constrained_layout=True)
    labels=['1 group','2 groups','3–4 groups','5–9 groups','10+ groups']
    values=[sum(counts.validation_groups==1),sum(counts.validation_groups==2),sum(counts.validation_groups.between(3,4)),sum(counts.validation_groups.between(5,9)),sum(counts.validation_groups>=10)]
    bars=ax.bar(labels,values,color=['#9babb7','#326a91','#326a91','#326a91','#326a91']);ax.bar_label(bars,padding=3)
    ax.set(ylabel='Mineral classes',title='Independent-group support after source audit',ylim=(0,max(values)*1.15))
    ax.spines[['top','right']].set_visible(False);fig.savefig(out/'class_support.svg');plt.close(fig)
    print('Exported figures and offline browser data.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=HERE/'outputs');export(p.parse_args().output)

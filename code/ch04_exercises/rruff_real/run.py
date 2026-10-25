"""Fixed-model, leave-one-RRUFF-ID-out evaluation on measured spectra."""
import argparse
import hashlib
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer, StandardScaler
from sklearn.svm import SVC
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLASSES = ['Quartz', 'Calcite', 'Gypsum']
AXIS = np.arange(200., 1201., 2.)
CONFIG = {'classes': CLASSES, 'wavenumber_cm-1': [200, 1200, 2],
          'validation': 'LeaveOneGroupOut, group=RRUFF ID',
          'models_fixed_before_evaluation': ['Dummy', 'Cosine_1NN', 'PCA8_LR', 'RBF_SVC'],
          'hyperparameters': {'PCA_components': 8, 'LR_C': 1.0, 'SVC_C': 10.0, 'SVC_gamma': 'scale'},
          'normalization': 'L2 per spectrum; scale/PCA fitted inside each training fold',
          'selection': 'No model selection or tuning on the reported out-of-fold results; report all four.',
          'vote_tie': 'Lowest class index in Quartz, Calcite, Gypsum order',
          'augmentation': 'None', 'external_instrument_test': 'None'}


def load_data(directory=HERE / 'data'):
    directory = Path(directory)
    meta = pd.read_csv(directory / 'manifest.csv', dtype={'spectrum_id': str})
    if not meta.spectrum_id.is_unique or meta.specimen_id.isna().any():
        raise ValueError('Missing specimen ID or duplicated spectrum ID')
    if not meta.groupby('specimen_id').mineral.nunique().eq(1).all():
        raise ValueError('Conflicting mineral labels for one specimen')
    arrays = np.load(directory / 'measured_processed_spectra.npz', allow_pickle=False)
    if set(arrays.files) != set('s' + meta.spectrum_id):
        raise ValueError('Manifest and numeric archive disagree')
    spectra, hashes = [], {}
    for row in meta.itertuples():
        a = arrays['s' + row.spectrum_id]
        digest = hashlib.sha256(a.astype('<f8').tobytes()).hexdigest()
        if digest != row.numeric_sha256:
            raise ValueError('Spectrum checksum mismatch')
        if a.ndim != 2 or a.shape[1] != 2 or not np.isfinite(a).all():
            raise ValueError('Invalid numeric spectrum')
        if not np.all(np.diff(a[:, 0]) > 0) or a[0, 0] > AXIS[0] or a[-1, 0] < AXIS[-1]:
            raise ValueError('Invalid axis or missing coverage; no extrapolation allowed')
        if digest in hashes and hashes[digest] != row.specimen_id:
            raise ValueError('Identical spectrum occurs under distinct specimen IDs')
        hashes[digest] = row.specimen_id
        spectra.append(np.interp(AXIS, a[:, 0], a[:, 1]))
    X = np.array(spectra)
    if np.any(np.linalg.norm(X, axis=1) == 0):
        raise ValueError('Zero spectrum')
    return meta, X, np.array([CLASSES.index(v) for v in meta.mineral])


def models():
    return {
        'Dummy': DummyClassifier(strategy='most_frequent'),
        'Cosine_1NN': make_pipeline(Normalizer(), KNeighborsClassifier(n_neighbors=1, metric='cosine')),
        'PCA8_LR': make_pipeline(Normalizer(), StandardScaler(), PCA(n_components=8, svd_solver='full'),
                                LogisticRegression(C=1, max_iter=5000, random_state=2026)),
        'RBF_SVC': make_pipeline(Normalizer(), SVC(C=10, gamma='scale')),
    }


def scores(truth, predicted):
    return {'macro_f1': float(f1_score(truth, predicted, labels=range(3), average='macro', zero_division=0)),
            'balanced_accuracy': float(balanced_accuracy_score(truth, predicted)),
            'confusion_matrix': confusion_matrix(truth, predicted, labels=range(3)).tolist()}


def evaluate(meta, X, y):
    rows, folds = [], []
    for fold, (train, test) in enumerate(LeaveOneGroupOut().split(X, y, meta.specimen_id), 1):
        train_ids = sorted(set(meta.iloc[train].specimen_id))
        test_ids = sorted(set(meta.iloc[test].specimen_id))
        assert not set(train_ids) & set(test_ids)
        assert set(y[train]) == set(range(3))
        folds.append({'fold': fold, 'train_ids': train_ids, 'test_ids': test_ids,
                      'train_spectra': len(train), 'test_spectra': len(test), 'shared_ids': 0})
        for name, estimator in models().items():
            prediction = clone(estimator).fit(X[train], y[train]).predict(X[test])
            for index, pred in zip(test, prediction):
                r = meta.iloc[index]
                rows.append({'model': name, 'fold': fold, 'spectrum_id': r.spectrum_id,
                             'specimen_id': r.specimen_id, 'mineral': r.mineral, 'laser_nm': int(r.laser_nm),
                             'true_class': int(y[index]), 'predicted_class': int(pred)})
    rows = pd.DataFrame(rows)
    samples = []
    for (name, sid), group in rows.groupby(['model', 'specimen_id'], sort=False):
        votes = np.bincount(group.predicted_class, minlength=3)
        samples.append({'model': name, 'specimen_id': sid, 'fold': int(group.fold.iloc[0]),
                        'mineral': group.mineral.iloc[0], 'true_class': int(group.true_class.iloc[0]),
                        'predicted_class': int(votes.argmax()), 'n_spectra': len(group),
                        'vote_tie': int(np.sum(votes == votes.max()) > 1)})
    samples = pd.DataFrame(samples)
    metrics = {name: {'specimen': scores(g.true_class, g.predicted_class),
                       'spectrum': scores(rows[rows.model.eq(name)].true_class, rows[rows.model.eq(name)].predicted_class)}
               for name, g in samples.groupby('model', sort=False)}
    return rows, samples, folds, metrics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HERE / 'outputs')
    args = p.parse_args()
    out = args.output.resolve();out.mkdir(parents=True, exist_ok=True)
    (out / 'protocol.json').write_text(json.dumps(CONFIG, indent=2) + '\n', encoding='utf-8')
    meta, X, y = load_data()
    with threadpool_limits(limits=1):
        rows, samples, folds, metrics = evaluate(meta, X, y)
    rows.to_csv(out / 'row_predictions.csv', index=False)
    samples.to_csv(out / 'specimen_predictions.csv', index=False)
    result = {'data_status': 'REAL MEASURED, SOURCE-PROCESSED RRUFF SPECTRA',
              'source_doi': '10.11583/DTU.20222331.v1', 'n_spectra': len(meta),
              'n_specimens': int(meta.specimen_id.nunique()), 'class_order': CLASSES,
              'counts': {k: {'spectra': len(g), 'specimens': int(g.specimen_id.nunique())} for k,g in meta.groupby('mineral')},
              'metrics': metrics, 'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__},
              'limits': ['Gypsum: only two specimens.', 'Leave-one-specimen-out, not an independent external test.',
                         'Source preprocessing predates our model evaluation.', 'No instrument transfer claim; laser wavelength is not instrument ID.',
                         'No model was selected using these results. Future tuning needs nested validation or new held-out specimens.']}
    (out / 'metrics.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (out / 'folds.json').write_text(json.dumps(folds, indent=2) + '\n', encoding='utf-8')
    plt.rcParams.update({'svg.fonttype': 'none', 'svg.hashsalt': 'g04-rruff-real'})
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.4), constrained_layout=True)
    norm = Normalizer().fit_transform(X)
    for j, name in enumerate(CLASSES):
        ids = np.where(meta.mineral.eq(name).to_numpy())[0]
        for i in ids:ax[j].plot(AXIS, norm[i], alpha=.35, lw=.7)
        ax[j].set(title=f'{name}: {len(ids)} spectra / {meta.iloc[ids].specimen_id.nunique()} IDs', xlabel='Raman shift (cm$^{-1}$)', ylabel='L2-normalized intensity')
    fig.suptitle('Measured RRUFF spectra, processed by source; DTU dataset v1 (CC BY 4.0)')
    fig.savefig(out / 'measured_spectra.svg', metadata={'Date': None});plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(9, 7), constrained_layout=True)
    for ax,(name,m) in zip(axes.flat, metrics.items()):
        matrix = np.array(m['specimen']['confusion_matrix']);ax.imshow(matrix,vmin=0,vmax=10,cmap='Blues')
        for i in range(3):
            for j in range(3):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>5 else 'black')
        ax.set(xticks=range(3),yticks=range(3),xticklabels=CLASSES,yticklabels=CLASSES,xlabel='Predicted',ylabel='Reference',title=f"{name}: macro-F1 {m['specimen']['macro_f1']:.3f}")
    fig.suptitle('Leave-one-RRUFF-ID-out: 22 specimens; Gypsum has only 2 IDs')
    fig.savefig(out / 'confusion_matrices.svg', metadata={'Date':None});plt.close(fig)
    for figure in out.glob('*.svg'):
        figure.write_text('\n'.join(line.rstrip() for line in figure.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    page_data = {'results': result, 'axis': AXIS.tolist(), 'spectra': [
        {'id':r.spectrum_id,'specimen':r.specimen_id,'mineral':r.mineral,'laser':int(r.laser_nm),
         'intensity':[float(f'{v:.7g}') for v in norm[i]]} for i,r in enumerate(meta.itertuples())],
         'predictions': rows.to_dict('records')}
    (out / 'browser-data.js').write_text('window.RRUFF_REAL='+json.dumps(page_data,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

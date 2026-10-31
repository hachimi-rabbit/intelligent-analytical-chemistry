"""Fixed baselines on all usable RRUFF records, with group-isolated evaluation."""
import argparse
import json
import platform
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer, StandardScaler
from sklearn.svm import SVC
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
MODEL_NAMES = ('Dummy', 'Cosine_1NN', 'PCA8_LR', 'RBF_SVC')
SEED = 20261026
N_FOLDS = 5


def load_data(directory=HERE / 'data'):
    directory = Path(directory)
    manifest = pd.read_csv(directory / 'manifest.csv', dtype={'spectrum_id': str}).fillna({'reason': ''})
    meta = manifest[manifest.status.eq('usable')].reset_index(drop=True)
    with np.load(directory / 'features.npz', allow_pickle=False) as z:
        X, axis = z['X'], z['axis']
    if not meta.matrix_row.eq(np.arange(len(meta))).all() or X.shape != (len(meta), len(axis)):
        raise ValueError('Manifest and matrix differ')
    if not meta.spectrum_id.is_unique or not np.isfinite(X).all() or np.any(np.linalg.norm(X, axis=1) == 0):
        raise ValueError('Invalid feature matrix or identities')
    if not meta.groupby('validation_group').mineral.nunique().eq(1).all():
        raise ValueError('Conflicting validation-group labels')
    classes = sorted(meta.mineral.unique())
    y = pd.Categorical(meta.mineral, categories=classes).codes
    return manifest, meta, X, y, classes, axis


def estimator(name):
    if name == 'Dummy':
        return DummyClassifier(strategy='most_frequent')
    if name == 'Cosine_1NN':
        return make_pipeline(Normalizer(), KNeighborsClassifier(n_neighbors=1, metric='cosine', n_jobs=1))
    if name == 'PCA8_LR':
        return make_pipeline(Normalizer(), StandardScaler(), PCA(n_components=8, svd_solver='full'),
                             LogisticRegression(C=1, max_iter=5000, random_state=SEED))
    if name == 'RBF_SVC':
        return make_pipeline(Normalizer(), SVC(C=10, gamma='scale', cache_size=512))
    raise ValueError(name)


def assign_folds(meta):
    groups = meta[['validation_group', 'mineral']].drop_duplicates().sort_values(['mineral', 'validation_group'])
    rng = np.random.default_rng(SEED)
    assignment = {}
    for _, rows in groups.groupby('mineral', sort=True):
        ids = rng.permutation(rows.validation_group.to_numpy())
        if len(ids) == 1:
            assignment[ids[0]] = -1
        else:
            start = int(rng.integers(N_FOLDS))
            for i, group in enumerate(ids):
                assignment[group] = (start + i) % N_FOLDS
    return meta.validation_group.map(assignment).to_numpy(), groups.assign(fold=groups.validation_group.map(assignment))


def vote(frame, classes):
    rows = []
    for group, g in frame.groupby('validation_group', sort=True):
        winner = int(np.bincount(g.predicted_class, minlength=len(classes)).argmax())
        rows.append({'model': g.model.iloc[0], 'fold': int(g.fold.iloc[0]),
                     'validation_group': group, 'specimen_ids': '|'.join(sorted(g.specimen_id.unique())),
                     'true_class': int(g.true_class.iloc[0]), 'predicted_class': winner,
                     'true_mineral': classes[int(g.true_class.iloc[0])], 'predicted_mineral': classes[winner],
                     'n_spectra': len(g)})
    return pd.DataFrame(rows)


def scores(frame, labels):
    return {'accuracy': float(accuracy_score(frame.true_class, frame.predicted_class)),
            'macro_f1': float(f1_score(frame.true_class, frame.predicted_class, labels=labels, average='macro', zero_division=0)),
            'balanced_accuracy': float(recall_score(frame.true_class, frame.predicted_class, labels=labels, average='macro', zero_division=0)),
            'correct': int(frame.true_class.eq(frame.predicted_class).sum()), 'total': len(frame)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HERE / 'outputs')
    p.add_argument('--models-dir', type=Path, default=HERE / 'models')
    a = p.parse_args()
    out, model_dir = a.output.resolve(), a.models_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    manifest, meta, X, y, classes, axis = load_data()
    fold, assignment = assign_folds(meta)
    evaluated = fold >= 0
    labels = sorted(np.unique(y[evaluated]).tolist())
    assignment.to_csv(out / 'group_folds.csv', index=False)
    meta.assign(fold=fold).to_csv(out / 'spectrum_folds.csv', index=False)
    protocol = {'models': list(MODEL_NAMES), 'seed': SEED, 'folds': N_FOLDS,
                'axis': [float(axis[0]), float(axis[-1]), float(axis[1]-axis[0])],
                'pca_components': 8, 'lr_C': 1, 'svc_C': 10, 'svc_gamma': 'scale',
                'grouping': 'RRUFF ID; IDs with identical interpolated input vectors and same label are co-grouped.',
                'validation': 'Class-wise balanced assignment of whole groups to five folds. Single-group classes remain training-only in every fold.',
                'score_labels': labels, 'class_order': classes,
                'vote_tie': 'Alphabetically first mineral label.',
                'selection': 'All four fixed candidates reported, no tuning or score-based model selection.',
                'final_fit': 'After validation, each fixed model is refitted on every usable spectrum; no training score is reported as test performance.',
                'external_test': False}
    (out / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    metrics, warning_records, run_times = {}, [], []
    all_rows, all_votes = [], []
    with threadpool_limits(limits=2):
        for name in MODEL_NAMES:
            rows = []
            for f in range(N_FOLDS):
                test = fold == f
                train = ~test
                if set(meta.loc[test, 'validation_group']) & set(meta.loc[train, 'validation_group']):
                    raise AssertionError('Group leakage')
                if not set(y[test]).issubset(set(y[train])):
                    raise AssertionError('Validation class absent in training')
                print(f'{name}: fold {f+1}/{N_FOLDS}, train {sum(train)}, validate {sum(test)}', flush=True)
                model = estimator(name)
                started = time.monotonic()
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    model.fit(X[train], y[train])
                    predicted = model.predict(X[test])
                warning_records.extend({'model': name, 'fold': f, 'message': str(w.message)} for w in caught)
                run_times.append({'model': name, 'fold': f, 'seconds': time.monotonic()-started})
                frame = meta.loc[test, ['spectrum_id', 'specimen_id', 'validation_group', 'mineral']].copy()
                frame['model'], frame['fold'] = name, f
                frame['true_class'], frame['predicted_class'] = y[test], predicted
                frame['predicted_mineral'] = [classes[int(v)] for v in predicted]
                rows.append(frame)
            rows = pd.concat(rows, ignore_index=True)
            grouped = vote(rows, classes)
            metrics[name] = {'group': scores(grouped, labels), 'spectrum': scores(rows, labels)}
            rows.to_csv(out / f'{name}_predictions.csv', index=False)
            grouped.to_csv(out / f'{name}_groups.csv', index=False)
            all_rows.append(rows)
            all_votes.append(grouped)
            print(name, json.dumps(metrics[name]['group']), flush=True)
            print(name, 'final fit on', len(meta), 'spectra', flush=True)
            final_model = estimator(name)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                final_model.fit(X, y)
            warning_records.extend({'model': name, 'fold': 'final_fit', 'message': str(w.message)} for w in caught)
            joblib.dump({'model': final_model, 'classes': classes, 'axis': axis,
                         'training_spectrum_ids': meta.spectrum_id.tolist(),
                         'protocol': protocol}, model_dir / (name + '.joblib'), compress=3)
    source = json.loads((HERE / 'data/provenance.json').read_text())
    result = {k: source[k] for k in ['source_spectra', 'source_specimens', 'source_classes', 'usable_spectra',
                                      'usable_specimens', 'usable_classes', 'usable_validation_groups']}
    result.update({'evaluated_spectra': int(evaluated.sum()),
                   'evaluated_groups': int(meta.loc[evaluated, 'validation_group'].nunique()),
                   'evaluated_specimens': int(meta.loc[evaluated, 'specimen_id'].nunique()),
                   'evaluated_classes': len(labels), 'training_only_spectra': int((~evaluated).sum()),
                   'training_only_classes': len(classes)-len(labels), 'excluded_spectra': len(manifest)-len(meta),
                   'metrics': metrics, 'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__},
                   'warnings': warning_records, 'timings': run_times,
                   'limits': source['limits'] + ['Scores apply only to classes with at least two validation groups.',
                     'Single-group classes contribute training references but have no new-specimen score.',
                     'No external-laboratory validation and no hyperparameter search.']})
    (out / 'metrics.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    pd.concat(all_rows).to_csv(out / 'row_predictions.csv', index=False)
    votes = pd.concat(all_votes)
    votes.to_csv(out / 'group_predictions.csv', index=False)
    errors = votes[votes.true_class.ne(votes.predicted_class)]
    errors.groupby(['model', 'true_mineral', 'predicted_mineral']).size().reset_index(name='groups').sort_values('groups', ascending=False).to_csv(out / 'confusions.csv', index=False)
    print('Finished all grouped evaluations and final fits.', flush=True)


if __name__ == '__main__':
    main()

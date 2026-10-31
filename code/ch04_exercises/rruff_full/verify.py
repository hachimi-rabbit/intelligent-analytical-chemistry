"""Check full-source accounting, group isolation and reported metrics."""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score

from run import HERE, MODEL_NAMES, N_FOLDS, load_data


def verify(output, models_dir):
    out = Path(output)
    source, meta, X, y, classes, axis = load_data()
    metrics = json.loads((out / 'metrics.json').read_text())
    protocol = json.loads((out / 'protocol.json').read_text())
    folds = pd.read_csv(out / 'spectrum_folds.csv', dtype={'spectrum_id': str})
    rows = pd.read_csv(out / 'row_predictions.csv', dtype={'spectrum_id': str})
    groups = pd.read_csv(out / 'group_predictions.csv')
    checks = []
    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        checks.append(label)
    check(len(source) == 5228 and source.spectrum_id.is_unique, 'all 5228 source records retained')
    check(len(meta) + source.status.eq('excluded').sum() == len(source), 'source accounting')
    check(source.loc[source.status.eq('excluded'), 'reason'].str.len().gt(0).all(), 'all exclusions have reasons')
    check(folds.spectrum_id.tolist() == meta.spectrum_id.tolist(), 'fold identity order')
    check(folds.groupby('validation_group').fold.nunique().eq(1).all(), 'one fold per validation group')
    counts = meta[['validation_group', 'mineral']].drop_duplicates().groupby('mineral').size()
    check(folds.fold.eq(-1).equals(meta.mineral.map(counts).eq(1)), 'only singleton classes are training-only')
    check(set(folds.fold) == {-1, *range(N_FOLDS)}, 'five validation folds and training-only marker')
    _, duplicate = np.unique(X, axis=0, return_inverse=True)
    d = folds.assign(duplicate=duplicate)
    check(d.groupby('duplicate').validation_group.nunique().eq(1).all(), 'identical model inputs never cross validation groups')
    for f in range(N_FOLDS):
        test = folds.fold.eq(f)
        check(not set(folds.loc[test, 'specimen_id']) & set(folds.loc[~test, 'specimen_id']), f'no shared specimens fold {f}')
        check(set(meta.loc[test, 'mineral']).issubset(set(meta.loc[~test, 'mineral'])), f'all test classes represented in training fold {f}')
    selected = folds[folds.fold.ge(0)]
    label_ids = protocol['score_labels']
    check(set(rows.model) == set(groups.model) == set(MODEL_NAMES), 'all four models reported')
    for name in MODEL_NAMES:
        r = rows[rows.model.eq(name)]
        g = groups[groups.model.eq(name)]
        check(r.spectrum_id.is_unique and set(r.spectrum_id) == set(selected.spectrum_id), name+' complete held-out predictions')
        merged = r.merge(selected[['spectrum_id', 'fold', 'validation_group']], on='spectrum_id', validate='one_to_one', suffixes=('', '_reference'))
        check(merged.fold.eq(merged.fold_reference).all() and merged.validation_group.eq(merged.validation_group_reference).all(), name+' fold attribution')
        truth = meta.set_index('spectrum_id').mineral.to_dict()
        check(all(classes[int(t)] == truth[s] for s, t in zip(r.spectrum_id, r.true_class)), name+' reference labels')
        check(g.validation_group.is_unique and set(g.validation_group) == set(selected.validation_group), name+' complete group predictions')
        for group, h in r.groupby('validation_group'):
            prediction = int(np.bincount(h.predicted_class, minlength=len(classes)).argmax())
            saved = g[g.validation_group.eq(group)].iloc[0]
            check(prediction == saved.predicted_class and saved.true_class == h.true_class.iloc[0], name+' vote '+group)
        for key, frame in [('group', g), ('spectrum', r)]:
            v = metrics['metrics'][name][key]
            expected = [accuracy_score(frame.true_class, frame.predicted_class),
                        f1_score(frame.true_class, frame.predicted_class, labels=label_ids, average='macro', zero_division=0),
                        recall_score(frame.true_class, frame.predicted_class, labels=label_ids, average='macro', zero_division=0)]
            check(np.allclose(expected, [v['accuracy'], v['macro_f1'], v['balanced_accuracy']]), name+' recomputed '+key+' metrics')
        bundle = joblib.load(Path(models_dir) / (name+'.joblib'))
        check(bundle['training_spectrum_ids'] == meta.spectrum_id.tolist(), name+' final model fitted to all usable records')
        check(bundle['classes'] == classes and np.array_equal(bundle['axis'], axis), name+' final model metadata')
        check(set(bundle['model'].classes_) == set(range(len(classes))), name+' final class coverage')
    check(metrics['evaluated_spectra'] == len(selected), 'evaluation spectrum count')
    check(metrics['evaluated_groups'] == selected.validation_group.nunique(), 'evaluation group count')
    check(metrics['training_only_spectra'] == folds.fold.eq(-1).sum(), 'training-only spectrum count')
    check(not metrics['warnings'], 'model fits completed without warnings')
    print(f'PASS: {len(checks)} checks; {len(source)} source rows, {len(meta)} final training rows, {len(selected)} held-out rows per model.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HERE/'outputs')
    p.add_argument('--models-dir', type=Path, default=HERE/'models')
    a = p.parse_args()
    verify(a.output, a.models_dir)

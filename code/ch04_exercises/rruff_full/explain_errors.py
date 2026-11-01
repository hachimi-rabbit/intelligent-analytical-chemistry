"""Trace selected archived cosine-1NN errors to fold-isolated training spectra.

This is a post-hoc illustration, not an exhaustive mineral-family annotation,
a learning curve, or a new performance evaluation. Run from any directory.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize
from threadpoolctl import threadpool_limits

from run import HERE, assign_folds, estimator, load_data

EXAMPLE_PAIRS = [('Amblygonite', 'Montebrasite'), ('Pyrope', 'Almandine'),
                 ('Grossular', 'Andradite')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'outputs')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = HERE / 'outputs'
    relations = json.loads((HERE / 'mineral_relations.json').read_text())
    _, meta, X, y, classes, axis = load_data()
    folds, group_folds = assign_folds(meta)
    rows = pd.read_csv(source / 'Cosine_1NN_predictions.csv', dtype={'spectrum_id': str})
    groups = pd.read_csv(source / 'Cosine_1NN_groups.csv')
    errors = groups[groups.true_mineral.ne(groups.predicted_mineral)]
    counts = errors.groupby(['true_mineral', 'predicted_mineral']).size()
    pair_rows = []
    for r in relations:
        pair_rows.append({**{k: r[k] for k in ['true_mineral', 'predicted_mineral', 'relation_zh']},
                          'error_groups': int(counts.get((r['true_mineral'], r['predicted_mineral']), 0)),
                          'source_dois': ';'.join(r['source_dois'])})
    pd.DataFrame(pair_rows).to_csv(out / 'mineral_error_pairs.csv', index=False)
    sizes = group_folds.groupby('mineral').size()
    single = set(sizes[sizes.eq(1)].index)
    summary = {
        'model': 'Cosine_1NN', 'all_error_groups': len(errors),
        'selected_pair_error_groups': sum(r['error_groups'] for r in pair_rows),
        'errors_predicted_as_training_only_classes': int(errors.predicted_mineral.isin(single).sum()),
        'selection': 'Six preselected literature-supported pairs; not a complete family classification or global top-six list.',
        'example_selection': 'For each of three declared pairs, first validation group and first matching erroneous spectrum in lexical ID order.',
        'input_sha256': {},
    }
    for rel in ['data/features.npz', 'data/manifest.csv', 'mineral_relations.json',
                'outputs/Cosine_1NN_predictions.csv', 'outputs/Cosine_1NN_groups.csv',
                'outputs/group_folds.csv']:
        summary['input_sha256'][rel] = hashlib.sha256((HERE / rel).read_bytes()).hexdigest()
    normalized = normalize(X)
    examples, plotted = [], []
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none', 'svg.hashsalt': 'g04-errors'})
    fig, axes = plt.subplots(3, 1, figsize=(11, 11), sharex=True, layout='constrained')
    with threadpool_limits(limits=2):
        for ax, (truth, prediction) in zip(axes, EXAMPLE_PAIRS):
            pair_groups = errors[errors.true_mineral.eq(truth) & errors.predicted_mineral.eq(prediction)]
            if pair_groups.empty:
                raise AssertionError(f'Archived example absent: {truth} -> {prediction}')
            group = pair_groups.sort_values('validation_group').iloc[0].validation_group
            chosen = rows[rows.validation_group.eq(group) & rows.predicted_mineral.eq(prediction)]
            row = chosen.sort_values('spectrum_id').iloc[0]
            index = int(meta.index[meta.spectrum_id.eq(row.spectrum_id)][0])
            fold = int(folds[index])
            if fold < 0 or fold != row.fold:
                raise AssertionError('Example is not held out in its archived fold')
            train_ids = np.flatnonzero(folds != fold)
            if group in set(meta.iloc[train_ids].validation_group):
                raise AssertionError('Example group leaked into reference search')
            model = estimator('Cosine_1NN').fit(X[train_ids], y[train_ids])
            transformed = model.steps[0][1].transform(X[index:index+1])
            distance, local = model.steps[1][1].kneighbors(transformed)
            neighbor = int(train_ids[int(local[0, 0])])
            if classes[int(y[neighbor])] != prediction or int(model.predict(X[index:index+1])[0]) != row.predicted_class:
                raise AssertionError('Nearest reference does not reproduce the archived prediction')
            correct_ids = train_ids[y[train_ids] == y[index]]
            if len(correct_ids) == 0:
                raise AssertionError('No same-class training reference')
            similarities = normalized[correct_ids] @ normalized[index]
            correct = int(correct_ids[int(similarities.argmax())])
            examples.append({
                'true_mineral': truth, 'predicted_mineral': prediction, 'validation_group': group,
                'fold': fold, 'test_spectrum_id': row.spectrum_id, 'test_specimen_id': meta.iloc[index].specimen_id,
                'nearest_spectrum_id': meta.iloc[neighbor].spectrum_id,
                'nearest_specimen_id': meta.iloc[neighbor].specimen_id,
                'nearest_validation_group': meta.iloc[neighbor].validation_group,
                'nearest_cosine_similarity': 1-float(distance[0, 0]),
                'same_class_spectrum_id': meta.iloc[correct].spectrum_id,
                'same_class_specimen_id': meta.iloc[correct].specimen_id,
                'same_class_cosine_similarity': float(similarities.max()),
                'test_laser_nm': meta.iloc[index].laser_nm,
                'nearest_laser_nm': meta.iloc[neighbor].laser_nm,
                'same_class_laser_nm': meta.iloc[correct].laser_nm,
            })
            for role, idx, color, style in [('held-out', index, '#176c96', '-'),
                                          ('nearest wrong class', neighbor, '#ae6d22', '-'),
                                          ('nearest same class', correct, '#68747c', '--')]:
                record = meta.iloc[idx]
                ax.plot(axis, normalized[idx], color=color, linestyle=style, lw=1.4,
                        label=f'{role}: {record.mineral}, {record.specimen_id}, spectrum {record.spectrum_id}')
                for w, intensity in zip(axis, normalized[idx]):
                    plotted.append({'pair': f'{truth}->{prediction}', 'role': role,
                                    'spectrum_id': record.spectrum_id, 'wavenumber_cm-1': w,
                                    'l2_intensity': intensity})
            ax.set_title(f'{truth} -> {prediction} | held-out fold {fold+1}', loc='left', fontsize=13)
            ax.set_ylabel('L2-normalized intensity')
            ax.grid(alpha=.15)
            ax.legend(fontsize=8, loc='upper right')
        axes[-1].set_xlabel('Raman shift / cm$^{-1}$ (common model window only)')
        fig.savefig(out / 'error_examples.svg', metadata={'Date': None})
        plt.close(fig)
    pd.DataFrame(examples).to_csv(out / 'error_examples.csv', index=False, float_format='%.10g')
    pd.DataFrame(plotted).to_csv(out / 'error_example_spectra.csv', index=False, float_format='%.10g')
    (out / 'error_evidence.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'input_sha256'}, ensure_ascii=False))
    print(f'PASS: {len(examples)} archived errors traced to training-only nearest references; no group overlap.')


if __name__ == '__main__':
    main()

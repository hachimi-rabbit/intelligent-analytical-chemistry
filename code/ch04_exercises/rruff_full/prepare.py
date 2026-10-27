"""Audit all source-processed RRUFF records before grouped model evaluation."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
AXIS = np.arange(304., 853., 2.)
SOURCE_DOI = '10.11583/DTU.20222331.v1'


def read_source(archive):
    source_path = HERE.parent / 'rruff_real' / 'prepare_data.py'
    spec = importlib.util.spec_from_file_location('rruff_archive_format', source_path)
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    payload = Path(archive).read_bytes()
    if hashlib.sha256(payload).hexdigest() != source.SHA256:
        raise ValueError('Archive differs from the pinned DTU version')
    with ZipFile(io.BytesIO(payload)) as z:
        prefix = 'public_dataset/mineral_preprocess/'
        meta = pd.read_csv(io.BytesIO(z.read(prefix + 'excellent_unoriented_unoriented.csv')))
        meta = meta[meta.raw.eq(0)].reset_index(drop=True)
        spectra = source.NumericUnpickler(io.BytesIO(z.read(prefix + 'spectra.obj'))).load()
    if len(meta) != 5228 or len(spectra) != 5228 or not meta['index'].is_unique:
        raise ValueError('Unexpected source dimensions or record identity')
    return meta, spectra, source.SHA256


def prepare(archive, output):
    meta, spectra, source_hash = read_source(archive)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    conflicts = set(meta.groupby('id')['name'].nunique().loc[lambda s: s > 1].index)
    valid_arrays = [np.asarray(a, dtype=float) for a in spectra]
    if any(a.ndim != 2 or a.shape[1] != 2 or not np.isfinite(a).all()
           or not np.all(np.diff(a[:, 0]) > 0) for a in valid_arrays):
        raise ValueError('Source contains malformed numeric spectra; audit before modelling')
    all_features = np.array([np.interp(AXIS, a[:, 0], a[:, 1]) for a in valid_arrays])
    _, inverse, multiplicity = np.unique(all_features, axis=0, return_inverse=True, return_counts=True)
    duplicate_label_ids = set()
    duplicate_groups = []
    parent = {str(v): str(v) for v in meta.id.unique()}
    def find(v):
        while parent[v] != v:
            v = parent[v]
        return v
    for group in np.where(multiplicity > 1)[0]:
        indices = np.where(inverse == group)[0]
        for k, i in enumerate(indices):
            for j in indices[k + 1:]:
                a, b = meta.iloc[i], meta.iloc[j]
                same_source = np.array_equal(valid_arrays[i], valid_arrays[j])
                duplicate_groups.append({'spectrum_a': int(a['index']), 'spectrum_b': int(b['index']),
                                         'same_source_array': same_source,
                                         'same_label': bool(a['name'] == b['name'])})
                if a['name'] != b['name'] and same_source:
                    duplicate_label_ids.update([a.id, b.id])
                elif a['name'] == b['name']:
                    ra, rb = find(a.id), find(b.id)
                    parent[max(ra, rb)] = min(ra, rb)
    records, features = [], []
    for i, r in meta.iterrows():
        a = np.asarray(spectra[i], dtype=float)
        reasons = []
        if r.id in conflicts:
            reasons.append('conflicting_mineral_labels_for_specimen')
        if r.id in duplicate_label_ids:
            reasons.append('identical_source_spectrum_with_conflicting_labels')
        valid_shape = a.ndim == 2 and a.shape[1] == 2 and len(a) > 1
        numeric_ok = valid_shape and np.isfinite(a).all()
        lo = float(a[0, 0]) if numeric_ok else None
        hi = float(a[-1, 0]) if numeric_ok else None
        if not numeric_ok:
            reasons.append('invalid_numeric_spectrum')
        elif not np.all(np.diff(a[:, 0]) > 0):
            reasons.append('non_increasing_axis')
        elif lo > AXIS[0] or hi < AXIS[-1]:
            reasons.append('does_not_cover_304_852')
        x = None
        if not reasons:
            x = np.interp(AXIS, a[:, 0], a[:, 1])
            if np.linalg.norm(x) == 0:
                reasons.append('zero_spectrum')
        row = {'spectrum_id': str(int(r['index'])), 'specimen_id': r.id,
               'mineral': r['name'], 'validation_group': find(r.id), 'laser_nm': r.laser, 'source_list_index': i,
               'source_filename': r.full_name, 'points': len(a), 'axis_min': lo, 'axis_max': hi,
               'status': 'excluded' if reasons else 'usable', 'reason': ';'.join(reasons),
               'matrix_row': -1 if reasons else len(features)}
        records.append(row)
        if not reasons:
            features.append(x)
    frame = pd.DataFrame(records)
    frame.to_csv(out / 'manifest.csv', index=False)
    X = np.array(features)
    np.savez_compressed(out / 'features.npz', X=X, axis=AXIS)
    valid = frame[frame.status.eq('usable')]
    counts = valid.groupby('mineral').agg(spectra=('spectrum_id', 'size'), specimens=('specimen_id', 'nunique'), validation_groups=('validation_group', 'nunique'))
    counts['eligible_for_group_validation'] = counts.validation_groups.ge(2)
    counts.to_csv(out / 'class_counts.csv')
    result = {'source_doi': SOURCE_DOI, 'source_archive_sha256': source_hash,
              'download_url': 'https://ndownloader.figshare.com/files/36144495',
              'license': 'CC BY 4.0', 'source_spectra': len(frame),
              'source_specimens': int(frame.specimen_id.nunique()), 'source_classes': int(frame.mineral.nunique()),
              'usable_spectra': len(valid), 'usable_specimens': int(valid.specimen_id.nunique()),
              'usable_classes': len(counts), 'usable_validation_groups': int(valid.validation_group.nunique()),
              'duplicate_pairs': duplicate_groups, 'excluded_records': frame[frame.status.eq('excluded')].to_dict('records'),
              'axis': [304, 852, 2], 'selection': 'All raw==0 source-processed records; no mineral selection or score-based filtering.',
              'processing': 'Linear interpolation on fixed 275-point common-coverage grid; no extrapolation. Per-spectrum L2 and learned transforms are applied by the model pipeline.',
              'limits': ['Source-processed measured spectra, not newly collected raw detector signals.',
                         'One RRUFF ID is a grouping proxy, not evidence of independent parent rock or locality.',
                         'Laser wavelength does not identify a spectrometer.',
                         'The 304–852 cm-1 common interval discards peaks outside this window; scope differs from the three-class example.']}
    (out / 'provenance.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'excluded_records'}, indent=2))
    print('Exclusions:', frame.reason.value_counts().to_dict())


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, default=HERE / 'cache/public_dataset.zip')
    p.add_argument('--output', type=Path, default=HERE / 'data')
    a = p.parse_args()
    prepare(a.archive, a.output)

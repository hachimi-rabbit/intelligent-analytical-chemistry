"""Recover the attributed three-mineral subset from DTU's fixed public archive."""
import argparse
import hashlib
import io
import json
import pickle
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
URL = 'https://ndownloader.figshare.com/files/36144495'
SHA256 = '90f029cda4380f74d7f51b0295532e68cf196b1de8afa3c6a9dd225f9bad398f'
MD5 = 'f3280bc15f1739baf7d243c4835ab2d4'
CLASSES = ['Quartz', 'Calcite', 'Gypsum']


class NumericUnpickler(pickle.Unpickler):
    """Only the three NumPy reconstruction globals observed in the fixed archive."""
    def find_class(self, module, name):
        if (module, name) not in {('numpy', 'ndarray'), ('numpy', 'dtype'),
                                 ('numpy.core.multiarray', '_reconstruct')}:
            raise pickle.UnpicklingError(f'Unexpected pickle global: {module}.{name}')
        return super().find_class(module, name)


def prepare(archive, output):
    payload = Path(archive).read_bytes()
    if hashlib.sha256(payload).hexdigest() != SHA256:
        raise ValueError('Archive SHA-256 differs from the audited DTU version')
    with ZipFile(io.BytesIO(payload)) as z:
        prefix = 'public_dataset/mineral_preprocess/'
        csv_name = prefix + 'excellent_unoriented_unoriented.csv'
        meta = pd.read_csv(io.BytesIO(z.read(csv_name)))
        # Match the author's prepare_data.py: filter raw==0 BEFORE list indexing.
        meta = meta[meta.raw.eq(0)].reset_index(drop=True)
        spectra = NumericUnpickler(io.BytesIO(z.read(prefix + 'spectra.obj'))).load()
        if len(meta) != 5228 or len(spectra) != len(meta):
            raise ValueError('Metadata/spectrum alignment changed')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records, arrays = [], {}
    for source_index, row in meta[meta.name.isin(CLASSES)].iterrows():
        spectrum = np.asarray(spectra[source_index], dtype=np.float64)
        if spectrum.ndim != 2 or spectrum.shape[1] != 2 or not np.isfinite(spectrum).all():
            raise ValueError(f'Invalid measured spectrum at {source_index}')
        if not np.all(np.diff(spectrum[:, 0]) > 0):
            raise ValueError('Wavenumbers must be strictly increasing')
        if spectrum[:, 0].min() > 200 or spectrum[:, 0].max() < 1200:
            raise ValueError('Measured spectrum does not cover the fixed interval')
        record_id = str(int(row['index']))
        arrays['s' + record_id] = spectrum
        records.append({'spectrum_id': record_id, 'specimen_id': row.id,
                        'mineral': row['name'], 'laser_nm': int(row.laser),
                        'source_filename': row.full_name, 'source_list_index': source_index,
                        'source_state': 'RRUFF processed; not raw detector intensity',
                        'source_record_url': 'https://rruff.info/' + row.id,
                        'points': len(spectrum),
                        'numeric_sha256': hashlib.sha256(spectrum.astype('<f8').tobytes()).hexdigest()})
    frame = pd.DataFrame(records)
    if len(frame) != 52 or frame.specimen_id.nunique() != 22 or not frame.spectrum_id.is_unique:
        raise ValueError('Unexpected subset membership')
    frame.to_csv(output / 'manifest.csv', index=False)
    np.savez_compressed(output / 'measured_processed_spectra.npz', **arrays)
    provenance = {
        'data_status': 'MEASURED RAMAN SPECTRA; SOURCE-PROCESSED; NOT SIMULATED',
        'dataset_doi': '10.11583/DTU.20222331.v1', 'download_url': URL,
        'license': 'CC BY 4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'archive_sha256': SHA256, 'archive_md5': MD5,
        'authors': ['Bo Li', 'Mikkel N. Schmidt', 'Tommy S. Alstrøm'],
        'source_publication': 'https://doi.org/10.1039/D2AN00403H',
        'original_database': 'https://www.rruff.net/',
        'original_database_reference': 'https://doi.org/10.1515/9783110417104-003',
        'mapping_reference': 'https://github.com/lyn1874/raman_spectra_matching_with_contrastive_learning/blob/main/data/prepare_data.py',
        'archive_members': [csv_name, prefix + 'spectra.obj'],
        'selection': 'All Quartz, Calcite and Gypsum records after raw==0 filter; source order preserved.',
        'changes': 'Subset selected and converted to CSV + numeric NPZ. Original archived coordinate/intensity pairs preserved; no generated spectra.',
        'n_spectra': 52, 'n_specimens': 22,
        'limits': ['Gypsum has only two RRUFF IDs.', 'RRUFF IDs are grouping proxies; shared origin/parent-rock dependencies are not resolved.',
                   'Laser wavelength does not identify a spectrometer.', 'Author archive is a historical RRUFF derivative, not a current complete RRUFF export.']}
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(frame.groupby('mineral').agg(spectra=('spectrum_id', 'size'), specimens=('specimen_id', 'nunique')))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, help='Existing public_dataset.zip; otherwise download it')
    p.add_argument('--output', type=Path, default=HERE / 'data')
    args = p.parse_args()
    archive = args.archive or HERE / 'cache/public_dataset.zip'
    if not args.archive and not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        temporary = archive.with_suffix('.part')
        with urlopen(URL, timeout=60) as response, temporary.open('wb') as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != SHA256:
            raise ValueError('Downloaded archive failed checksum')
        temporary.replace(archive)
    prepare(archive, args.output)


if __name__ == '__main__':
    main()

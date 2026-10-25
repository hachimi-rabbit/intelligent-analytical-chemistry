# Data attribution and modifications

The bundled spectra are **measured Raman spectra processed by the source**, not synthetic spectra.

**Redistributed source:** Bo Li, Mikkel N. Schmidt, Tommy S. Alstrøm. *Datasets for replicating the paper “Raman Spectrum Matching with Contrastive Representation Learning”*, version 1. Technical University of Denmark (2022). https://doi.org/10.11583/DTU.20222331.v1 . Licensed under **Creative Commons Attribution 4.0 International (CC BY 4.0)**: https://creativecommons.org/licenses/by/4.0/ . The source authors do not endorse this project.

**Associated paper:** Li, B.; Schmidt, M. N.; Alstrøm, T. S. *Raman spectrum matching with contrastive representation learning*. Analyst **147**, 2238–2246 (2022). https://doi.org/10.1039/D2AN00403H . We use its deposited data and documented metadata mapping; we do not reproduce its contrastive-learning method or its published benchmark.

**Original database:** RRUFF, https://www.rruff.net/ . Lafuente, B.; Downs, R. T.; Yang, H.; Stone, N. *The power of databases: the RRUFF project*. In *Highlights in Mineralogical Crystallography*, pp. 1–30. https://doi.org/10.1515/9783110417104-003 . Original specimen identifiers and record links are retained in `data/manifest.csv`.

**Our changes:** from the deposited `public_dataset/mineral_preprocess` files, filter the metadata to `raw == 0` and reset its index, following the source authors' mapping code. Select all records labeled Quartz, Calcite or Gypsum (52 spectra, 22 RRUFF IDs). Convert the metadata to CSV and paired numeric arrays to NPZ. Preserve archived coordinates and intensities, with numeric checksums. For derived modeling/display only, interpolate to 200–1200 cm⁻¹ in 2 cm⁻¹ steps and normalize each spectrum by its L2 norm. No new measured observations are claimed. The full source ZIP is not redistributed here.

Author mapping: https://github.com/lyn1874/raman_spectra_matching_with_contrastive_learning/blob/main/data/prepare_data.py . Fixed source ZIP, version, checksum and machine-readable changes: `data/provenance.json`. The CC BY 4.0 attribution and source notice accompany these data regardless of the code license used elsewhere in this repository.

"""G04: repeated Raman spectra, specimen leakage and instrument shift.

All spectra are generated teaching examples, NOT measurements, RRUFF data,
or an authoritative table of Raman peak assignments. This is a fixed teaching
benchmark, not a prospectively registered experimental study.

Run: python exercise.py [--output PATH]
Default output is the outputs directory next to this script.
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.ndimage import gaussian_filter1d
import sklearn
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


SEED = 2026
N_FOLDS = 4
CLASSES = ["Quartz", "Calcite", "Gypsum"]
LABELS = np.arange(len(CLASSES))
# Deliberately rounded, simplified teaching templates, not reference peak data.
TEMPLATES = {
    "Quartz": [(210, 0.25), (355, 0.12), (465, 1.00), (805, 0.18), (1080, 0.12)],
    "Calcite": [(285, 0.30), (710, 0.35), (1085, 1.00)],
    "Gypsum": [(415, 0.18), (495, 0.22), (620, 0.25), (670, 0.22),
               (1005, 1.00), (1135, 0.15)],
}
CONFIG = {
    "data_status": "SYNTHETIC TEACHING DATA; NOT EXPERIMENTAL SPECTRA",
    "seed": SEED,
    "specimens_per_class": 30,
    "development_specimens_per_class": 24,
    "holdout_specimens_per_class": 6,
    "scans_per_specimen_per_instrument": 3,
    "wavenumber_min_cm-1": 200,
    "wavenumber_max_cm-1": 1400,
    "wavenumber_step_cm-1": 2,
    "template_peak_centers_are": "rounded schematic parameters, not validated peak assignments",
    "template_peaks_center_and_amplitude": TEMPLATES,
    "template_peak_sigma_cm-1": 4.0,
    "specimen_peak_shift_sd_cm-1": 0.9,
    "specimen_peak_width_multiplier_range": [0.8, 1.3],
    "specimen_peak_amplitude_lognormal_sigma": 0.25,
    "specimen_fingerprint_bumps": 12,
    "specimen_fingerprint_bump_sigma_range_cm-1": [25.0, 90.0],
    "specimen_fingerprint_bump_amplitude_sd": 0.14,
    "specimen_background_uniform_range": [0.03, 0.18],
    "instrument_A": {"shift_cm-1": 0.0, "extra_gaussian_sigma_bins": 0.7,
                     "response_slope": 0.0, "added_background": [0.0, 0.0, 0.0],
                     "noise_sd": 0.008},
    "instrument_B": {"shift_cm-1": 5.0, "extra_gaussian_sigma_bins": 3.0,
                     "response_slope": 0.25, "added_background": [0.22, 0.14, 0.06],
                     "noise_sd": 0.016},
    "scan_gain_sd": 0.015,
    "negative_control_seed": SEED + 1,
    "cv_folds": N_FOLDS,
    "hyperparameter_policy": "fixed, no grid search or result-driven adjustment",
    "vote_tie_policy": "lowest encoded class among tied classes (Quartz, Calcite, Gypsum order)",
}


def generate_data(seed=SEED):
    """Keep a specimen's latent fingerprint shared across instruments/scans."""
    rng = np.random.default_rng(seed)
    axis = np.arange(200.0, 1400.0 + 2.0, 2.0)
    z = (axis - axis.min()) / np.ptp(axis)
    rows, spectra, specimen_records = [], [], []
    for label, mineral in enumerate(CLASSES):
        # Split physical specimens before generating instrument observations.
        development_numbers = set(rng.permutation(30)[:24].tolist())
        for number in range(30):
            specimen = f"{mineral[:3].upper()}_{number + 1:02d}"
            partition = "development" if number in development_numbers else "holdout"
            shift = rng.normal(0.0, 0.9)
            width_factor = rng.uniform(0.8, 1.3)
            latent = np.zeros_like(axis)
            for center, amplitude in TEMPLATES[mineral]:
                peak_amp = amplitude * rng.lognormal(0.0, 0.25)
                latent += peak_amp * np.exp(-0.5 * ((axis - center - shift) /
                                                   (4.0 * width_factor)) ** 2)
            # These smooth, specimen-specific nuisance features are intentionally
            # persistent across technical replicates. They are independent of y.
            fingerprint = np.zeros_like(axis)
            for _ in range(12):
                center = rng.uniform(axis.min(), axis.max())
                width = rng.uniform(25.0, 90.0)
                amplitude = rng.normal(0.0, 0.14)
                fingerprint += amplitude * np.exp(-0.5 * ((axis - center) / width) ** 2)
            background = rng.uniform(0.03, 0.18)
            latent = latent + fingerprint + background
            # Raman detector intensity is nonnegative before independent noise.
            latent -= min(float(latent.min()), 0.0)
            specimen_records.append({
                "specimen_id": specimen, "mineral": mineral, "class_id": label,
                "partition": partition, "specimen_peak_shift_cm-1": shift,
                "specimen_peak_width_multiplier": width_factor,
                "specimen_background_level": background,
            })
            for instrument in ["A", "B"]:
                spec = CONFIG[f"instrument_{instrument}"]
                shifted = np.interp(axis - spec["shift_cm-1"], axis, latent)
                signal = gaussian_filter1d(shifted, spec["extra_gaussian_sigma_bins"])
                b0, b1, b2 = spec["added_background"]
                signal = signal * (1.0 + spec["response_slope"] * z) + b0 + b1 * z + b2 * z**2
                role = ("development_A" if instrument == "A" else "unused_development_B") \
                    if partition == "development" else f"holdout_{instrument}"
                for scan in range(1, 4):
                    observed = signal * rng.normal(1.0, CONFIG["scan_gain_sd"])
                    observed += rng.normal(0.0, spec["noise_sd"], len(axis))
                    rows.append({
                        "row_id": f"{specimen}_{instrument}_{scan}",
                        "specimen_id": specimen, "mineral": mineral,
                        "class_id": label, "instrument": instrument,
                        "scan_id": scan, "partition": partition, "analysis_role": role,
                    })
                    spectra.append(observed)
    metadata = pd.DataFrame(rows)
    specimen_metadata = pd.DataFrame(specimen_records)
    X = np.asarray(spectra, dtype=float)
    assert X.shape == (540, 601)
    assert metadata.row_id.is_unique and specimen_metadata.specimen_id.is_unique
    assert np.isfinite(X).all()
    assert metadata.groupby(["specimen_id", "instrument"]).size().eq(3).all()
    assert metadata.groupby("specimen_id")["class_id"].nunique().eq(1).all()
    for mineral in CLASSES:
        subset = specimen_metadata[specimen_metadata.mineral == mineral]
        assert len(subset) == 30
        assert subset.partition.value_counts().to_dict() == {"development": 24, "holdout": 6}
    return axis, X, metadata, specimen_metadata


def make_models():
    # Every transform that learns across observations lives inside the Pipeline.
    # Insertion order is the prespecified model tie-break order.
    return {
        "Dummy": Pipeline([("classifier", DummyClassifier(strategy="most_frequent"))]),
        "1NN": Pipeline([("scale", StandardScaler()),
                         ("classifier", KNeighborsClassifier(n_neighbors=1))]),
        "PCA_LR": Pipeline([("scale", StandardScaler()),
                            ("pca", PCA(n_components=8, svd_solver="full")),
                            ("classifier", LogisticRegression(C=1.0, max_iter=3000,
                                                              random_state=SEED))]),
        "RBF_SVC": Pipeline([("scale", StandardScaler()),
                             # The default disables internal probability calibration.
                             ("classifier", SVC(C=10.0, gamma="scale"))]),
    }


def score(y_true, y_pred, label_names=None):
    names = CLASSES if label_names is None else label_names
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)
    totals = matrix.sum(axis=1)
    recalls = np.divide(np.diag(matrix), totals, out=np.zeros(3, dtype=float), where=totals != 0)
    return {
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=LABELS, average="macro",
                                  zero_division=0)),
        "confusion_matrix": matrix.tolist(),
        "recall_per_class": {name: float(value) for name, value in zip(names, recalls)},
    }


def sample_votes(row_predictions):
    records = []
    for specimen, part in row_predictions.groupby("specimen_id", sort=True):
        assert part.true_class.nunique() == 1
        votes = np.bincount(part.predicted_class.to_numpy(dtype=int), minlength=len(CLASSES))
        winner = int(np.argmax(votes))
        records.append({
            "specimen_id": specimen,
            "true_class": int(part.true_class.iloc[0]), "predicted_class": winner,
            "true_label": CLASSES[int(part.true_class.iloc[0])],
            "predicted_label": CLASSES[winner], "n_scans": len(part),
            "vote_tie": bool(np.sum(votes == votes.max()) > 1),
            "vote_Quartz": int(votes[0]), "vote_Calcite": int(votes[1]),
            "vote_Gypsum": int(votes[2]),
            "folds": ",".join(map(str, sorted(part.fold.unique()))) if "fold" in part else "final",
        })
    return pd.DataFrame(records)


def make_splits(y, groups, strategy):
    if strategy == "row_random":
        splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    elif strategy == "specimen_group":
        splitter = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    else:
        raise ValueError(strategy)
    return list(splitter.split(np.zeros((len(y), 1)), y, groups if strategy == "specimen_group" else None))


def evaluate_oof(model, X, y, metadata, splits, require_disjoint, label_names=None):
    prediction = np.full(len(y), -1, dtype=int)
    fold_id = np.full(len(y), -1, dtype=int)
    seen = np.zeros(len(y), dtype=int)
    audit = []
    for fold, (train, validation) in enumerate(splits, start=1):
        train_groups = set(metadata.iloc[train].specimen_id)
        validation_groups = set(metadata.iloc[validation].specimen_id)
        shared = train_groups & validation_groups
        assert not (set(train) & set(validation))
        if require_disjoint:
            assert not shared, "Physical specimen leakage in the grouped evaluation"
        assert set(y[train]) == set(LABELS) and set(y[validation]) == set(LABELS)
        estimator = clone(model).fit(X[train], y[train])
        prediction[validation] = estimator.predict(X[validation])
        fold_id[validation] = fold
        seen[validation] += 1
        audit.append({
            "fold": fold, "train_rows": len(train), "validation_rows": len(validation),
            "train_specimens": len(train_groups), "validation_specimens": len(validation_groups),
            "shared_specimen_count": len(shared), "shared_specimen_ids": sorted(shared),
            "train_class_counts": np.bincount(y[train], minlength=3).tolist(),
            "validation_class_counts": np.bincount(y[validation], minlength=3).tolist(),
        })
    assert np.all(seen == 1) and np.all(prediction >= 0)
    rows = metadata[["row_id", "specimen_id", "instrument", "scan_id"]].copy()
    rows["true_class"] = y
    rows["predicted_class"] = prediction
    rows["fold"] = fold_id
    samples = sample_votes(rows)
    assert samples.n_scans.eq(3).all()
    return rows, samples, {
        "row": score(y, prediction, label_names),
        "sample": score(samples.true_class, samples.predicted_class, label_names),
    }, audit


def save_figure(fig, output, name):
    fig.savefig(output / f"{name}.png", dpi=180, bbox_inches="tight")
    fig.savefig(output / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def plot_outputs(axis, X, metadata, comparison, external, negative, output):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none"})
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    for ax, mineral in zip(axes, CLASSES):
        sid = metadata.loc[(metadata.mineral == mineral) & (metadata.partition == "holdout"),
                           "specimen_id"].iloc[0]
        for instrument, color in [("A", "#167d9a"), ("B", "#e7853e")]:
            mask = (metadata.specimen_id == sid) & (metadata.instrument == instrument)
            values = X[mask.to_numpy()]
            for trace in values:
                ax.plot(axis, trace, color=color, alpha=0.20, lw=0.7)
            ax.plot(axis, values.mean(axis=0), color=color, lw=1.1, label=f"Instrument {instrument}")
        ax.set_ylabel("Intensity (a.u.)")
        ax.set_title(f"{mineral}: paired holdout specimen {sid}", loc="left", fontsize=11)
        ax.set_ylim(top=ax.get_ylim()[1] * 1.23)
        ax.legend(loc="upper right", ncol=2)
    axes[-1].set_xlabel(r"Schematic Raman shift (cm$^{-1}$)")
    fig.suptitle("SYNTHETIC TEACHING SPECTRA: three scans per instrument", fontsize=13)
    save_figure(fig, output, "synthetic_spectra")

    model_names = list(make_models())
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    x = np.arange(len(model_names))
    for j, (strategy, label, color) in enumerate([
        ("row_random", "Row-random CV (leaky)", "#e7853e"),
        ("specimen_group", "Specimen-group CV", "#167d9a"),
    ]):
        values = comparison[comparison.cv_strategy == strategy].set_index("model").loc[model_names,
                                                                                         "sample_macro_f1"]
        axes[0].bar(x + (j - 0.5) * 0.36, values, 0.36, label=label, color=color)
    axes[0].set_xticks(x, model_names)
    axes[0].set_ylim(0, 1.08)
    axes[0].set_ylabel("Specimen-vote macro-F1")
    axes[0].set_title("Development A: fixed models, 4-fold OOF")
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8)
    nc_values = [negative[s]["sample"]["macro_f1"] for s in ["row_random", "specimen_group"]]
    bars = axes[1].bar(["Row-random", "Specimen-group"], nc_values, color=["#e7853e", "#167d9a"])
    axes[1].bar_label(bars, fmt="%.3f", padding=3)
    axes[1].set_ylim(0, 1.13)
    axes[1].set_ylabel("Specimen-vote macro-F1")
    axes[1].set_title("1NN negative control: shuffled specimen labels")
    fig.suptitle("SYNTHETIC RESULTS | random labels are shared by repeated scans", fontsize=13)
    save_figure(fig, output, "cv_and_negative_control")

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), constrained_layout=True)
    for ax, instrument in zip(axes, ["A", "B"]):
        result = external[instrument]["sample"]
        matrix = np.asarray(result["confusion_matrix"])
        ax.imshow(matrix, vmin=0, vmax=6, cmap="Blues")
        for row in range(3):
            for col in range(3):
                ax.text(col, row, str(matrix[row, col]), ha="center", va="center",
                        color="white" if matrix[row, col] > 3 else "#16314b", fontsize=16)
        ax.set_xticks(range(3), CLASSES)
        ax.set_yticks(range(3), CLASSES)
        ax.set_xlabel("Predicted mineral")
        ax.set_ylabel("True mineral")
        ax.set_title(f"Instrument {instrument}: 18 unseen specimens\nmacro-F1 = {result['macro_f1']:.3f}")
    fig.suptitle(f"Frozen model: {external['selected_model']} | identical held-out specimens on A/B")
    save_figure(fig, output, "paired_holdout_confusion")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "outputs")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    axis, X, metadata, specimen_metadata = generate_data()
    development_mask = metadata.analysis_role.eq("development_A").to_numpy()
    development = metadata.loc[development_mask].reset_index(drop=True)
    X_dev = X[development_mask]
    y_dev = development.class_id.to_numpy()
    groups = development.specimen_id.to_numpy()
    assert X_dev.shape[0] == 216 and len(set(groups)) == 72
    development_ids = set(groups)
    holdout_ids = set(metadata.loc[metadata.partition.eq("holdout"), "specimen_id"])
    assert len(holdout_ids) == 18 and not (development_ids & holdout_ids)
    assert metadata.analysis_role.value_counts().to_dict() == {
        "development_A": 216, "unused_development_B": 216, "holdout_A": 54, "holdout_B": 54}

    models = make_models()
    comparisons, all_rows, all_samples = [], [], []
    cv_results, split_audits = {}, {}
    for strategy in ["row_random", "specimen_group"]:
        splits = make_splits(y_dev, groups, strategy)
        cv_results[strategy] = {}
        for name, model in models.items():
            rows, samples, result, audit = evaluate_oof(
                model, X_dev, y_dev, development, splits, strategy == "specimen_group")
            rows.insert(0, "model", name)
            rows.insert(1, "cv_strategy", strategy)
            samples.insert(0, "model", name)
            samples.insert(1, "cv_strategy", strategy)
            all_rows.append(rows)
            all_samples.append(samples)
            cv_results[strategy][name] = result
            comparisons.append({
                "model": name, "cv_strategy": strategy,
                "n_rows": len(rows), "n_specimens": len(samples),
                "row_balanced_accuracy": result["row"]["balanced_accuracy"],
                "row_macro_f1": result["row"]["macro_f1"],
                "sample_balanced_accuracy": result["sample"]["balanced_accuracy"],
                "sample_macro_f1": result["sample"]["macro_f1"],
                "sample_vote_ties": int(samples.vote_tie.sum()),
            })
            split_audits[strategy] = audit
    assert all(fold["shared_specimen_count"] == 0 for fold in split_audits["specimen_group"])
    assert any(fold["shared_specimen_count"] > 0 for fold in split_audits["row_random"])
    comparison = pd.DataFrame(comparisons)
    # This selection runs BEFORE the held-out A/B predictions. Model order breaks
    # an exact macro-F1 tie; neither random CV nor holdout scores select the model.
    selected_name = max(models, key=lambda name: cv_results["specimen_group"][name]["sample"]["macro_f1"])
    frozen = clone(models[selected_name]).fit(X_dev, y_dev)
    external = {"selected_model": selected_name}
    external_rows, external_samples = [], []
    for instrument in ["A", "B"]:
        mask = metadata.analysis_role.eq(f"holdout_{instrument}").to_numpy()
        part = metadata.loc[mask].reset_index(drop=True)
        assert len(part) == 54 and set(part.specimen_id) == holdout_ids
        # A single final predict call for each held-out instrument.
        predicted = frozen.predict(X[mask])
        rows = part[["row_id", "specimen_id", "instrument", "scan_id"]].copy()
        rows["true_class"] = part.class_id
        rows["predicted_class"] = predicted
        samples = sample_votes(rows)
        samples.insert(0, "instrument", instrument)
        external_rows.append(rows)
        external_samples.append(samples)
        external[instrument] = {
            "n_rows": len(rows), "n_specimens": len(samples),
            "row": score(rows.true_class, rows.predicted_class),
            "sample": score(samples.true_class, samples.predicted_class),
            "sample_vote_ties": int(samples.vote_tie.sum()),
        }
    a_ids = external_samples[0].specimen_id.tolist()
    b_ids = external_samples[1].specimen_id.tolist()
    assert a_ids == b_ids

    # Identity-memory negative control: random targets are generated once per
    # specimen, then inherited by all its scans. No holdout is involved.
    nc_rng = np.random.default_rng(SEED + 1)
    unique_ids = np.array(sorted(development_ids))
    random_specimen_labels = nc_rng.permutation(np.tile(LABELS, len(unique_ids) // 3))
    random_map = dict(zip(unique_ids, random_specimen_labels))
    y_random = np.array([random_map[sid] for sid in groups], dtype=int)
    negative, nc_rows, nc_samples, nc_audits = {}, [], [], {}
    for strategy in ["row_random", "specimen_group"]:
        splits = make_splits(y_random, groups, strategy)
        rows, samples, result, audit = evaluate_oof(
            models["1NN"], X_dev, y_random, development, splits, strategy == "specimen_group",
            label_names=["random_0", "random_1", "random_2"])
        rows.insert(0, "cv_strategy", strategy)
        samples.insert(0, "cv_strategy", strategy)
        # Avoid confusing artificial random targets with mineral identities.
        for column in ["true_label", "predicted_label"]:
            samples[column] = samples[column].map(dict(zip(CLASSES, ["random_0", "random_1", "random_2"])))
        samples = samples.rename(columns={f"vote_{c}": f"vote_random_{i}" for i, c in enumerate(CLASSES)})
        nc_rows.append(rows)
        nc_samples.append(samples)
        negative[strategy] = result
        nc_audits[strategy] = audit
    assert all(fold["shared_specimen_count"] == 0 for fold in nc_audits["specimen_group"])

    versions = {"python": platform.python_version(), "numpy": np.__version__,
                "pandas": pd.__version__, "scipy": scipy.__version__,
                "scikit-learn": sklearn.__version__, "matplotlib": matplotlib.__version__}
    metrics = {
        "data_status": CONFIG["data_status"], "seed": SEED, "versions": versions,
        "class_order": CLASSES, "independent_unit": "physical specimen",
        "total_specimens": 90, "total_rows": 540,
        "development_specimens": 72, "development_rows_A": 216,
        "unused_development_rows_B": 216, "holdout_specimens": 18,
        "cv_folds": N_FOLDS, "cv_results": cv_results,
        "selection_rule": "highest specimen-group OOF specimen-vote macro-F1; ties use Dummy, 1NN, PCA_LR, RBF_SVC order",
        "vote_tie_policy": CONFIG["vote_tie_policy"],
        "selected_model": selected_name, "paired_holdout": external,
        "negative_control": negative,
        "scientific_checks": {"development_holdout_specimen_intersection": 0,
                              "all_grouped_cv_specimen_intersections": 0,
                              "paired_A_B_holdout_specimens_identical": True,
                              "all_rows_have_one_oof_prediction_per_model_strategy": True,
                              "B_development_rows_used_in_model_fitting": 0,
                              "hyperparameters_tuned_on_holdout": False},
        "limits": ["Synthetic closed-set teaching data; not evidence of analytical validity.",
                   "Technical replicates do not increase the independent sample count.",
                   "Two instruments and 18 held-out specimens do not represent all instruments or mineral matrices.",
                   "No confidence interval is inferred from correlated scan rows.",
                   "An absent positive-task score gap does not validate a leaky split.",
                   "The random-label control measures identity memorization; its finite-sample score need not be exactly one third."]}
    metadata.to_csv(output / "metadata.csv", index=False, encoding="utf-8-sig")
    specimen_metadata.to_csv(output / "specimen_metadata.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"feature_index": range(len(axis)), "wavenumber_cm-1": axis}).to_csv(
        output / "wavenumbers.csv", index=False)
    wide = pd.DataFrame(X, columns=[f"shift_{int(v):04d}" for v in axis])
    wide.insert(0, "row_id", metadata.row_id)
    wide.to_csv(output / "spectra.csv", index=False, float_format="%.8g")
    np.savez_compressed(output / "spectra.npz", X=X, wavenumber=axis,
                        row_id=metadata.row_id.to_numpy(dtype=str))
    pd.concat(all_rows, ignore_index=True).to_csv(output / "row_oof.csv", index=False)
    pd.concat(all_samples, ignore_index=True).to_csv(output / "sample_oof.csv", index=False)
    comparison.to_csv(output / "model_comparison.csv", index=False)
    pd.concat(external_rows, ignore_index=True).to_csv(output / "holdout_row_predictions.csv", index=False)
    pd.concat(external_samples, ignore_index=True).to_csv(output / "holdout_sample_predictions.csv", index=False)
    pd.concat(nc_rows, ignore_index=True).to_csv(output / "negative_control_row_oof.csv", index=False)
    pd.concat(nc_samples, ignore_index=True).to_csv(output / "negative_control_sample_oof.csv", index=False)
    pd.DataFrame({"specimen_id": unique_ids, "random_class": random_specimen_labels}).to_csv(
        output / "negative_control_labels.csv", index=False)
    for filename, value in [("metrics.json", metrics), ("simulation_config.json", CONFIG),
                            ("split_audit.json", {"mineral_task": split_audits, "negative_control": nc_audits})]:
        (output / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    dictionary = """G04 Raman teaching dataset: SYNTHETIC, NOT EXPERIMENTAL.

metadata.csv: one row per scan, 540 rows. row_id is unique; specimen_id is
the independent physical-specimen group; mineral/class_id is the teaching
target (0 Quartz, 1 Calcite, 2 Gypsum); instrument is A/B; scan_id is 1..3;
partition is development/holdout; analysis_role controls eligibility.
development_A: 72 specimens/216 scans used for development.
unused_development_B: 216 scans explicitly excluded from all model fitting,
cross-validation, model selection and final evaluation.
holdout_A and holdout_B: the SAME 18 previously unseen specimens, 54 scans
per instrument. No development specimen occurs in either holdout.

specimen_metadata.csv: 90 independent units and selected generation parameters.
spectra.csv: row_id followed by 601 intensity features in arbitrary units.
shift_0200 ... shift_1400 are schematic Raman-shift coordinates (cm^-1), step 2.
wavenumbers.csv: numeric coordinate mapping. spectra.npz stores the same X,
wavenumber and row_id arrays without CSV rounding (load with allow_pickle=False).
Intensity values include independent detector noise and may be slightly negative.

row_oof.csv: out-of-fold predictions; one row for each development scan,
model and CV strategy (4 models x 2 strategies x 216 rows).
row_random is a deliberately leaky spectrum-row split. specimen_group keeps
all scans from a specimen together. Each scan is predicted exactly once.
sample_oof.csv: votes of the three OOF scan predictions for each specimen,
model and strategy. For row_random these predictions may come from different
fitted folds (recorded in folds); hence the aggregation does not cure leakage.
vote_tie means tied vote counts. Prespecified tie rule selects the lowest
encoded class among ties. No probability calibration is claimed.
model_comparison.csv: pooled OOF row and specimen scores, not fold means.
Models are selected only by specimen-group specimen-level macro-F1.

holdout_*_predictions.csv: predictions from the ONE selected, frozen model,
fit on all development A rows. A and B use identical new physical specimens.
negative_control_labels.csv: a balanced random label permutation across the
72 development specimens, inherited by their repeated scans, seed 2027.
negative_control_*_oof.csv: 1NN only; classes are artificial random targets.
The control is independent of model selection and uses no held-out data.

metrics.json: actual computed scores, selected model, versions and limitations.
split_audit.json: row/specimen/class counts and specimen intersections by fold.
simulation_config.json: all fixed generation settings and schematic templates.
The peak templates are rounded teaching parameters, not authoritative peak
positions, measured reference spectra, or evidence of peak assignments.
Specimen fingerprints/backgrounds are persistent simulated nuisance features;
instrument B applies a common shift, extra broadening, response and background.

Figures are exported as both PNG and editable SVG with English annotations.
All spectra/figures/results describe this simulation only. Technical repeats
are correlated. External independent sample size is 18, not 54 or 108.
The negative-control finite-sample macro-F1 need not equal exactly 1/3.
"""
    (output / "data_dictionary.txt").write_text(dictionary, encoding="utf-8")
    plot_outputs(axis, X, metadata, comparison, external, negative, output)
    print(json.dumps({"output": str(output), "versions": versions,
                      "selected_model": selected_name,
                      "development_comparison": comparisons,
                      "paired_holdout": external,
                      "negative_control": negative,
                      "scientific_checks": metrics["scientific_checks"]}, indent=2))


if __name__ == "__main__":
    main()

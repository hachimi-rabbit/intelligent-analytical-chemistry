"""Predeclared teaching extensions: row-wise preprocessing and repeated nulls.

All inputs are simulated. The previously viewed seed 2026 is retained as a
historical benchmark. Seeds below are a separate fixed simulation panel, not
independent evidence about real instruments. No parameter is selected on B.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.special import expit
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Normalizer
from sklearn.svm import SVC
import exercise as core

PANEL_SEEDS = [1101, 1102, 1103, 1104, 1105]
NULL_SEED = 20261023


class ArPLS(BaseEstimator, TransformerMixin):
    """Baek et al. (2015), arPLS; parameters fixed for the 2 cm^-1 grid.

    Every spectrum estimates only its own background. No population-level
    fitting or labels are used. This does not align peaks or calibrate an axis.
    """
    def __init__(self, lam=1e5, max_iter=30, tol=1e-3):
        self.lam, self.max_iter, self.tol = lam, max_iter, tol

    def fit(self, X, y=None):
        self.n_features_in_ = np.asarray(X).shape[1]
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[1] != self.n_features_in_:
            raise ValueError("Unexpected spectral matrix shape")
        n = X.shape[1]
        D = sparse.diags([np.ones(n-2), -2*np.ones(n-2), np.ones(n-2)],
                         [0, 1, 2], shape=(n-2, n), format="csc")
        penalty = self.lam * (D.T @ D)
        corrected = np.empty_like(X)
        for i, x in enumerate(X):
            w = np.ones(n)
            for _ in range(self.max_iter):
                baseline = spsolve(sparse.diags(w, format="csc") + penalty, w*x)
                d = x-baseline
                neg = d[d < 0]
                if neg.size < 2 or neg.std() < 1e-12:
                    break
                new_w = expit(-2*(d - (2*neg.std()-neg.mean()))/neg.std())
                if np.linalg.norm(w-new_w)/max(np.linalg.norm(w), 1e-12) < self.tol:
                    w = new_w
                    break
                w = new_w
            baseline = spsolve(sparse.diags(w, format="csc") + penalty, w*x)
            corrected[i] = x-baseline
        if not np.isfinite(corrected).all():
            raise ValueError("Non-finite corrected spectra")
        return corrected


def processed_model():
    return Pipeline([("baseline", ArPLS()), ("unit_norm", Normalizer()),
                     ("classifier", SVC(C=10.0, gamma="scale"))])


def run_panel():
    comparisons, predictions, selections = [], [], []
    for seed in PANEL_SEEDS:
        _, X, meta, _ = core.generate_data(seed=seed)
        mask = meta.analysis_role.eq("development_A").to_numpy()
        dev = meta.loc[mask].reset_index(drop=True)
        xd, yd, groups = X[mask], dev.class_id.to_numpy(), dev.specimen_id.to_numpy()
        splits = core.make_splits(yd, groups, "specimen_group")
        models = {"Dummy": core.make_models()["Dummy"],
                  "raw_SVC": core.make_models()["RBF_SVC"],
                  "arPLS_L2_SVC": processed_model()}
        dev_scores = {}
        fitted = {}
        for name, model in models.items():
            _, _, result, audit = core.evaluate_oof(model, xd, yd, dev, splits, True)
            assert all(f["shared_specimen_count"] == 0 for f in audit)
            dev_scores[name] = result["sample"]["macro_f1"]
            comparisons.append({"seed": seed, "model": name, "evaluation": "group_cv",
                                "macro_f1": dev_scores[name], "n_specimens": 72})
            fitted[name] = clone(model).fit(xd, yd)
        # Freeze selection before reading any A/B holdout predictions.
        winner = max(dev_scores, key=dev_scores.get)
        selections.append({"seed": seed, "selected_model": winner,
                           "selection_data": "development_A_group_cv_only"})
        for name, estimator in fitted.items():
            # Both fixed pipelines are evaluated for a paired ablation. Results
            # are reported in full, never used to choose the winner above.
            for instrument in ("A", "B"):
                hm = meta.analysis_role.eq(f"holdout_{instrument}").to_numpy()
                h = meta.loc[hm].reset_index(drop=True)
                assert set(h.specimen_id).isdisjoint(set(groups))
                rows = h[["row_id", "specimen_id", "instrument", "scan_id"]].copy()
                rows["true_class"] = h.class_id
                rows["predicted_class"] = estimator.predict(X[hm])
                samples = core.sample_votes(rows)
                samples.insert(0, "seed", seed)
                samples.insert(1, "model", name)
                samples.insert(2, "instrument", instrument)
                predictions.append(samples)
                comparisons.append({"seed": seed, "model": name,
                                    "evaluation": f"holdout_{instrument}",
                                    "macro_f1": core.score(samples.true_class, samples.predicted_class)["macro_f1"],
                                    "n_specimens": len(samples), "selected": name == winner})
    return pd.DataFrame(comparisons), pd.concat(predictions), selections


def run_nulls(n_permutations):
    _, X, meta, _ = core.generate_data()
    mask = meta.analysis_role.eq("development_A").to_numpy()
    dev = meta.loc[mask].reset_index(drop=True)
    xd = X[mask]
    groups = dev.specimen_id.to_numpy()
    ids = np.array(sorted(set(groups)))
    rng = np.random.default_rng(NULL_SEED)
    result = []
    for i in range(n_permutations):
        label_map = dict(zip(ids, rng.permutation(np.tile(core.LABELS, len(ids)//3))))
        labels = np.array([label_map[g] for g in groups])
        for strategy in ("row_random", "specimen_group"):
            splits = core.make_splits(labels, groups, strategy)
            _, _, scores, _ = core.evaluate_oof(core.make_models()["1NN"], xd, labels,
                                               dev, splits, strategy == "specimen_group")
            result.append({"permutation": i, "strategy": strategy,
                           "macro_f1": scores["sample"]["macro_f1"]})
    return pd.DataFrame(result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=Path(__file__).parent/"outputs")
    p.add_argument("--permutations", type=int, default=199)
    args = p.parse_args()
    if args.permutations < 1:
        p.error("--permutations must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    comparisons, predictions, selections = run_panel()
    nulls = run_nulls(args.permutations)
    comparisons.to_csv(args.output/"preprocessing_panel.csv", index=False)
    predictions.to_csv(args.output/"panel_sample_predictions.csv", index=False)
    nulls.to_csv(args.output/"permutation_scores.csv", index=False)
    summary = {"data_status": "SYNTHETIC TEACHING DATA ONLY", "seeds": PANEL_SEEDS,
               "selection": selections, "preprocessing": "arPLS(lam=1e5,max_iter=30,tol=1e-3), L2 normalization, SVC(C=10,gamma=scale)",
               "axis_alignment": "none; no true synthetic shift is supplied to the estimator",
               "null_seed": NULL_SEED, "permutations": args.permutations,
               "null_summary": {}, "panel_mean": [],
               "interpretation": "A fixed simulation sensitivity panel, not independent experimental validation or a prespecified clinical/statistical test. All candidates and seeds are reported. Quantiles describe null simulations, not confidence intervals for mineral identification."}
    for strategy, g in nulls.groupby("strategy"):
        summary["null_summary"][strategy] = {"mean": float(g.macro_f1.mean()),
                "q025": float(g.macro_f1.quantile(.025)), "q975": float(g.macro_f1.quantile(.975))}
    summary["panel_mean"] = comparisons.groupby(["model", "evaluation"]).macro_f1.agg(
        ["mean", "min", "max"]).reset_index().to_dict("records")
    (args.output/"extensions_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    core.plt.rcParams["svg.fonttype"] = "none"
    fig, axes = core.plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for strategy, g in nulls.groupby("strategy"):
        axes[0].hist(g.macro_f1, bins=np.linspace(0,1,26), alpha=.65, label=strategy)
    axes[0].set(xlabel="Specimen macro-F1", ylabel="Permutation count", title="Random targets: 199 label permutations" if args.permutations==199 else f"Random targets: {args.permutations} permutations")
    axes[0].legend(fontsize=8)
    for name, color in [("raw_SVC", "#9b3b36"), ("arPLS_L2_SVC", "#24577b")]:
        g=comparisons[(comparisons.model==name)&(comparisons.evaluation=="holdout_B")]
        axes[1].plot(g.seed.astype(str),g.macro_f1,"o-",label=name,color=color)
    axes[1].set(xlabel="Simulation seed",ylabel="Specimen macro-F1",ylim=(0,1.05),title="Instrument B: fixed preprocessing comparison")
    axes[1].legend(fontsize=8)
    core.save_figure(fig,args.output,"extensions")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    main()

"""Independently recompute outputs and validate isolation/invariants."""
import argparse
from itertools import product
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
import exercise as core
from extensions import ArPLS, PANEL_SEEDS
from export_interactive import DEFAULT_TARGET, build_payload, render_script


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=Path(__file__).parent/"outputs")
    p.add_argument("--interactive-data",type=Path,default=DEFAULT_TARGET)
    args=p.parse_args();o=args.output
    checks=[]
    def check(condition,name):
        if not condition:raise AssertionError(name)
        checks.append(name)
    metadata=pd.read_csv(o/"metadata.csv")
    check(len(metadata)==540 and metadata.row_id.is_unique,"540 unique scans")
    check(metadata.specimen_id.nunique()==90,"90 physical specimens")
    dev=set(metadata.loc[metadata.analysis_role.eq("development_A"),"specimen_id"])
    hold=set(metadata.loc[metadata.partition.eq("holdout"),"specimen_id"])
    check(len(dev)==72 and len(hold)==18 and not dev&hold,"development/holdout isolation")
    audit=json.loads((o/"split_audit.json").read_text(encoding="utf-8"))
    for task in ("mineral_task","negative_control"):
        check(all(f["shared_specimen_count"]==0 for f in audit[task]["specimen_group"]),task+" grouped split isolation")
    comp=pd.read_csv(o/"model_comparison.csv")
    samples=pd.read_csv(o/"sample_oof.csv")
    rows=pd.read_csv(o/"row_oof.csv")
    expected_cv=set(product(("row_random","specimen_group"),core.make_models()))
    for name,frame in (("comparison",comp),("samples",samples),("rows",rows)):
        check(set(map(tuple,frame[["cv_strategy","model"]].drop_duplicates().to_numpy()))==expected_cv,
              "complete CV coverage "+name)
    check(not comp.duplicated(["cv_strategy","model"]).any(),"unique comparison rows")
    for (strategy,model),g in samples.groupby(["cv_strategy","model"]):
        c=comp[(comp.cv_strategy==strategy)&(comp.model==model)].iloc[0]
        check(len(g)==72 and g.specimen_id.nunique()==72,f"OOF samples {strategy} {model}")
        check(np.isclose(f1_score(g.true_class,g.predicted_class,average="macro"),c.sample_macro_f1),f"F1 recomputed {strategy} {model}")
        rr=rows[(rows.cv_strategy==strategy)&(rows.model==model)]
        check(len(rr)==216 and rr.row_id.is_unique,f"OOF rows {strategy} {model}")
        if strategy=="specimen_group":check(rr.groupby("specimen_id").fold.nunique().eq(1).all(),f"one fold per specimen {model}")
    m=json.loads((o/"metrics.json").read_text(encoding="utf-8"))
    grouped=comp[comp.cv_strategy.eq("specimen_group")]
    check(grouped.loc[grouped.sample_macro_f1.idxmax(),"model"]==m["selected_model"],"model selected from grouped development only")
    hp=pd.read_csv(o/"holdout_sample_predictions.csv")
    check(set(hp[hp.instrument.eq("A")].specimen_id)==set(hp[hp.instrument.eq("B")].specimen_id)==hold,"paired holdout identity")
    for inst,g in hp.groupby("instrument"):
        check(np.isclose(f1_score(g.true_class,g.predicted_class,average="macro"),m["paired_holdout"][inst]["sample"]["macro_f1"]),f"holdout F1 recomputed {inst}")
    panel=pd.read_csv(o/"preprocessing_panel.csv")
    pp=pd.read_csv(o/"panel_sample_predictions.csv")
    models=("Dummy","raw_SVC","arPLS_L2_SVC")
    check(set(map(tuple,panel[["seed","model","evaluation"]].to_numpy()))==
          set(product(PANEL_SEEDS,models,("group_cv","holdout_A","holdout_B"))),
          "complete panel score coverage")
    check(set(map(tuple,pp[["seed","model","instrument"]].drop_duplicates().to_numpy()))==
          set(product(PANEL_SEEDS,models,("A","B"))),"complete panel prediction coverage")
    check(not pp.duplicated(["seed","model","instrument","specimen_id"]).any(),
          "unique panel specimen predictions")
    check(sorted(panel.seed.unique().tolist())==PANEL_SEEDS,"all fixed seeds retained")
    check(len(panel)==45,"all panel candidates/evaluations retained")
    for (seed,model,inst),g in pp.groupby(["seed","model","instrument"]):
        row=panel[(panel.seed==seed)&(panel.model==model)&(panel.evaluation=="holdout_"+inst)].iloc[0]
        check(len(g)==18 and np.isclose(f1_score(g.true_class,g.predicted_class,average="macro"),row.macro_f1),f"panel recomputed {seed} {model} {inst}")
    summary=json.loads((o/"extensions_summary.json").read_text(encoding="utf-8"))
    null=pd.read_csv(o/"permutation_scores.csv")
    check(null.groupby("strategy").size().eq(summary["permutations"]).all(),"all permutations retained")
    for strategy,g in null.groupby("strategy"):
        check(np.isclose(g.macro_f1.mean(),summary["null_summary"][strategy]["mean"]),"null mean "+strategy)
    # A row-wise transform must not change a spectrum when unrelated rows change.
    _,X,_,_=core.generate_data()
    transformer=ArPLS().fit(X[:3]);first=transformer.transform(X[:1])
    others=transformer.transform(np.vstack([X[:1],X[1:3]*2+20]))[:1]
    check(np.allclose(first,others,rtol=1e-10,atol=1e-10),"row-wise preprocessing independence")
    calibration=json.loads((o/"calibration.json").read_text(encoding="utf-8"))
    partitions=[set(v) for v in calibration["partition_ids"].values()]
    check(all(not a&b for i,a in enumerate(partitions) for b in partitions[i+1:]),"fit/calibration/threshold/test isolation")
    check(sum(map(len,partitions))==2400,"calibration observations covered once")
    check(args.interactive_data.read_text(encoding="utf-8")==render_script(build_payload(o)),
          "browser export matches Python results; rerun export_interactive.py if stale")
    print(json.dumps({"passed":len(checks),"checks":checks},indent=2))


if __name__=="__main__":main()

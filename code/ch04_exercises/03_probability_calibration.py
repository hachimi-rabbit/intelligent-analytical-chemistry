"""Separate fitting, calibration, threshold selection and final testing.

Synthetic independent observations; real repeated spectra require group splits
at every boundary. Run from the repository root. Output contains test metrics
for thresholds frozen using the threshold-validation set, never test labels.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.datasets import make_classification
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def run():
    X,y=make_classification(n_samples=2400,n_features=20,weights=[.88,.12],flip_y=.04,random_state=5)
    ids=np.arange(len(y))
    fitting, rest=train_test_split(ids,test_size=.4,stratify=y,random_state=3)
    calibration, rest=train_test_split(rest,test_size=.5,stratify=y[rest],random_state=4)
    threshold_set, test=train_test_split(rest,test_size=.5,stratify=y[rest],random_state=6)
    partitions={"fit":fitting,"calibrate":calibration,"threshold":threshold_set,"test":test}
    assert len(set(np.concatenate(list(partitions.values())))) == len(y)
    assert sum(map(len,partitions.values()))==len(y)
    base=make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000)).fit(X[fitting],y[fitting])
    calibrated=CalibratedClassifierCV(FrozenEstimator(base),method="sigmoid").fit(X[calibration],y[calibration])
    pv=calibrated.predict_proba(X[threshold_set])[:,1]
    frozen=[]
    for cost_fn,cost_fp in [(1,1),(8,1)]:
        grid=np.linspace(.01,.99,99)
        losses=[]
        for t in grid:
            tn,fp,fn,tp=confusion_matrix(y[threshold_set],pv>=t,labels=[0,1]).ravel()
            losses.append(int(cost_fn*fn+cost_fp*fp))
        # Tie: lowest threshold in the fixed ascending grid.
        frozen.append({"cost_fn":cost_fn,"cost_fp":cost_fp,"threshold":float(grid[np.argmin(losses)]),
                       "validation_cost":int(min(losses))})
    # First access to final probabilities/labels occurs after thresholds freeze.
    pt=calibrated.predict_proba(X[test])[:,1]
    raw=base.predict_proba(X[test])[:,1]
    for entry in frozen:
        tn,fp,fn,tp=confusion_matrix(y[test],pt>=entry["threshold"],labels=[0,1]).ravel()
        entry.update({"test_confusion_tn_fp_fn_tp":[int(v) for v in (tn,fp,fn,tp)],
                      "test_cost":int(entry["cost_fn"]*fn+entry["cost_fp"]*fp)})
    reliability={}
    for name,p in [("raw",raw),("calibrated",pt)]:
        fraction,mean=calibration_curve(y[test],p,n_bins=6,strategy="quantile")
        reliability[name]={"mean_predicted":mean.tolist(),"observed_fraction":fraction.tolist()}
    return {"data_status":"synthetic independent observations", "partition_sizes":{k:len(v) for k,v in partitions.items()},
            "partition_ids":{k:v.tolist() for k,v in partitions.items()},
            "test_brier_raw":float(brier_score_loss(y[test],raw)),
            "test_brier_calibrated":float(brier_score_loss(y[test],pt)),
            "threshold_source":"threshold validation only", "results":frozen,"reliability":reliability,
            "limitations":"Calibration may worsen finite-sample Brier; reported without selecting on test. No claim under domain shift."}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path)
    args=p.parse_args();result=run()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="partition_ids"},indent=2))

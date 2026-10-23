"""Coefficient stability and block permutation on synthetic correlated bands.

No SHAP dependency; this exercise does not claim chemical causality.
"""
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error


def run():
    rng=np.random.default_rng(12)
    z=rng.normal(size=(180,5));X=np.repeat(z,6,axis=1)+rng.normal(0,.08,(180,30))
    y=2*z[:,0]-z[:,1]+rng.normal(0,.3,180)
    train,test=np.arange(120),np.arange(120,180)
    coefficients=[]
    for _ in range(100):
        boot=rng.choice(train,size=len(train),replace=True)
        model=make_pipeline(StandardScaler(),Ridge(alpha=1)).fit(X[boot],y[boot])
        coefficients.append(model[-1].coef_/model[0].scale_)
    coefficients=np.array(coefficients)
    model=make_pipeline(StandardScaler(),Ridge(alpha=1)).fit(X[train],y[train])
    baseline=mean_squared_error(y[test],model.predict(X[test]))
    records=[]
    for band in range(5):
        cols=np.arange(band*6,(band+1)*6);delta=[]
        for _ in range(30):
            xp=X[test].copy();order=rng.permutation(len(test))
            xp[:,cols]=X[test][order][:,cols]
            delta.append(mean_squared_error(y[test],model.predict(xp))-baseline)
        aggregate=coefficients[:,cols].sum(axis=1)
        records.append({"band":band,"coefficient_sum_mean":float(aggregate.mean()),
                        "coefficient_sum_sd":float(aggregate.std(ddof=1)),
                        "permutation_MSE_increase_mean":float(np.mean(delta))})
    return {"bands":records,"limitations":"Bootstrap SD describes algorithm sensitivity on this sample, not causal evidence. Held-out labels are used only for final block importance, not variable selection."}

if __name__=="__main__":
    import json
    print(json.dumps(run(),indent=2))

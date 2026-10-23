"""Nested grouped model selection on synthetic repeated measurements.

Inner GroupKFold selects family + hyperparameters. Outer GroupKFold estimates
that selection procedure. Independent units are specimens, not scan rows.
"""
import numpy as np
from sklearn.base import clone
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import GroupKFold, GridSearchCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


def run():
    rng=np.random.default_rng(2)
    latent=rng.normal(size=(60,6));loadings=rng.normal(size=(6,30))
    groups=np.repeat(np.arange(60),3)
    X=np.repeat(latent@loadings,3,axis=0)+rng.normal(0,.1,(180,30))
    y=np.repeat(2*latent[:,0]+latent[:,1]**2-latent[:,2],3)+rng.normal(0,.1,180)
    models={
      "PLS":(PLSRegression(),{"n_components":[2,4,6]}),
      "Ridge":(make_pipeline(StandardScaler(),Ridge()),{"ridge__alpha":[.1,10,100]}),
      "SVR":(make_pipeline(StandardScaler(),SVR()),{"svr__C":[1,10],"svr__gamma":[.01,.1]}),
      "RF":(RandomForestRegressor(n_estimators=80,random_state=1,n_jobs=1),{"max_depth":[3,None],"min_samples_leaf":[1,4]})}
    outer=GroupKFold(5);prediction=np.full(len(y),np.nan);records=[]
    for fold,(train,test) in enumerate(outer.split(X,y,groups),1):
        assert set(groups[train]).isdisjoint(groups[test])
        inner=list(GroupKFold(3).split(X[train],y[train],groups[train]))
        assert all(set(groups[train][a]).isdisjoint(groups[train][b]) for a,b in inner)
        searches={}
        for name,(model,grid) in models.items():
            searches[name]=GridSearchCV(clone(model),grid,cv=inner,scoring="neg_root_mean_squared_error",n_jobs=1).fit(X[train],y[train])
        winner=max(searches,key=lambda k:searches[k].best_score_)
        prediction[test]=np.ravel(searches[winner].predict(X[test]))
        records.append({"fold":fold,"selected":winner,"parameters":searches[winner].best_params_})
    assert np.isfinite(prediction).all()
    true=y.reshape(60,3).mean(axis=1);pred=prediction.reshape(60,3).mean(axis=1)
    # GridSearchCV uses scan RMSE; outer reporting averages three scans/specimen.
    return {"selection":records,"outer_specimen_RMSE":float(np.sqrt(mean_squared_error(true,pred))),
            "inner_objective":"scan RMSE", "outer_unit":"mean of three scans per specimen", "independent_specimens":60}

if __name__=="__main__":
    import json
    print(json.dumps(run(),indent=2))

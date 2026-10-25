"""Independently audit identities, fold membership, voting and displayed results."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, balanced_accuracy_score, confusion_matrix
from run import HERE, CLASSES, AXIS, load_data


def verify(output=HERE/'outputs'):
    output=Path(output);meta,X,y=load_data();checks=[]
    def check(ok,name):
        if not ok:raise AssertionError(name)
        checks.append(name)
    check(len(meta)==52 and meta.specimen_id.nunique()==22,'52 measured spectra, 22 RRUFF IDs')
    counts=meta.groupby('mineral').specimen_id.nunique().to_dict()
    check(counts=={'Quartz':10,'Calcite':10,'Gypsum':2},'rare-class limitation retained')
    check(meta.numeric_sha256.is_unique,'no identical numeric spectra')
    provenance=json.loads((HERE/'data/provenance.json').read_text(encoding='utf-8'))
    check(provenance['data_status'].startswith('MEASURED') and provenance['license']=='CC BY 4.0','measured source and license')
    folds=json.loads((output/'folds.json').read_text(encoding='utf-8'))
    ids=set(meta.specimen_id);seen=[]
    for f in folds:
        tr,te=set(f['train_ids']),set(f['test_ids'])
        check(len(te)==1 and not tr&te and tr|te==ids,'fold isolation '+str(f['fold']))
        check(f['train_spectra']==int(meta.specimen_id.isin(tr).sum()) and f['test_spectra']==int(meta.specimen_id.isin(te).sum()),'fold sizes '+str(f['fold']))
        seen.extend(te)
    check(len(seen)==22 and set(seen)==ids,'each specimen held out exactly once')
    rows=pd.read_csv(output/'row_predictions.csv',dtype={'spectrum_id':str})
    samples=pd.read_csv(output/'specimen_predictions.csv')
    metrics=json.loads((output/'metrics.json').read_text(encoding='utf-8'))
    expected={'Dummy','Cosine_1NN','PCA8_LR','RBF_SVC'}
    check(set(rows.model)==set(samples.model)==set(metrics['metrics'])==expected,'four models retained')
    foldmap={f['test_ids'][0]:f['fold'] for f in folds}
    for name,g in rows.groupby('model'):
        check(len(g)==52 and g.spectrum_id.is_unique and set(g.spectrum_id)==set(meta.spectrum_id),'complete spectrum predictions '+name)
        merged=g.merge(meta,on='spectrum_id',suffixes=('','_reference'),validate='one_to_one')
        check(merged.specimen_id.eq(merged.specimen_id_reference).all() and merged.true_class.eq(merged.mineral_reference.map(dict(zip(CLASSES,range(3))))).all(),'identity/label traceability '+name)
        check(g.fold.eq(g.specimen_id.map(foldmap)).all(),'prediction uses held-out specimen fold '+name)
        s=samples[samples.model.eq(name)].set_index('specimen_id')
        check(len(s)==22 and s.index.is_unique and set(s.index)==ids,'complete specimen predictions '+name)
        for sid,h in g.groupby('specimen_id'):
            vote=int(np.bincount(h.predicted_class,minlength=3).argmax())
            check(vote==s.loc[sid,'predicted_class'] and h.true_class.iloc[0]==s.loc[sid,'true_class'],'independent vote '+name+' '+sid)
        for unit,frame in [('spectrum',g),('specimen',s)]:
            result=metrics['metrics'][name][unit]
            check(np.isclose(f1_score(frame.true_class,frame.predicted_class,average='macro',labels=range(3)),result['macro_f1']) and np.isclose(balanced_accuracy_score(frame.true_class,frame.predicted_class),result['balanced_accuracy']),'recomputed scores '+name+' '+unit)
            check(confusion_matrix(frame.true_class,frame.predicted_class,labels=range(3)).tolist()==result['confusion_matrix'],'recomputed matrix '+name+' '+unit)
    script=(output/'browser-data.js').read_text(encoding='utf-8')
    browser=json.loads(script.removeprefix('window.RRUFF_REAL=').rstrip(';\n'))
    check(browser['results']==metrics,'browser metrics match')
    check(browser['predictions']==rows.to_dict('records'),'browser predictions match')
    check(len(browser['spectra'])==52 and all(len(s['intensity'])==501 for s in browser['spectra']),'browser spectrum coverage')
    check(browser['axis']==AXIS.tolist(),'browser axis matches fixed grid')
    normalized=X / np.linalg.norm(X,axis=1,keepdims=True)
    for i,(r,b) in enumerate(zip(meta.itertuples(),browser['spectra'])):
        check(b['id']==r.spectrum_id and b['specimen']==r.specimen_id and b['mineral']==r.mineral and b['laser']==int(r.laser_nm),'browser spectrum identity '+r.spectrum_id)
        check(np.allclose(b['intensity'],normalized[i],rtol=6e-7,atol=1e-12),'browser numeric spectrum '+r.spectrum_id)
    print(json.dumps({'passed':len(checks),'checks':checks},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=HERE/'outputs')
    verify(p.parse_args().output)

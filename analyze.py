"""Exploratory CoAuthor secondary analysis. No causal or clinical claims.
Usage: python analyze.py --input coauthor_metadata.xlsx --out results
Dependencies: pandas openpyxl numpy scipy matplotlib
"""
from pathlib import Path
import argparse, hashlib, json, warnings, platform
import numpy as np
import pandas as pd
import scipy
from scipy.stats import spearmanr, t
from scipy.optimize import minimize
from scipy.optimize import check_grad
from scipy.special import expit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from stats_core import design, logistic_cluster

P=argparse.ArgumentParser(description=__doc__)
P.add_argument('--input', required=True, help='Original CoAuthor XLSX workbook')
P.add_argument('--out', default='results', help='Output directory; may contain raw participant comments')
P.add_argument('--bootstrap', type=int, default=500, help='Participant bootstrap repetitions (default: 500)')
P.add_argument('--seed', type=int, default=20261009, help='Bootstrap seed; qualitative selection uses fixed 20261009')
A=P.parse_args(); OUT=Path(A.out); OUT.mkdir(parents=True,exist_ok=True)
if A.bootstrap < 20:
    P.error('--bootstrap must be at least 20; use 500 for reported results')
raw=pd.read_excel(A.input,sheet_name=None)
required_sheets = {'Metadata (creative)', 'Metadata (argumentative)', 'Survey (creative)', 'Survery (argumentative)'}
if not required_sheets.issubset(raw):
    raise ValueError(f'Missing source sheets: {sorted(required_sheets - set(raw))}')
audit={'sha256':hashlib.sha256(Path(A.input).read_bytes()).hexdigest(),'sheets':{},'decisions':[
 'Trim surrounding whitespace in participant and session IDs; do not fuzzy-match.',
 'Retain latest survey for duplicated session ID; earliest retained as sensitivity.',
 'Require exact session+participant match; primary analysis requires num_query > 0.',
 'Treat ratings as observed 1-7 ordinal categories despite paper section 5.2 stating 5 points.',
 'No imputation; no-query is observed non-use, not missing data.',
 'All analyses exploratory and not preregistered; focal hypotheses were set after schema inspection, before initial model outputs.',
 'Additional weighting and session-order sensitivities were added after reviewing initial results.'
]}
maps={
'understanding':'the system understood what I was trying to write',
'ideation':'the suggestions helped me come up with new ideas',
'ownership':'I feel like the',
'satisfaction':'I am satisfied with',
'confidence':'I am confident in my ability',
'fluency':'grammatically correct',
'alone_better':'would have written a *better*',
'reuse':'I would reuse',
'ease':'It was easy to write',
'perceived_human':'____%',
'improve':'Which aspects of the suggestions',
'comment':'Any feedback/comment?',
}
def prepare(keep='last'):
    frames=[]
    for genre,mn,sn in [('creative','Metadata (creative)','Survey (creative)'),('argumentative','Metadata (argumentative)','Survery (argumentative)')]:
        m=raw[mn].copy(); s=raw[sn].copy(); orig=len(s)
        needed={'session_id','worker_id','num_query','written_by_human','time','temperature','frequency_penalty','prompt_code','timestamp'}
        # Some releases may spell the penalty differently; only columns actually used are mandatory.
        needed.discard('frequency_penalty')
        if not needed.issubset(m):
            raise ValueError(f'{mn}: missing metadata columns {sorted(needed-set(m))}')
        s=s.rename(columns={s.columns[0]:'survey_time',s.columns[1]:'survey_worker',s.columns[2]:'session_id'})
        for name,fragment in maps.items():
            found=[c for c in s if fragment in c]
            if len(found) != 1:
                raise ValueError(f'{sn}: expected one column matching {fragment!r}, found {len(found)}')
            s=s.rename(columns={found[0]:name})
        for f in (m,s): f['session_id']=f.session_id.astype(str).str.strip()
        m.worker_id=m.worker_id.astype(str).str.strip(); s.survey_worker=s.survey_worker.astype(str).str.strip()
        assert m.session_id.is_unique
        dupe=s[s.session_id.duplicated(False)]
        if keep=='last': dupe.to_csv(OUT/f'duplicate_surveys_{genre}.csv',index=False)
        ndup=int(s.session_id.duplicated().sum()); unmatched=int((~s.session_id.isin(m.session_id)).sum())
        s=s.sort_values('survey_time').drop_duplicates('session_id',keep=keep)
        j=m.merge(s,on='session_id',how='left',validate='one_to_one',indicator=True)
        mism=(j['_merge']=='both') & (j.worker_id!=j.survey_worker)
        if keep=='last':
            audit['sheets'][genre]={'metadata_rows':len(m),'metadata_workers':m.worker_id.nunique(),'survey_rows':orig,
             'duplicate_excess':ndup,'survey_unmatched_rows':unmatched,'metadata_without_survey':int((j['_merge']=='left_only').sum()),
             'worker_mismatch':int(mism.sum()),'no_query':int((m.num_query==0).sum())}
        j=j[(j['_merge']=='both') & ~mism].copy(); j['genre']=genre
        frames.append(j)
    d=pd.concat(frames,ignore_index=True)
    for c in ['understanding','ideation','ownership','satisfaction','confidence','fluency','alone_better','reuse','ease','perceived_human']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    for c in ['understanding','ideation','ownership','satisfaction','confidence','fluency','alone_better','reuse','ease']:
        assert d[c].dropna().between(1,7).all()
    d.loc[~d.perceived_human.between(0,100),'perceived_human']=np.nan
    if not d.written_by_human.between(0,100).all() or not (d.time>0).all() or not (d.num_query>=0).all():
        raise ValueError('Invalid human share, duration, or query count; inspect the source before modeling.')
    d['human10']=d.written_by_human/10
    d['log_query']=np.log1p(d.num_query)
    d['log_time']=np.log(d.time)
    d['high_creative']=((d.genre=='creative')&(d.temperature==.75)).astype(int)
    d['high_argumentative']=((d.genre=='argumentative')&(d.temperature==.9)).astype(int)
    d['gap']=d.perceived_human-d.written_by_human
    return d

def center(d):
    d=d.copy()
    for c in ['understanding','human10','ideation','log_query','log_time','fluency']:
        d[c+'_b']=d.groupby('worker_id')[c].transform('mean')
        d[c+'_w']=d[c]-d[c+'_b']
    d['session_order']=d.groupby('worker_id')['timestamp'].rank(method='first')
    d['order_w']=(d.session_order-d.groupby('worker_id').session_order.transform('mean'))/10
    return d

joined=prepare(); primary=center(joined[joined.num_query>0].dropna(subset=['understanding','ownership','human10','ideation']).copy())
audit['joined_sessions']=len(joined); audit['joined_workers']=joined.worker_id.nunique()
audit['primary_sessions']=len(primary); audit['primary_workers']=primary.worker_id.nunique()
audit['primary_genres']=primary.genre.value_counts().to_dict()
audit['primary_sessions_per_worker']=primary.groupby('worker_id').size().describe().to_dict()
audit['workers_varying_understanding']=int((primary.groupby('worker_id').understanding.nunique()>1).sum())
audit['workers_varying_ownership']=int((primary.groupby('worker_id').ownership.nunique()>1).sum())
audit['versions']={'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__,'scipy':scipy.__version__, 'matplotlib':matplotlib.__version__, 'openpyxl':__import__('openpyxl').__version__}
numeric=['ownership','understanding','ideation','satisfaction','confidence','written_by_human','num_query','time','gap']
primary.groupby('genre')[numeric].agg(['count','mean','std','median']).to_csv(OUT/'descriptives.csv')
primary.groupby('genre').ownership.value_counts().unstack(fill_value=0).to_csv(OUT/'ownership_distribution.csv')
primary.to_csv(OUT/'analysis_data.csv',index=False)

BASE='understanding_w + understanding_b + human10_w + human10_b + C(prompt_code) + high_creative + high_argumentative'
fits={}; details={}; rows=[]
def record(name,X,f,ordinal=True):
    for i,term in enumerate(X.columns):
        r={'model':name,'term':term,'beta':float(f['b'][i]),'se':float(f['se'][i]),'ci_low':float(f['lo'][i]),'ci_high':float(f['hi'][i]),'p':float(f['p'][i])}
        if ordinal: r.update(OR=float(np.exp(f['b'][i])),OR_low=float(np.exp(f['lo'][i])),OR_high=float(np.exp(f['hi'][i])))
        rows.append(r)

def gee_fit(name,d,rhs=BASE,outcome='ownership',equal_person=False):
    X=design(d,rhs); cuts=np.arange(1,7); n=len(d)
    # Working-independence ordinal GEE: stack Y>k, k=1,...,6.
    # Cluster by PERSON, accounting for both threshold and repeated-session dependence.
    Z=pd.DataFrame(np.column_stack([np.tile(np.eye(6),(n,1)),np.repeat(X.to_numpy(),6,axis=0)]),columns=[f'threshold_{k}' for k in cuts]+list(X.columns))
    assert np.linalg.matrix_rank(Z)==Z.shape[1]
    y=(d[outcome].to_numpy()[:,None]>cuts).ravel()
    f=logistic_cluster(Z,y,np.repeat(d.worker_id.to_numpy(),6),equal_person)
    assert np.all(np.diff(f['b'][:6])<0), 'Nonmonotonic cumulative probabilities'
    fits[name]=f; details[name]={'n':len(d),'workers':d.worker_id.nunique(),'max_abs_mean_score':f['maxscore'],'condition_number':f['condition_number'],'optimizer_message':f['optimizer_message']}
    record(name,Z,f)
    return f

main=gee_fit('primary_ordinal',primary)
gee_fit('equal_person_weight',primary,equal_person=True)
gee_fit('session_order_adjusted',primary,BASE+' + order_w')
gee_fit('extended_behavior',primary,BASE+' + log_query_w + log_query_b + log_time_w + log_time_b')
gee_fit('ideation_adjusted',primary,BASE+' + ideation_w + ideation_b')
gee_fit('fluency_adjusted',primary,BASE+' + fluency_w + fluency_b')
gee_fit('within_interaction',primary,BASE+' + ideation_w + ideation_b + understanding_w:ideation_w')
gee_fit('ideation_outcome',primary,BASE,outcome='ideation')
gee_fit('all_queries_included',center(joined),BASE)
first=prepare('first'); gee_fit('earliest_duplicate',center(first[first.num_query>0]),BASE)
for genre in ['creative','argumentative']:
    dg=center(primary[primary.genre==genre])
    rhs='understanding_w + understanding_b + human10_w + human10_b + C(prompt_code) + high_'+genre
    gee_fit(genre,dg,rhs)

# Linear participant-fixed-effects model as a sensitivity, not the main ordinal model.
xb=design(primary,'understanding + human10 + C(worker_id) + C(prompt_code) + high_creative + high_argumentative',True)
xx=xb.to_numpy(); yy=primary.ownership.to_numpy(); b=np.linalg.lstsq(xx,yy,rcond=None)[0]
gc=pd.Categorical(primary.worker_id); G=len(gc.categories); n,p=xx.shape
S=np.zeros((G,p)); np.add.at(S,gc.codes,xx*(yy-xx@b)[:,None]); inv=np.linalg.inv(xx.T@xx)
V=inv@(S.T@S)@inv*(G/(G-1))*((n-1)/(n-p)); se=np.sqrt(np.diag(V)); crit=t.ppf(.975,G-1)
f={'b':b,'se':se,'lo':b-crit*se,'hi':b+crit*se,'p':2*t.sf(np.abs(b/se),G-1)}
record('participant_FE_linear',xb,f,False); fe_point=float(b[xb.columns.get_loc('understanding')])

# Threshold-specific binary GEE is a sensitivity diagnostic for proportional odds.
X=design(primary,BASE,True)
for cut in [3,4,5,6]:
    fit=logistic_cluster(X,(primary.ownership>cut).astype(int),primary.worker_id)
    record(f'threshold_gt_{cut}',X,fit)

# Person-cluster bootstrap for the transparent FE linear sensitivity (500 resamples).
# Precomputed design with reweighted full worker clusters is algebraically equivalent
# to concatenating resampled clusters for OLS; least squares handles zero-weight
# worker dummy columns through its minimum-norm solution.
wid=pd.Categorical(primary.worker_id); G=len(wid.categories)
byX=np.array([xx[wid.codes==g].T@xx[wid.codes==g] for g in range(G)])
byY=np.array([xx[wid.codes==g].T@yy[wid.codes==g] for g in range(G)])
rng=np.random.default_rng(A.seed); bi=xb.columns.get_loc('understanding'); boot=[]
for b in range(A.bootstrap):
    w=np.bincount(rng.integers(0,G,G),minlength=G)
    gram=np.tensordot(w,byX,axes=1); target=np.tensordot(w,byY,axes=1)
    est=np.linalg.lstsq(gram,target,rcond=1e-10)[0][bi]; boot.append(float(est))
audit['FE_cluster_bootstrap']={'B':A.bootstrap,'seed':A.seed,'percentile_CI':np.quantile(boot,[.025,.975]).tolist(),'point':fe_point}

res=pd.DataFrame(rows)
# Only the two secondary focal tests constitute the declared Holm family.
mask=((res.model=='within_interaction')&(res.term=='understanding_w:ideation_w'))|((res.model=='ideation_outcome')&(res.term=='understanding_w'))
pv=res.loc[mask,'p'].to_numpy(); order=np.argsort(pv); adjusted=np.empty(len(pv)); adjusted[order]=np.minimum(1,np.maximum.accumulate(pv[order]*np.arange(len(pv),0,-1)))
res.loc[mask,'p_holm_secondary']=adjusted
res.to_csv(OUT/'model_results.csv',index=False)
audit['models']=details
audit['raw_spearman']={c:float(spearmanr(primary[c],primary.ownership).statistic) for c in ['understanding','ideation','written_by_human']}
audit['gap_descriptives']={'valid_n':int(primary.gap.notna().sum()),'mean':float(primary.gap.mean()),'median':float(primary.gap.median())}

# Numerical validation: analytic score vs finite differences on real design;
# intercept-only stacked logits vs empirical cumulative probabilities;
# FE coefficient vs independent Frisch-Waugh-Lovell residualization.
vx=design(primary,BASE,True).to_numpy(); vy=(primary.ownership>5).to_numpy().astype(float)
theta=np.linspace(-.05,.05,vx.shape[1]); nn=len(vy)
grad_error=check_grad(lambda b:np.sum(np.logaddexp(0,vx@b)-vy*(vx@b))/nn,lambda b:vx.T@(expit(vx@b)-vy)/nn,theta)
zc=pd.DataFrame(np.tile(np.eye(6),(len(primary),1)),columns=[f'k{k}' for k in range(6)])
yc=(primary.ownership.to_numpy()[:,None]>np.arange(1,7)).ravel()
sat=logistic_cluster(zc,yc,np.repeat(primary.worker_id.to_numpy(),6))
empirical=(primary.ownership.to_numpy()[:,None]>np.arange(1,7)).mean(axis=0)
sat_error=float(np.max(np.abs(expit(sat['b'])-empirical)))
u=xb['understanding'].to_numpy(); others=xb.drop(columns='understanding').to_numpy()
ur=u-others@np.linalg.lstsq(others,u,rcond=None)[0]; yr=yy-others@np.linalg.lstsq(others,yy,rcond=None)[0]
fwl=float(ur@yr/(ur@ur)); assert abs(fwl-fe_point)<1e-8 and grad_error<1e-5 and sat_error<1e-6
audit['numerical_validation']={'gradient_error_norm':float(grad_error),'intercept_only_max_probability_error':sat_error,'FE_FWL_coefficient_difference':float(abs(fwl-fe_point))}

# Select contrasting cases before reading free text. Ratings <=3 vs >=6.
# Seeded sample: up to 3 per genre/quadrant; at most one case per worker per cell.
q=primary.copy(); q['u_group']=np.where(q.understanding>=6,'high',np.where(q.understanding<=3,'low','middle'))
q['o_group']=np.where(q.ownership>=6,'high',np.where(q.ownership<=3,'low','middle'))
q['text_available']=q.improve.fillna('').str.strip().ne('')|q.comment.fillna('').str.strip().ne('')
sel=[]; cells={}
for genre in ['creative','argumentative']:
    for u in ['low','high']:
        for o in ['low','high']:
            sub=q[(q.genre==genre)&(q.u_group==u)&(q.o_group==o)&q.text_available]
            cells[f'{genre}_{u}_{o}']=len(sub)
            sub=sub.sample(frac=1,random_state=20261009).drop_duplicates('worker_id').head(3)
            sel.append(sub)
selected=pd.concat(sel).copy(); selected['case_id']=[f'Q{i:02}' for i in range(1,len(selected)+1)]
selected[['case_id','session_id','genre','u_group','o_group','understanding','ownership','written_by_human','ideation','improve','comment']].to_csv(OUT/'qualitative_sample.csv',index=False)
audit['qualitative_sampling']={'eligible_cells':cells,'selected_n':len(selected),'selected_workers':selected.worker_id.nunique(),'max_per_genre_quadrant':3,'seed':20261009}

# Figure: primary model and exploratory sensitivities, with robust 95% CIs.
plotmodels=['primary_ordinal','equal_person_weight','session_order_adjusted','extended_behavior','ideation_adjusted','fluency_adjusted','creative','argumentative']
z=res[(res.model.isin(plotmodels))&(res.term=='understanding_w')].set_index('model').loc[plotmodels]
labels=['Primary','Equal person weights','+ within-person session order','+ usage and duration','+ ideation rating','+ fluency rating','Creative only','Argumentative only']
fig,ax=plt.subplots(figsize=(8,4.6)); yy=np.arange(len(z))
ax.errorbar(z.OR,yy,xerr=[z.OR-z.OR_low,z.OR_high-z.OR],fmt='o',color='#255c86',capsize=3)
ax.axvline(1,color='gray',ls='--'); ax.set_yticks(yy,labels); ax.invert_yaxis()
ax.set_xlabel('Odds ratio for higher ownership per +1 within-person understanding point')
ax.set_title('Exploratory associations, not causal effects'); ax.spines[['top','right']].set_visible(False)
fig.tight_layout(); fig.savefig(OUT/'associations.png',dpi=180); plt.close(fig)
(OUT/'audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False,default=lambda x:int(x) if isinstance(x,np.integer) else float(x)))
print(json.dumps({k:v for k,v in audit.items() if k!='models'},indent=2,default=str))
print(res[(res.term.isin(['understanding_w','understanding_b','human10_w','understanding_w:ideation_w','understanding']))].to_string(index=False))

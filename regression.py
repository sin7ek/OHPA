"""Exploratory OLS with gap-aware hourly Newey-West covariance."""
import numpy as np
def fit(y,columns,names,times):
    y=np.asarray(y,float);X=np.column_stack([np.ones(len(y))]+columns)
    n,p=X.shape
    if n<=p:return None
    # Scale predictors for numerical stability; transform results back to original units.
    scale=np.r_[1.,np.std(X[:,1:],axis=0)]
    if np.any(scale<=0):return None
    Z=X/scale;beta,_,rank,_=np.linalg.lstsq(Z,y,rcond=None)
    if rank<p:return None
    pred=Z@beta;res=y-pred;score=Z*res[:,None]
    lag=min(24,max(1,n//4));meat=score.T@score
    # Only actual hourly lags, never bridge excluded hours as if adjacent.
    index={round(float(t)/3600):i for i,t in enumerate(times)}
    for k in range(1,lag+1):
        pairs=[(i,index.get(hour-k)) for hour,i in index.items()]
        pairs=[(i,j) for i,j in pairs if j is not None]
        if pairs:
            i,j=np.array(pairs).T;cross=score[i].T@score[j];meat+=(1-k/(lag+1))*(cross+cross.T)
    bread=np.linalg.pinv(Z.T@Z);cov=bread@meat@bread*n/(n-p)
    se=np.sqrt(np.maximum(np.diag(cov),0))/scale;coef=beta/scale
    ss=float(res@res);den=float(np.sum((y-y.mean())**2))
    def rr(v):return round(float(v),6)
    return {'features':names,'coefficients':{k:rr(v) for k,v in zip(['intercept']+names,coef)},'confidence_intervals_95':{k:[rr(v-1.96*s),rr(v+1.96*s)] for k,v,s in zip(['intercept']+names,coef,se)},'heat_loss_w_per_k':rr(coef[1]*1000),'heat_loss_ci95_w_per_k':[rr((coef[1]-1.96*se[1])*1000),rr((coef[1]+1.96*se[1])*1000)],'rmse_kw':rr(np.sqrt(ss/n)),'r2':rr(1-ss/den) if den>0 else None,'adjusted_r2':rr(1-(ss/(n-p))/(den/(n-1))) if den>0 else None,'hac_lag_hours':lag,'predictor_means':{k:rr(v) for k,v in zip(names,np.mean(X[:,1:],axis=0))},'predicted_kw':[rr(v) for v in pred]}

def diagnostics(y,columns,names,times,model):
    X=np.column_stack(columns);y=np.asarray(y);times=np.asarray(times)
    pred=np.asarray(model['predicted_kw']);res=y-pred;n=len(y)
    def rr(v):return round(float(v),5) if np.isfinite(v) else None
    def corr(a,b):
        return rr(np.corrcoef(a,b)[0,1]) if len(a)>2 and np.std(a)>1e-12 and np.std(b)>1e-12 else None
    def ols(x,z):
        design=np.column_stack([np.ones(len(x)),x])
        coef,_,rank,_=np.linalg.lstsq(design,z,rcond=None)
        return coef if rank==design.shape[1] else None
    vif={}
    for k,name in enumerate(names):
        z=X[:,k];others=np.delete(X,k,axis=1)
        if not others.shape[1]:vif[name]=1.;continue
        beta=ols(others,z)
        if beta is None:vif[name]=None;continue
        err=z-(np.column_stack([np.ones(n),others])@beta)
        fraction=np.sum(err**2)/np.sum((z-z.mean())**2)
        vif[name]=rr(1/fraction) if fraction>1e-10 else None
    allcols=[*columns,y];labels=[*names,'heat_kw']
    index={round(v/3600):i for i,v in enumerate(times)}
    acf=[]
    for lag in (1,2,3,6,12,24):
        pairs=[(i,index[h-lag]) for h,i in index.items() if h-lag in index]
        acf.append({'lag_hours':lag,'pairs':len(pairs),'correlation':corr(*[res[np.array(pairs)[:,k]] for k in (0,1)]) if len(pairs)>2 else None})
    # Chronological expanding windows, shared splits across all variants.
    cv=[];errors=[]
    for frac in (.5,.625,.75,.875):
        a=int(n*frac);b=min(n,a+max(1,n//8))
        if a<24 or b-a<3:continue
        beta=ols(X[:a],y[:a])
        if beta is None:continue
        err=y[a:b]-np.column_stack([np.ones(b-a),X[a:b]])@beta
        errors.extend(err.tolist());cv.append({'train_hours':a,'test_hours':b-a,'rmse_kw':rr(np.sqrt(np.mean(err**2)))})
    rolling=[]
    # Seven calendar days, step one day. Only full windows, no filling excluded hours.
    first=times[0];last=times[-1]+3600
    for end in np.arange(first+7*86400,last+1,86400):
        mask=(times>=end-7*86400)&(times<end)
        if mask.sum()<24 or np.ptp(X[mask,0])<4:continue
        beta=ols(X[mask],y[mask])
        if beta is not None:rolling.append({'end_epoch':int(end),'hours':int(mask.sum()),'slope_w_per_k':rr(1000*beta[1])})
    return {'vif':vif,'correlations':{'labels':labels,'matrix':[[corr(x,z) for z in allcols] for x in allcols]},'residual_acf':acf,'residual_abs_vs_fitted_correlation':corr(np.abs(res),pred),'residuals_kw':[rr(v) for v in res],'cv':{'folds':cv,'test_hours':len(errors),'rmse_kw':rr(np.sqrt(np.mean(np.square(errors)))) if errors else None,'mae_kw':rr(np.mean(np.abs(errors))) if errors else None},'rolling_7d':rolling,'predictor_ranges':{k:[rr(np.min(v)),rr(np.max(v))] for k,v in zip(names,columns)}}

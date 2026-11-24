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

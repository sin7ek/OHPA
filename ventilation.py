"""Observed fan runtime and explicitly user-selected CO2 decay experiment."""
import math
import numpy as np
from core import aligned,load,mapping,series_id,r,local_iso
def fan_report(cfg,p,a,b):
    t,d,x=aligned(cfg,a,b);v=x.get('bathroom_fan',np.full(t.shape,np.nan));ok=np.isfinite(v)
    hours=float(d[ok&(v==1)].sum()/3600);known=float(d[ok].sum()/3600);nom=p['air_exchange']['fan_nominal_m3h']
    return {'start':local_iso(a),'end':local_iso(b),'coverage_pct':r(known*3600/(b-a),2),'runtime_hours':r(hours) if known else None,'nominal_extracted_m3':r(hours*nom) if known and nom is not None else None}
def decay(cfg,a,b,outdoor):
    if not 0<b-a<=6*3600 or b-a<1800:raise ValueError('Select a 30 minute to 6 hour decay interval')
    if not math.isfinite(outdoor) or not 250<=outdoor<=1000:raise ValueError('Enter measured or justified outdoor CO2 (250–1000 ppm)')
    m=mapping(cfg).get('co2_indoor')
    if not m:return {'status':'missing_sensor'}
    ts,vs,cov=load(series_id('co2_indoor',m),a,b)
    # Fit actual recorder events only; no synthetic repeated samples.
    ok=(ts>=a)&(ts<=b)&np.isfinite(vs);ts=ts[ok];vs=vs[ok]
    coverage=sum(max(0,min(b,y)-max(a,x)) for x,y in cov)/(b-a)
    if len(ts)<8 or ts[-1]-ts[0]<1800 or coverage<.95 or np.max(np.diff(ts))>900 or np.any(vs-outdoor<100) or vs[0]-vs[-1]<100:
        return {'status':'insufficient_decay_data','samples':len(ts),'coverage_pct':r(coverage*100,2)}
    x=(ts-ts[0])/3600;y=np.log(vs-outdoor);coef=np.polyfit(x,y,1);pred=np.polyval(coef,x);den=np.sum((y-y.mean())**2)
    fit=1-np.sum((y-pred)**2)/den if den>0 else 0
    if coef[0]>=0 or fit<.8:return {'status':'poor_decay_fit','samples':len(ts),'r2':r(fit)}
    return {'status':'exploratory','ach':r(-coef[0]),'r2':r(fit),'samples':len(ts),'duration_hours':r(x[-1]),'coverage_pct':r(coverage*100,2),'warning':'Local zone only; assumes no CO2 sources, constant outdoor concentration, well-mixed air and approximately constant airflow. No automatic profile adoption.'}

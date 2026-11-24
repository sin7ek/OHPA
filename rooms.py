"""Optional room registry, read-only HA mappings and coverage-aware local analysis."""
import re, math
import numpy as np
import core
FIELDS={'temperature':('zone_temperature',['°C','°F','K']),'target':('target',['°C','°F','K']),'humidity':('zone_humidity',['%']),'co2':('co2_indoor',['ppm']),'presence':('zone_presence',['on/off']),'light':('illuminance',['lx','klx']),'fan':('bathroom_fan',['on/off']),'window':('zone_presence',['on/off']),'door':('zone_presence',['on/off']),'power':('power',['W','kW'])}
def num(x):
    if x in (None,''):return None
    x=float(x)
    if not math.isfinite(x) or not 0<x<=100000:raise ValueError('Invalid room dimension')
    return x
def normalize(raw):
    if not isinstance(raw,list) or len(raw)>100:raise ValueError('Maximum 100 rooms')
    out=[];ids=set()
    for item in raw:
        rid=str(item.get('id',''))
        if not re.fullmatch('[a-zA-Z0-9_-]{1,64}',rid) or rid in ids:raise ValueError('Invalid or duplicate room ID')
        ids.add(rid);sensors={}
        for key,m in item.get('sensors',{}).items():
            if key not in FIELDS or not m.get('entity'):continue
            entity=m['entity'];unit=m['unit']
            if not isinstance(entity,str) or not re.fullmatch('[a-z0-9_]+\\.[a-z0-9_]+',entity) or len(entity)>250 or unit not in FIELDS[key][1]:raise ValueError('Invalid room sensor')
            sensors[key]={'entity':entity,'attribute':str(m.get('attribute',''))[:100],'unit':unit,'on_value':str(m.get('on_value','on'))[:100]}
        out.append({'id':rid,'name':str(item.get('name',''))[:100],'floor':str(item.get('floor',''))[:100],'area':num(item.get('area')),'volume':num(item.get('volume')),'heated':item.get('heated') if item.get('heated') in ('yes','no','unknown') else 'unknown','emitter':str(item.get('emitter',''))[:100],'area_id':str(item.get('area_id',''))[:100],'sensors':sensors})
    return out
def mappings(profile):
    return [(room,key,FIELDS[key][0],m) for room in profile for key,m in room['sensors'].items()]
def report(cfg,profile,a,b):
    result=[]
    for room in profile:
        data={};edges=[np.array([a,b])]
        for key,m in room['sensors'].items():
            role=FIELDS[key][0];ts,vs,cov=core.load(core.series_id(role,m),a,b)
            data[key]=(ts,vs,cov);edges.append(ts[(ts>a)&(ts<b)])
            for x,y in cov:edges.append(np.array([max(a,x),min(b,y)]))
        e=np.unique(np.concatenate(edges));t=e[:-1];d=np.diff(e)
        vals={k:core.interpolate_step(t,*v,False,cfg['counter_max_gap']) for k,v in data.items()}
        metrics={}
        for k,v in vals.items():
            ok=np.isfinite(v);sec=d[ok].sum()
            metrics[k]={'coverage_pct':core.r(100*sec/(b-a),2),'mean':core.r(np.sum(v[ok]*d[ok])/sec) if sec else None,'min':core.r(np.min(v[ok])) if sec else None,'max':core.r(np.max(v[ok])) if sec else None}
        comfort=None
        if 'temperature' in vals and 'target' in vals:
            x,y=vals['temperature'],vals['target'];ok=np.isfinite(x)&np.isfinite(y);sec=d[ok].sum()
            if sec:comfort={'coverage_pct':core.r(100*sec/(b-a),2),'deficit_degree_hours':core.r(np.sum(np.maximum(y[ok]-x[ok],0)*d[ok])/3600),'within_half_degree_pct':core.r(100*d[ok&(np.abs(x-y)<=.5)].sum()/sec)}
        result.append({'id':room['id'],'name':room['name'],'floor':room['floor'],'metrics':metrics,'comfort':comfort})
    return {'rooms':result,'start':core.local_iso(a),'end':core.local_iso(b),'warning':'Local room measurements only; no automatic extrapolation or changes to whole-house regression.'}
def co2_config(cfg,room):
    # Reuse canonical role identities, so room and legacy mappings share history.
    m={k:v for k,v in cfg['mapping'].items() if k not in ('co2_indoor','zone_presence','zone_temperature','zone_humidity','bathroom_fan')}
    for key in ('co2','presence','temperature','humidity','fan'):
        if key in room['sensors']:m[FIELDS[key][0]]=room['sensors'][key]
    return {**cfg,'mapping':m}

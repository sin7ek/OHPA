"""Local, opt-in VFM research; never modifies measured analytics."""
import csv
import io
import uuid
import hashlib
import json
import numpy as np
import core
import virtual_flow as vf

FIELDS = ('installation_id','model','mode','defrost','buh','steady','power_source',
          'frequency_hz','outside_c','supply_c','return_c','power_w','water_factor',
          'measured_flow_lh','pump_pwm','minute_index')
REQUIRED = ('frequency','outside','supply','return','power','defrost','heating')


def settings():
    return core.getmeta('vfm_settings', {'enabled':False,'confirmed':False,'installation_id':None})


def configure(enabled, confirmed):
    if type(enabled) is not bool or type(confirmed) is not bool:
        raise ValueError('Explicit boolean choices required')
    previous = settings()
    result = {'enabled':enabled,'confirmed':confirmed,'installation_id':previous.get('installation_id') or uuid.uuid4().hex,'mapping_hash':fingerprint(core.config())}
    core.setmeta('vfm_settings', result)
    return result


def fingerprint(cfg):
    return hashlib.sha256(json.dumps({k:cfg[k] for k in ('mapping','model','buh_mode','buh_thermal','water_factor','regional')},sort_keys=True).encode()).hexdigest()


def observations(cfg, a, b, setup, reference=True):
    if not setup.get('enabled') or not setup.get('confirmed'):
        raise ValueError('Enable research and confirm measurement boundaries first')
    if setup.get('mapping_hash') != fingerprint(cfg):
        raise ValueError('Sensor setup changed; confirm research boundaries again')
    if cfg['model'] not in vf.MODELS:
        raise ValueError('Select an Amber model in sensor setup')
    mapping = core.mapping(cfg)
    if any(k not in mapping for k in REQUIRED) or mapping['outside'].get('source') == 'regional':
        raise ValueError('Map frequency, local outside, supply, return, power, heating and defrost')
    if cfg['buh_mode'] != 'none' and (cfg['buh_mode'] != 'separate' or 'buh' not in mapping):
        raise ValueError('Confirm no BUH or map separate BUH power')
    if reference and not ('flow' in mapping or 'flow_counter' in mapping):
        raise ValueError('Map a physical primary flow meter for reference export')
    # A complete five-minute steady window preceding each non-overlapping minute.
    first = int(np.ceil(a/60))*60; end = int(b//60)*60
    if end <= first: return []
    t,d,x = core.aligned(cfg,first-300,end)
    out = []
    for minute in range(first,end,60):
        left = np.searchsorted(t+d,minute-300,side='right')
        right = np.searchsorted(t,minute+60,side='left')
        sl = slice(left,right)
        keys = REQUIRED + (('buh',) if cfg['buh_mode']=='separate' else ())
        if not all(k in x and np.isfinite(x[k][sl]).all() for k in keys): continue
        if not len(t[sl]) or not np.all(x['heating'][sl]==1) or not np.all(x['defrost'][sl]==0): continue
        if cfg['buh_mode']=='separate' and not np.all(x['buh'][sl]==0): continue
        if np.min(x['frequency'][sl])<=0 or np.ptp(x['frequency'][sl])>3: continue
        if np.ptp(x['supply'][sl])>1 or np.ptp(x['return'][sl])>1: continue
        if 'pump_pwm' in x and (not np.isfinite(x['pump_pwm'][sl]).all() or np.ptp(x['pump_pwm'][sl])>3): continue
        w=np.maximum(0,np.minimum(t[sl]+d[sl],minute+60)-np.maximum(t[sl],minute))
        if abs(w.sum()-60)>0.001: continue
        def avg(key):
            if key not in x or not np.isfinite(x[key][sl]).all(): return None
            return float(np.average(x[key][sl],weights=w))
        row=dict(installation_id=setup['installation_id'],model=cfg['model'],mode='heating',defrost=0,buh=0,
                 steady=1,power_source='metered',frequency_hz=avg('frequency'),outside_c=avg('outside'),
                 supply_c=avg('supply'),return_c=avg('return'),power_w=avg('power'),water_factor=cfg['water_factor'],
                 measured_flow_lh=avg('flow'),pump_pwm=avg('pump_pwm'),minute_index=(minute-first)//60)
        try: vf.inputs(row)
        except (ValueError,TypeError,KeyError): continue
        if reference and (row['measured_flow_lh'] is None or row['measured_flow_lh']<=0): continue
        out.append(row)
    return out


def export_csv(rows):
    f=io.StringIO(); writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    return f.getvalue()


def train_csv(text, model, method='thermal'):
    if not isinstance(text,str) or len(text)>12_000_000: raise ValueError('CSV limit 12 MB')
    reader=csv.DictReader(io.StringIO(text))
    if not set(FIELDS[:13]) <= set(reader.fieldnames or []): raise ValueError('Missing VFM CSV fields')
    rows=list(reader)
    if len(rows)>100000: raise ValueError('CSV limit 100,000 rows')
    artifact=vf.fit(rows,model,method)
    # Do not persist contributor identities or raw uploaded rows.
    for i,report in enumerate(artifact['validation']): report['installation_id']=str(i+1)
    core.setmeta('vfm_model:'+model+':'+method,artifact)
    return artifact


def report(cfg,a,b,setup,method='thermal'):
    if method not in ('thermal','hydraulic','hybrid'): raise ValueError('Unknown method')
    rows=observations(cfg,a,b,setup,reference=False)
    artifact=core.getmeta('vfm_model:'+cfg['model']+':'+method)
    points=[]
    if artifact:
        for row in rows:
            p=vf.predict(row,artifact)
            points.append({'minute_index':row['minute_index'],'measured_flow_lh':row['measured_flow_lh'],**p})
    valid=[p for p in points if p['flow_lh'] is not None]
    return {'eligible_minutes':len(rows),'predicted_minutes':len(valid),'window_minutes':int((b-a)//60),
            'model':artifact,'latest':points[-1] if points else None,'points':points,
            'mean_flow_lh':float(np.mean([p['flow_lh'] for p in valid])) if valid else None}

"""Read-only current HA snapshot; no historical values mixed into live KPIs."""
from core import convert,parse_time,local_iso,now,ROLES
import math

def snapshot(cfg,states,at=None):
    at=now() if at is None else at
    by={s['entity_id']:s for s in states}
    values={}
    for role,m in cfg['mapping'].items():
        if role not in ROLES:continue
        s=by.get(m['entity'],{});raw=s.get('attributes',{}).get(m['attribute']) if m.get('attribute') else s.get('state')
        if str(s.get('state','')).lower() in ('unknown','unavailable','none',''):raw=None
        stamp=s.get('last_reported') or s.get('last_updated') or s.get('last_changed')
        try: age=max(0,at-parse_time(stamp)) if stamp else None
        except (ValueError,TypeError):age=None
        v=convert(raw,m['unit'],role,m.get('on_value','on'))
        # Slow/contextual states can remain unchanged for long periods. A timestamp
        # is the entity timestamp, not proof of an attribute's physical freshness.
        contextual=role in ('inside','target','outside','weather_temperature','supply_target','humidity','dewpoint','air_pressure')
        status='missing' if v is None else 'state_available' if contextual else 'recent' if age is not None and age<=120 else 'age_unverified' if age is None else 'older_state'
        values[role]={'status':status,'value':v,'unit':m['unit'] if role in ('fan','eev') else ROLES[role][1],'timestamp':stamp,'age_seconds':round(age) if age is not None else None,'entity':m['entity']}
    def v(k):return values.get(k,{}).get('value')
    def usable(k):
        item=values.get(k,{})
        return item.get('value') is not None and item.get('age_seconds') is not None and item['age_seconds']<=120
    def coherent(keys):
        if not all(usable(k) for k in keys):return False
        ages=[values[k]['age_seconds'] for k in keys]
        return max(ages)-min(ages)<=60
    q=delta=pel=cop=None
    if coherent(('supply','return')):delta=v('supply')-v('return')
    if coherent(('supply','return','flow')):q=cfg['water_factor']*v('flow')*delta
    mode=cfg['buh_mode'];thermal=cfg['buh_thermal']
    if mode in ('included','none') and usable('power'):pel=v('power')
    elif mode=='separate' and coherent(('power','buh')):pel=v('power')+v('buh')
    keys=['supply','return','flow','power']+(['buh'] if mode=='separate' else [])
    if q is not None and pel is not None and pel>0 and coherent(keys):
        if mode=='none' or thermal=='inside' or (mode=='separate' and v('buh')==0):cop=q/pel
        elif mode=='separate' and thermal=='outside':cop=(q+v('buh'))/pel
    return {'timestamp':local_iso(at),'measurements':values,'thermal_w':q,'delta_t':delta,'system_power_w':pel,'system_cop':cop,'max_age_seconds':120,'max_skew_seconds':60}

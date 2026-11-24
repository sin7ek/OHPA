"""Read-only HA REST history collection and optional regional weather."""
import os, time, datetime as dt, threading
import httpx
from core import *
LOCK=threading.Lock()
WAKE=threading.Event()
STOP=threading.Event()
HA_URL=os.getenv('HA_URL','').rstrip('/')
HA_TOKEN=os.getenv('HA_TOKEN','')

def ha_get(path,params=None):
    if not HA_URL or not HA_TOKEN:raise RuntimeError('HA_URL and HA_TOKEN must be configured.')
    with httpx.Client(timeout=90,follow_redirects=False) as c:
        response=c.get(HA_URL+path,params=params,headers={'Authorization':'Bearer '+HA_TOKEN,'Accept':'application/json'})
        if response.status_code!=200:raise RuntimeError(f'Home Assistant API returned HTTP {response.status_code}')
        return response.json()

def entities():
    rows=ha_get('/api/states');out=[]
    for x in rows:
        eid=x['entity_id'];attrs=x.get('attributes',{})
        if eid.split('.')[0] not in ('sensor','binary_sensor','climate','input_number','input_boolean','number','weather','switch'):continue
        # Do not expose arbitrary HA attributes, credentials or config to the browser.
        aa={k:v for k,v in attrs.items() if isinstance(v,(float,int)) and not isinstance(v,bool) and not any(s in k.lower() for s in ('token','password','secret','key'))}
        out.append({'entity_id':eid,'name':attrs.get('friendly_name',eid),'state':str(x.get('state',''))[:150],'unit':attrs.get('unit_of_measurement',''),'device_class':attrs.get('device_class',''),'attributes':aa})
    return sorted(out,key=lambda x:x['entity_id'])

def fetch_history(maps,a,b):
    ids=sorted({v['entity'] for k,v in maps})
    payload=ha_get('/api/history/period/'+iso(a),{'filter_entity_id':','.join(ids),'end_time':iso(b),'significant_changes_only':'0'})
    if not isinstance(payload,list):raise RuntimeError('Unexpected HA history format')
    by={}
    for events in payload:
        if not events:continue
        eid=events[0].get('entity_id')
        if eid:by[eid]=events
    saved=0
    for role,m in maps:
        records=by.get(m['entity'],[]);rows=[]
        for e in records:
            stamp=e.get('last_updated') or e.get('last_changed')
            if not stamp:continue
            t=parse_time(stamp)
            if t>b:continue
            raw=e.get('attributes',{}).get(m['attribute']) if m.get('attribute') else e.get('state')
            rows.append((max(t,a),convert(raw,m['unit'],role,m.get('on_value','on'))))
        if rows:
            # If recorder has no initial snapshot, do not imply coverage before the first record.
            rows.sort(key=lambda x:x[0]);start=max(a,rows[0][0]);add_series(series_id(role,m),rows,start,b);saved+=1
        # Empty but successful query: advance scan cursor, without fabricating coverage.
        setmeta('scan:'+series_id(role,m),b)
    return saved

def weather(cfg,m):
    regional={k:v for k,v in m.items() if v.get('source')=='regional'}
    if not regional:return
    last=getmeta('weather_last',0)
    if now()-last<3600 and all(series_end(series_id(k,v)) is not None for k,v in regional.items()):return
    r=cfg['regional'];start=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=cfg['backfill_days']+1)).date().isoformat();end=dt.datetime.now(dt.timezone.utc).date().isoformat()
    params={'latitude':r['latitude'],'longitude':r['longitude'],'hourly':','.join(REGIONAL[k] for k in regional),'timezone':'GMT','wind_speed_unit':'ms','start_date':start,'end_date':end}
    with httpx.Client(timeout=40) as c:
        response=c.get('https://historical-forecast-api.open-meteo.com/v1/forecast',params=params)
        # Historical forecast API may lag. Use forecast API's recent past when needed.
        if response.status_code!=200:
            params.pop('start_date');params.pop('end_date');params['past_days']=min(cfg['backfill_days']+1,9);params['forecast_days']=1
            response=c.get('https://api.open-meteo.com/v1/forecast',params=params)
        if response.status_code!=200:raise RuntimeError(f'Open-Meteo returned HTTP {response.status_code}')
        hourly=response.json()['hourly']
    times=[parse_time(t+'+00:00') for t in hourly['time']];cut=now()
    for k,v in regional.items():
        shift=3600 if k=='solar' else 0
        # Radiation is the preceding-hour mean; other values are hourly model snapshots.
        rows=[(t-shift,convert(val,v['unit'],k)) for t,val in zip(times,hourly[REGIONAL[k]]) if t<=cut]
        if rows:
            a=rows[0][0];b=min(cut,rows[-1][0]+3600) if k!='solar' else rows[-1][0]+3600
            add_series(series_id(k,v),rows,a,b)
    setmeta('weather_last',now())

def collect_once():
    if not LOCK.acquire(blocking=False):return
    try:
        cfg=config();m=mapping(cfg);current=now()-15;errors=[];pending=0
        groups={}
        for role,v in m.items():
            if v.get('source')=='regional':continue
            sid=series_id(role,v);end=getmeta('scan:'+sid,series_end(sid))
            # 5 minute overlap catches recorder lag; initial backfill limited by user settings.
            a=max(current-cfg['backfill_days']*86400,end-300 if end else 0)
            # Shared 1h boundaries group requests for entities with similar progress.
            a=max(current-cfg['backfill_days']*86400, math.floor(a/300)*300)
            if a>=current:continue
            groups.setdefault(a,[]).append((role,v))
        for a,items in groups.items():
            b=min(current,a+3600)
            # Limit each request to 8 entities/roles. Avoid monopolizing recorder.
            for i in range(0,len(items),8):
                batch=items[i:i+8]
                try:
                    saved=fetch_history(batch,a,b)
                    if saved<len(batch):errors.append(f'{len(batch)-saved} mapped series returned no history in {iso(a)}')
                    if b<current-300:pending+=len(batch)
                except Exception as exc:errors.append(str(exc)[:250])
                if STOP.is_set():break
        try:weather(cfg,m)
        except Exception as exc:errors.append('Regional weather: '+str(exc)[:250])
        setmeta('collector',{'last_attempt':local_iso(now()),'errors':errors[:15],'backfill_pending_series':pending,'mapped_series':len(m)})
    finally:LOCK.release()
    return pending

def worker():
    while not STOP.is_set():
        try:pending=collect_once() or 0
        except Exception as exc:
            setmeta('collector',{'last_attempt':local_iso(now()),'errors':[type(exc).__name__]});pending=0
        # Backfill steadily, not a tight loop. Live collection defaults to two minutes.
        seconds=15 if pending else config()['poll_seconds']
        WAKE.wait(seconds);WAKE.clear()

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
        cfg=config();m=mapping(cfg);current=now()-15;errors=[];missing=[];pending=0
        import rooms
        extra=rooms.mappings(rooms.normalize(getmeta('rooms_profile',[])))
        # Keep room series separate from global role selection, deduplicate identical canonical series.
        pairs=list(m.items());seen={series_id(k,v) for k,v in pairs}
        for _,_,role,v in extra:
            sid=series_id(role,v)
            if sid not in seen:pairs.append((role,v));seen.add(sid)
        floor=current-cfg['backfill_days']*86400
        anchor=math.floor(current/3600)*3600
        live={};historical={}
        for role,v in pairs:
            if v.get('source')=='regional':continue
            sid=series_id(role,v)
            cursor=getmeta('live_v2:'+sid)
            # First retrieve the most recent hour; old forward scan cursors remain untouched.
            start=max(floor,anchor-3600 if cursor is None else cursor-300)
            start=max(floor,math.floor(start/300)*300)
            live.setdefault(start,[]).append((role,v))
            # A separate backwards cursor records successful queries, including empty history.
            old=getmeta('back_v2:'+sid)
            end=min(anchor-3600,old) if old is not None else anchor-3600
            if end>floor:
                historical.setdefault(end,[]).append((role,v))
        def run_batch(items,a,b,key,cursor):
            def attempt(batch):
                if STOP.is_set():return
                try:
                    saved=fetch_history(batch,a,b)
                    for role,v in batch:setmeta(key+series_id(role,v),cursor)
                    if saved<len(batch):missing.append(f'{len(batch)-saved} mapped series without history in {iso(a)}')
                except Exception as exc:
                    if len(batch)>8 and not STOP.is_set():
                        mid=len(batch)//2;attempt(batch[:mid]);attempt(batch[mid:])
                    else:errors.append(str(exc)[:250])
            size=24 if b-a<=10800 else 8
            for i in range(0,len(items),size):attempt(items[i:i+size])
        # Always prioritize live collection over older backfill.
        for a,items in live.items():
            if a<current:run_batch(items,a,current,'live_v2:',current)
        for b,items in historical.items():
            a=max(floor,b-3*3600)
            # Do not advance historical import until the first live query succeeds.
            items=[(k,v) for k,v in items if getmeta('live_v2:'+series_id(k,v)) is not None]
            if items:run_batch(items,a,b,'back_v2:',a)
        progress={}
        for role,v in pairs:
            if v.get('source')=='regional':continue
            sid=series_id(role,v);old=getmeta('back_v2:'+sid)
            live_end=getmeta('live_v2:'+sid)
            if old is None or old>floor or live_end is None:pending+=1
            progress[role+':'+sid.split(':')[-1] if sid not in {series_id(k,v) for k,v in m.items()} else role]=round(100*max(0,min(1,(current-(old if old is not None else current))/(current-floor))),1) if live_end is not None else 0
        try:weather(cfg,m)
        except Exception as exc:errors.append('Regional weather: '+str(exc)[:250])
        setmeta('collector',{'last_attempt':local_iso(now()),'errors':errors[:15],'missing_history':missing[:15],'backfill_pending_series':pending,'backfill_scan_pct':progress,'mapped_series':len(pairs)})
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

_registry_cache=None
_registry_cached_at=0
_registry_lock=threading.Lock()
def room_registry(refresh=False):
    global _registry_cache,_registry_cached_at
    with _registry_lock:
        if not refresh and _registry_cache is not None and time.monotonic()-_registry_cached_at<300:return _registry_cache
        result=_read_room_registry()
        _registry_cache=result;_registry_cached_at=time.monotonic()
        return result

def _read_room_registry():
    """Read-only registry queries. No service calls; no token returned to UI."""
    import json
    from websockets.sync.client import connect
    if not HA_URL or not HA_TOKEN:raise RuntimeError('HA connection not configured')
    url=HA_URL.replace('https://','wss://',1) if HA_URL.startswith('https://') else HA_URL.replace('http://','ws://',1)
    with connect(url+'/api/websocket',open_timeout=10,close_timeout=3,max_size=32*1024*1024) as ws:
        ws.recv(timeout=10);ws.send(json.dumps({'type':'auth','access_token':HA_TOKEN}))
        if json.loads(ws.recv(timeout=10)).get('type')!='auth_ok':raise RuntimeError('HA WebSocket authentication failed')
        result={}
        for i,kind in enumerate(('config/area_registry/list','config/device_registry/list','config/entity_registry/list','config/floor_registry/list'),1):
            ws.send(json.dumps({'id':i,'type':kind}));r=json.loads(ws.recv(timeout=20))
            if not r.get('success') and i!=4:raise RuntimeError('HA registry access unavailable: '+kind)
            result[kind]=r.get('result',[]) if r.get('success') else []
    states={e['entity_id']:e for e in entities()}
    areas=[{k:x.get(k) for k in ('area_id','name','floor_id')} for x in result['config/area_registry/list']]
    devices=[{k:x.get(k) for k in ('id','name','name_by_user','area_id','model','manufacturer')} for x in result['config/device_registry/list']]
    ents=[{**states[x['entity_id']],'device_id':x.get('device_id'),'area_id':x.get('area_id')} for x in result['config/entity_registry/list'] if x.get('entity_id') in states and not x.get('disabled_by')]
    return {'available_entities':list(states.values()),'areas':areas,'devices':devices,'entities':ents,'floors':[{k:x.get(k) for k in ('floor_id','name','level')} for x in result['config/floor_registry/list']]}

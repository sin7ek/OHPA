import os, secrets, datetime as dt, threading, base64, json, math
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from core import *
import collector
import profiles
import live
import building
import ventilation
import rooms
import research_flow

INGRESS=os.getenv('OHPA_INSTALL_MODE','docker')=='ha_app'
ADMIN=os.getenv('ADMIN_PASSWORD','');MCP_SECRET=os.getenv('MCP_SECRET','')
# Preserve existing explicitly configured Docker MCP installations. HA app is ingress-only.
MCP_ENABLED=not INGRESS and os.getenv('MCP_ENABLED','auto').lower() not in ('0','false','no','off') and bool(MCP_SECRET)
if not INGRESS and (len(ADMIN)<16 or ADMIN.startswith('replace_')):
    raise RuntimeError('Set a random ADMIN_PASSWORD (>=16 chars)')
if MCP_ENABLED and (len(MCP_SECRET)<24 or MCP_SECRET.startswith('replace_') or ADMIN==MCP_SECRET or not all(ch.isalnum() or ch in '-_' for ch in MCP_SECRET)):
    raise RuntimeError('Set a distinct URL-safe MCP_SECRET (>=24 chars), or disable MCP')
init()

def range_(start=None,end=None,hours=24,max_days=32):
    b=min(parse_time(end) if end else now(),now());a=parse_time(start) if start else b-float(hours)*3600
    if not (0<b-a<=max_days*86400):raise ValueError(f'Choose a positive time range up to {max_days} days.')
    return a,b

def compact(s):return {k:v for k,v in s.items() if k!='cycles'}
def compare(before_start,before_end,after_start,after_end):
    a,b=range_(before_start,before_end);c,d=range_(after_start,after_end);cfg=config()
    return {'before':compact(metrics(cfg,a,b)),'after':compact(metrics(cfg,c,d)),'warning':'Unadjusted comparison. Match outdoor temperature, humidity, wind, solar and indoor temperature before attributing change to an intervention.'}

def change_list():
    with db() as c:return [dict(t=local_iso(row['t']),note=row['note']) for row in c.execute('SELECT * FROM changes ORDER BY t DESC LIMIT 200')]

# MCP uses a distinct secret URL; tools expose analytics only, not HA API or credentials.
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
hosts=[x.strip() for x in os.getenv('MCP_ALLOWED_HOSTS','localhost:*,127.0.0.1:*').split(',') if x.strip()]
# Exact path mount plus host validation; reverse proxy must forward the approved public host.
mcp=FastMCP('HeatPump Analytics',stateless_http=True,json_response=True,streamable_http_path='/',transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,allowed_hosts=hosts,allowed_origins=[]))
@mcp.tool()
def get_performance(start: str|None=None,end: str|None=None,hours:float=24)->dict:
    """Read-only: net heat, electricity, coverage, COP, temperatures, comfort, compressor and defrost metrics. ISO times or hours lookback. No interpolation across unobserved intervals."""
    a,b=range_(start,end,hours);return compact(metrics(config(),a,b))
@mcp.tool()
def get_hourly_performance(start:str|None=None,end:str|None=None,hours:float=24)->dict:
    """Read-only hourly time-aligned KPIs, up to 7 days per request. Local timestamps include UTC offsets."""
    a,b=range_(start,end,hours)
    if b-a>7*86400:raise ValueError('Maximum 7 days for hourly MCP output.')
    return {'rows':[compact(h) for h in hourly(config(),a,b)]}
@mcp.tool()
def get_defrost_analysis(start:str|None=None,end:str|None=None,hours:float=24)->dict:
    """Read-only defrost periods, observed starts, negative heat, duration and coverage."""
    a,b=range_(start,end,hours);s=metrics(config(),a,b);return {k:v for k,v in s.items() if k.startswith('defrost') or k in ('start','end','cycles','warnings','weather_sources','coverage_pct')}
@mcp.tool()
def compare_periods(before_start:str,before_end:str,after_start:str,after_end:str)->dict:
    """Read-only before/after KPI comparison, not weather-normalized and not causal."""
    return compare(before_start,before_end,after_start,after_end)
@mcp.tool()
def get_heat_loss_model(start:str|None=None,end:str|None=None,hours:float=168)->dict:
    """Read-only exploratory steady-hour regression, requiring sufficient temperature range and coverage. Not certified heat-loss calculation."""
    a,b=range_(start,end,hours,max_days=90);return heat_loss(config(),a,b)
@mcp.tool()
def get_building_profile()->dict:
    """Read-only optional dwelling profile and partial envelope estimate; no certified heat loss."""
    p=building.normalize(getmeta('building_profile',{}));return {'profile':p,'estimate':building.estimate(p)}
@mcp.tool()
def get_measurement_setup()->dict:
    """Read-only mapping, units, collector health, weather source and logged interventions; excludes HA credentials."""
    cfg=config();return {'roles':{k:{'entity':v['entity'],'attribute':v.get('attribute',''),'unit':v['unit'],'source':v.get('source','HA')} for k,v in mapping(cfg).items()},'buh_mode':cfg['buh_mode'],'buh_thermal':cfg['buh_thermal'],'heat_only':cfg['heat_only'],'collector':getmeta('collector',{}),'interventions':change_list()}
@mcp.tool()
def get_weather_defrost_analysis(start:str|None=None,end:str|None=None,hours:float=168)->dict:
    """Read-only: observed defrost exposure and negative heat by outdoor temperature band, with humidity, dew point, wind and solar where mapped."""
    a,b=range_(start,end,hours);return weather_defrost(config(),a,b)
@mcp.tool()
def get_comfort_analysis(start:str|None=None,end:str|None=None,hours:float=24)->dict:
    """Observed indoor temperature vs target: degree-hours below/above target, mean and peak deficit, percent within ±0.5 °C and joint coverage. No extrapolation."""
    a,b=range_(start,end,hours);s=metrics(config(),a,b)
    return {k:v for k,v in s.items() if k.startswith('comfort_') or k in ('start','end','hours')}
@mcp.tool()
def get_flow_comparison(start:str|None=None,end:str|None=None,hours:float=24)->dict:
    """Read-only synchronized primary/reference flow comparison, by flow band and defrost status. No calibration or substitution."""
    a,b=range_(start,end,hours);s=metrics(config(),a,b);return {'start':s['start'],'end':s['end'],'flow_comparison':s['flow_comparison']}
@mcp.tool()
def get_latest_measurements()->dict:
    """Read-only: latest locally collected sensor values with their individual timestamps; not a live HA request."""
    return latest_measurements(config())
mcp_app=mcp.streamable_http_app()
@asynccontextmanager
async def lifespan(app):
    collector.STOP.clear();t=threading.Thread(target=collector.worker,daemon=True);t.start()
    try:
        if MCP_ENABLED:
            async with mcp.session_manager.run():yield
        else:yield
    finally:collector.STOP.set();collector.WAKE.set()
VERSION=(Path(__file__).parent/'VERSION').read_text().strip()
REVISION=os.getenv('OHPA_REVISION','unknown')
app=FastAPI(title='HeatPump Analytics',version=VERSION,lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
MCP_PATH='/mcp/'+MCP_SECRET
if MCP_ENABLED:app.mount(MCP_PATH,mcp_app)
@app.middleware('http')
async def protect(request:Request,call_next):
    path=request.url.path
    if INGRESS:
        if not request.client or request.client.host!='172.30.32.2':
            return JSONResponse({'detail':'Ingress only'},status_code=403)
    if path=='/health':return await call_next(request)
    if MCP_ENABLED and path in (MCP_PATH,MCP_PATH+'/'):return await call_next(request)
    if path=='/mcp' or path.startswith('/mcp/'):return JSONResponse({'detail':'Not found'},status_code=404)
    if not INGRESS:
        auth=request.headers.get('authorization','')
        expected='Basic '+base64.b64encode(('admin:'+ADMIN).encode()).decode()
        if not secrets.compare_digest(auth,expected):return JSONResponse({'detail':'Authentication required'},status_code=401,headers={'WWW-Authenticate':'Basic realm="HeatPump Analytics"','Cache-Control':'no-store'})
    if request.method in ('POST','PUT','DELETE','PATCH') and request.headers.get('x-analytics-ui')!='1':return JSONResponse({'detail':'Missing UI request header'},status_code=403)
    response=await call_next(request);response.headers['Cache-Control']='no-store';response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='SAMEORIGIN' if INGRESS else 'DENY';return response
@app.get('/health')
def health():return {'status':'ok','version':VERSION,'revision':REVISION}
@app.get('/')
def index(request:Request):
    from fastapi.responses import HTMLResponse
    from html import escape
    page=(Path(__file__).parent/'static/index.html').read_text()
    base='/'
    if INGRESS:
        import re
        path=request.headers.get('x-ingress-path','')
        if not re.fullmatch(r'/api/hassio_ingress/[A-Za-z0-9_-]+/?',path):
            return JSONResponse({'detail':'Missing or invalid ingress path'},status_code=400)
        base=path.rstrip('/')+'/'
    return HTMLResponse(page.replace('__OHPA_BASE__',escape(base,quote=True)).replace('__OHPA_VERSION__',escape(VERSION)).replace('__OHPA_REVISION__',escape(REVISION[:12])).replace('__OHPA_MCP_HIDDEN__','' if MCP_ENABLED else 'hidden style="display:none"'),headers={'Cache-Control':'no-store'})
app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
@app.get('/api/config')
def cfg():return {'config':config(),'roles':{k:{'label':v[0],'unit':v[1],'mode':v[2],'required':v[3],'units':v[4]} for k,v in ROLES.items()},'timezone':str(TZ)}
@app.get('/api/entities')
def ent():
    try:return collector.entities()
    except Exception as e:raise HTTPException(502,str(e)[:250])
@app.post('/api/profile-preview')
async def profile_preview(request:Request):
    raw=await request.json()
    try:return profiles.proposals(raw['profile'],raw['prefix'],collector.entities(),raw.get('existing',{}),raw.get('model','generic'))
    except (ValueError,KeyError,TypeError) as e:raise HTTPException(400,str(e))
    except Exception as e:raise HTTPException(502,str(e)[:250])
@app.post('/api/language')
async def language(request:Request):
    raw=await request.json()
    if raw.get('language') not in ('nl','en'):raise HTTPException(400,'Invalid language')
    with db() as conn:
        row=conn.execute('SELECT body FROM config WHERE id=1').fetchone()
        value=json.loads(row[0]);value['language']=raw['language']
        conn.execute('UPDATE config SET body=? WHERE id=1',(json.dumps(value),))
    return {'ok':True}
@app.get('/api/rooms')
def rooms_profile():
    return {'rooms':rooms.normalize(getmeta('rooms_profile',[]))}
@app.post('/api/rooms')
async def save_rooms(request:Request):
    try:
        p=rooms.normalize(await request.json());setmeta('rooms_profile',p);collector.WAKE.set();return {'rooms':p}
    except (ValueError,TypeError,KeyError,AttributeError) as e:raise HTTPException(400,str(e))
@app.get('/api/rooms/registry')
def rooms_registry(refresh:bool=False):
    try:return collector.room_registry(refresh)
    except Exception:raise HTTPException(502,'HA registry unavailable; manual configuration remains available.')
@app.get('/api/rooms/progress')
def rooms_progress():
    cfg=config();current=now()-15;floor=current-cfg['backfill_days']*86400
    result=[]
    for room in rooms.normalize(getmeta('rooms_profile',[])):
        sensors=[]
        for key,m in room['sensors'].items():
            role=rooms.FIELDS[key][0];sid=series_id(role,m)
            old=getmeta('back_v2:'+sid);end=getmeta('live_v2:'+sid)
            scanned=round(100*max(0,min(1,(current-(old if old is not None else current))/(current-floor))),1) if end is not None else 0
            sensors.append({'key':key,'scan_pct':scanned,'last_collected':local_iso(end) if end is not None else None})
        result.append({'id':room['id'],'sensors':sensors})
    return {'rooms':result,'backfill_days':cfg['backfill_days'],'warning':'Scan progress, not valid measurement coverage.'}
@app.get('/api/rooms/analysis')
def rooms_analysis(hours:float=24):
    try:
        a,b=range_(hours=hours,max_days=7);return rooms.report(config(),rooms.normalize(getmeta('rooms_profile',[])),a,b)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/rooms/co2')
def room_co2(room_id:str,outdoor:float,hours:float=168):
    try:
        a,b=range_(hours=hours,max_days=7)
        room=next((x for x in rooms.normalize(getmeta('rooms_profile',[])) if x['id']==room_id),None)
        if room is None:raise ValueError('Unknown room')
        return ventilation.candidates(rooms.co2_config(config(),room),a,b,outdoor)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/building')
def building_profile():
    p=building.normalize(getmeta('building_profile',{}));return {'profile':p,'estimate':building.estimate(p),'saved_at':getmeta('building_saved_at')}
@app.post('/api/building')
async def save_building(request:Request):
    try:
        p=building.normalize(await request.json());stamp=local_iso(now())
        with db() as conn:
            conn.executemany('INSERT OR REPLACE INTO meta VALUES(?,?)',[('building_profile',json.dumps(p)),('building_saved_at',json.dumps(stamp))])
        persisted=building.normalize(getmeta('building_profile',{}));return {'profile':persisted,'estimate':building.estimate(persisted),'saved_at':getmeta('building_saved_at')}
    except (ValueError,TypeError,KeyError,AttributeError) as e:raise HTTPException(400,str(e))
@app.get('/api/ventilation-fan')
def ventilation_fan(start:str|None=None,end:str|None=None,hours:float=24):
    try:
        a,b=range_(start,end,hours);return ventilation.fan_report(config(),building.normalize(getmeta('building_profile',{})),a,b)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/co2-decay')
def co2_decay(start:str,end:str,outdoor:float):
    try:
        a,b=range_(start,end);return ventilation.decay(config(),a,b,outdoor)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/co2-candidates')
def co2_candidates(outdoor:float,hours:float=72):
    try:
        a,b=range_(hours=hours,max_days=7)
        return ventilation.candidates(config(),a,b,outdoor)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/live')
def live_snapshot():
    try:return live.snapshot(config(),collector.ha_get('/api/states'))
    except Exception as e:raise HTTPException(502,str(e)[:250])
@app.get('/api/status')
def status():
    c=config();m=mapping(c);return {'collector':getmeta('collector',{}),'series':{k:{'last_collected':local_iso(e) if (e:=series_end(series_id(k,v))) else None,'source':v.get('source','HA')} for k,v in m.items()},'now':local_iso(now())}
@app.post('/api/config')
async def update(request:Request):
    raw=await request.json()
    try:
        c=dict(DEFAULT);c.update({k:raw[k] for k in DEFAULT if k in raw});c['mapping']={}
        for k,m in raw.get('mapping',{}).items():
            if k not in ROLES or not m.get('entity'):continue
            if m['unit'] not in ROLES[k][4]:raise ValueError('Invalid unit for '+k)
            if not isinstance(m['entity'],str) or len(m['entity'])>250 or '.' not in m['entity']:raise ValueError('Invalid entity ID')
            c['mapping'][k]={'entity':m['entity'],'attribute':str(m.get('attribute',''))[:100],'unit':m['unit'],'on_value':str(m.get('on_value','on'))[:100]}
        if c['language'] not in ('nl','en') or c['model'] not in profiles.MODELS or c['integration_profile'] not in ('manual',*profiles.PROFILES):raise ValueError('Invalid installation profile')
        c['entity_prefix']=str(c['entity_prefix'])[:100]
        if any(c[k] not in FLOW_PROFILES for k in ('flow_profile','reference_flow_profile')):raise ValueError('Invalid flow meter profile')
        primary=c['mapping'].get('flow') or c['mapping'].get('flow_counter');reference=c['mapping'].get('reference_flow') or c['mapping'].get('reference_flow_counter')
        if primary and reference and (primary['entity'],primary['attribute'])==(reference['entity'],reference['attribute']):raise ValueError('Primary and reference must be distinct measurements')
        if c['buh_mode'] not in ('unknown','separate','included','none') or c['buh_thermal'] not in ('unknown','inside','outside','none'):raise ValueError('Invalid BUH mode')
        c['heat_only']=bool(c['heat_only']);c['backfill_days']=int(c['backfill_days']);c['poll_seconds']=int(c['poll_seconds']);c['counter_max_gap']=int(c['counter_max_gap']);c['hz_threshold']=float(c['hz_threshold']);c['max_hz']=float(c['max_hz']);c['water_factor']=float(c['water_factor'])
        if not (1<=c['backfill_days']<=9 and 30<=c['poll_seconds']<=3600 and 30<=c['counter_max_gap']<=1800 and 0<c['hz_threshold']<=c['max_hz']<=300 and 0.5<=c['water_factor']<=1.5):raise ValueError('Configuration values out of range')
        rr=c['regional'];c['regional']={'enabled':bool(rr.get('enabled')),'latitude':None,'longitude':None}
        if rr.get('enabled'):
            lat=float(rr['latitude']);lon=float(rr['longitude'])
            if not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Invalid regional coordinates')
            c['regional'].update(latitude=lat,longitude=lon)
        c['notes']=str(c['notes'])[:3000];save_config(c);collector.WAKE.set();return {'ok':True}
    except (ValueError,KeyError,TypeError) as e:raise HTTPException(400,str(e))
@app.post('/api/collect')
def trigger():collector.WAKE.set();return {'queued':True}
@app.get('/api/research/settings')
def vfm_settings():
    return research_flow.settings()
@app.post('/api/research/settings')
async def vfm_config(request:Request):
    raw=await request.json()
    try:return research_flow.configure(raw.get('enabled'),raw.get('confirmed'))
    except (ValueError,TypeError) as e:raise HTTPException(400,str(e))
@app.get('/api/research/export')
def vfm_export(hours:float=24):
    try:
        a,b=range_(hours=hours,max_days=7)
        rows=research_flow.observations(config(),a,b,research_flow.settings())
        return {'row_count':len(rows),'csv':research_flow.export_csv(rows)}
    except ValueError as e:raise HTTPException(400,str(e))
@app.post('/api/research/train')
def vfm_train(raw:dict):
    try:
        setup=research_flow.settings()
        if not setup.get('enabled') or not setup.get('confirmed'):raise ValueError('Enable research and confirm measurement boundaries first')
        return research_flow.train_csv(raw.get('csv'),config()['model'],raw.get('method','thermal'))
    except (ValueError,TypeError,KeyError) as e:raise HTTPException(400,str(e))
@app.get('/api/research/report')
def vfm_report(hours:float=24,method:str='thermal'):
    try:
        a,b=range_(hours=hours,max_days=7)
        return research_flow.report(config(),a,b,research_flow.settings(),method)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/metrics')
def report(start:str|None=None,end:str|None=None,hours:float=24):
    try:a,b=range_(start,end,hours);return metrics(config(),a,b)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/hourly')
def hour_report(start:str|None=None,end:str|None=None,hours:float=24):
    try:a,b=range_(start,end,hours);return [compact(h) for h in hourly(config(),a,b)]
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/model')
def model(start:str|None=None,end:str|None=None,hours:float=168):
    try:a,b=range_(start,end,hours,max_days=90);return heat_loss(config(),a,b)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/compare')
def cmp(before_start:str,before_end:str,after_start:str,after_end:str):
    try:return compare(before_start,before_end,after_start,after_end)
    except ValueError as e:raise HTTPException(400,str(e))
@app.get('/api/changes')
def changes():return change_list()
def intervention_values(x):
    try:
        t=parse_time(x['time'])
        note=x['note']
        if not math.isfinite(t) or not isinstance(note,str) or not note.strip() or len(note.strip())>1000: raise ValueError()
        return t,note.strip()
    except (ValueError,TypeError,KeyError,OverflowError): raise HTTPException(400,'Time and note required (max 1000 characters).')

@app.post('/api/changes')
async def note(request:Request):
    t,s=intervention_values(await request.json())
    with db() as c:
        try:c.execute('INSERT INTO changes VALUES(?,?)',(t,s))
        except sqlite3.IntegrityError:raise HTTPException(409,'An intervention already exists at this time.')
    return {'ok':True}

def intervention_original(x):
    try:
        t=parse_time(x['original_time'])
        if not math.isfinite(t) or not isinstance(x['original_note'],str):raise ValueError()
        return t,x['original_note']
    except (ValueError,TypeError,KeyError,OverflowError):raise HTTPException(400,'Original intervention required.')

@app.post('/api/changes/edit')
async def edit_change(request:Request):
    x=await request.json()
    old,original=intervention_original(x);t,s=intervention_values(x)
    with db() as c:
        try:r=c.execute('UPDATE changes SET t=?,note=? WHERE t=? AND note=?',(t,s,old,original))
        except sqlite3.IntegrityError:raise HTTPException(409,'An intervention already exists at this time.')
        if r.rowcount!=1:raise HTTPException(409,'Intervention changed or deleted; refresh the log.')
    return {'ok':True}

@app.post('/api/changes/delete')
async def delete_change(request:Request):
    old,original=intervention_original(await request.json())
    with db() as c:
        r=c.execute('DELETE FROM changes WHERE t=? AND note=?',(old,original))
        if r.rowcount!=1:raise HTTPException(409,'Intervention changed or deleted; refresh the log.')
    return {'ok':True}

@app.get('/api/weather-defrost')
def weather_report(start:str|None=None,end:str|None=None,hours:float=168):
    try:a,b=range_(start,end,hours);return weather_defrost(config(),a,b)
    except ValueError as e:raise HTTPException(400,str(e))

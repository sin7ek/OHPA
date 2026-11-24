"""Deterministic event-aligned heat pump analytics; UTC seconds internally."""
import os, json, math, sqlite3, hashlib, time, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo
from contextlib import contextmanager
import numpy as np

TZ=ZoneInfo(os.getenv('TZ','Europe/Amsterdam'))
DATA=Path(os.getenv('DATA_DIR','/data'))
FLOW_UNITS=['L/h','l/hr','L/min','L/s','m³/h','m³/min','m³/s']
FLOW_PROFILES=('manual','aquaro','esphome','electropaultje','openquatt','generic_mqtt','modbus_mbus')
COUNTER_ROLES=('flow_counter','reference_flow_counter')
# canonical units and role descriptions. Power boundary is explicit in settings.
ROLES={
 'inside':('Indoor temperature','°C','basic',True,['°C','°F','K']),
 'target':('Indoor target','°C','basic',False,['°C','°F','K']),
 'outside':('Outdoor temperature','°C','basic',True,['°C','°F','K']),
 'supply':('Supply water temperature','°C','basic',True,['°C','°F','K']),
 'return':('Return water temperature','°C','basic',True,['°C','°F','K']),
 'flow':('Water flow rate','L/h','basic',True,FLOW_UNITS),
 'flow_counter':('Cumulative water volume (alternative to flow)','L','basic',False,['L','m³']),
 'reference_flow':('Reference flow rate','L/h','expert',False,FLOW_UNITS),
 'reference_flow_counter':('Reference cumulative volume','L','expert',False,['L','m³']),
 'power':('Heat pump electrical input','W','basic',True,['W','kW']),
 'buh':('Separate backup heater electrical input','W','basic',False,['W','kW']),
 'frequency':('Compressor frequency','Hz','basic',False,['Hz']),
 'defrost':('Defrost active','on/off','basic',False,['on/off']),
 'supply_target':('Supply water target','°C','expert',False,['°C','°F','K']),
 'thermal':('Measured thermal output (cross-check)','W','expert',False,['W','kW']),
 'cop':('Reported COP (cross-check)','ratio','expert',False,['ratio']),
 'humidity':('Outdoor relative humidity','%','expert',False,['%']),
 'dewpoint':('Outdoor dew point','°C','expert',False,['°C','°F','K']),
 'solar':('Global solar irradiance','W/m²','expert',False,['W/m²','kW/m²']),
 'wind':('Outdoor wind speed','m/s','expert',False,['m/s','km/h','mph','kn']),
 'illuminance':('Outdoor illuminance (proxy only)','lx','expert',False,['lx','klx']),
 'weather_temperature':('Weather station outdoor temperature','°C','expert',False,['°C','°F','K']),
 'wind_direction':('Wind direction','°','expert',False,['°']),
 'wind_gust':('Wind gust speed','m/s','expert',False,['m/s','km/h','mph','kn']),
 'rain_rate':('Rain intensity','mm/h','expert',False,['mm/h']),
 'wet':('Surface wet','on/off','expert',False,['on/off']),
 'air_pressure':('Atmospheric pressure','hPa','expert',False,['hPa','mbar','Pa','kPa']),
 'pv':('PV electrical production (proxy only)','W','expert',False,['W','kW']),
 'evaporator':('Evaporator coil temperature','°C','expert',False,['°C','°F','K']),
 'evap_sat':('Refrigerant evaporating temperature','°C','expert',False,['°C','°F','K']),
 'cond_sat':('Refrigerant condensing temperature','°C','expert',False,['°C','°F','K']),
 'condenser':('Condenser sensor temperature','°C','expert',False,['°C','°F','K']),
 'discharge':('Discharge gas temperature','°C','expert',False,['°C','°F','K']),
 'suction':('Suction gas temperature','°C','expert',False,['°C','°F','K']),
 'fan':('Fan speed','rpm','expert',False,['rpm','%']),
 'eev':('Expansion valve position','steps','expert',False,['steps','%']),
 'high_pressure':('High refrigerant pressure','bar','expert',False,['bar','kPa','MPa','psi']),
 'low_pressure':('Low refrigerant pressure','bar','expert',False,['bar','kPa','MPa','psi']),
 'other_heat':('Other measured thermal heat input','W','expert',False,['W','kW']),
 'heating':('Space heating active (not DHW/cooling)','on/off','expert',False,['on/off']),
}
REGIONAL={'humidity':'relative_humidity_2m','dewpoint':'dew_point_2m','solar':'shortwave_radiation','wind':'wind_speed_10m','outside':'temperature_2m'}
DEFAULT={'language':'nl','model':'generic','integration_profile':'manual','entity_prefix':'','flow_profile':'manual','reference_flow_profile':'manual','mapping':{},'buh_mode':'unknown','buh_thermal':'unknown','heat_only':False,'max_hz':90,'hz_threshold':89,'water_factor':1.163,'backfill_days':3,'poll_seconds':120,'counter_max_gap':300,'regional':{'enabled':False,'latitude':None,'longitude':None},'notes':''}

def parse_time(s):
    if isinstance(s,(int,float)): return float(s)
    v=dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))
    if v.tzinfo is None: v=v.replace(tzinfo=TZ)
    return v.timestamp()
def iso(t): return dt.datetime.fromtimestamp(float(t),dt.timezone.utc).isoformat().replace('+00:00','Z')
def local_iso(t): return dt.datetime.fromtimestamp(float(t),TZ).isoformat()
def now(): return time.time()
@contextmanager
def db():
    DATA.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DATA/'analytics.sqlite',timeout=30)
    c.row_factory=sqlite3.Row
    try:
        c.execute('PRAGMA busy_timeout=30000')
        yield c
        c.commit()
    except Exception:
        c.rollback();raise
    finally: c.close()
def init():
    with db() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''CREATE TABLE IF NOT EXISTS config(id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(series TEXT,t REAL,value REAL, PRIMARY KEY(series,t));
        CREATE TABLE IF NOT EXISTS coverage(series TEXT,start REAL,end REAL, PRIMARY KEY(series,start,end));
        CREATE INDEX IF NOT EXISTS coverage_end ON coverage(series,end);
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS changes(t REAL PRIMARY KEY,note TEXT);''')
        c.execute('INSERT OR IGNORE INTO config VALUES(1,?)',(json.dumps(DEFAULT),))
def config():
    with db() as c: return {**DEFAULT,**json.loads(c.execute('SELECT body FROM config WHERE id=1').fetchone()[0])}
def save_config(v):
    with db() as c: c.execute('UPDATE config SET body=? WHERE id=1',(json.dumps(v),))
def setmeta(k,v):
    with db() as c:c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',(k,json.dumps(v)))
def getmeta(k,default=None):
    with db() as c:r=c.execute('SELECT value FROM meta WHERE key=?',(k,)).fetchone();return json.loads(r[0]) if r else default

def unit_norm(u):
    return str(u or '').strip().replace('³','3').replace('²','2').lower().replace(' ','')
def convert(value,unit,role,on_value='on'):
    if role in ('defrost','heating','wet'):
        if value is None or str(value).lower() in ('unknown','unavailable','none',''): return None
        return float(str(value).lower()==str(on_value).lower())
    try: x=float(value)
    except (ValueError,TypeError):return None
    if not math.isfinite(x):return None
    u=unit_norm(unit)
    if u=='°f':x=(x-32)*5/9
    elif u=='k':x-=273.15
    elif u=='kw':x*=1000
    elif u=='l/min':x*=60
    elif u=='l/s':x*=3600
    elif u=='m3/s':x*=3600000
    elif u=='m3/h':x*=1000
    elif u=='m3/min':x*=60000
    elif u=='m3':x*=1000
    elif u=='km/h':x/=3.6
    elif u=='mph':x*=0.44704
    elif u=='kn':x*=0.514444
    elif u=='kw/m2':x*=1000
    elif u=='klx':x*=1000
    elif role=='air_pressure' and u=='pa':x/=100
    elif role=='air_pressure' and u=='kpa':x*=10
    elif u=='kpa':x/=100
    elif u=='mpa':x*=10
    elif u=='psi':x*=0.0689476
    # Reject impossible measurements, rather than silently clipping.
    if role in ('flow','flow_counter','reference_flow','reference_flow_counter','frequency','wind','solar','pv','power','buh','other_heat','fan','eev','high_pressure','low_pressure','illuminance','wind_gust','rain_rate','air_pressure') and x<0:return None
    if role=='wind_direction' and not 0<=x<=360:return None
    if role=='wind_direction':x%=360
    if role=='humidity' and not 0<=x<=100:return None
    return x

def series_id(role,m):
    identity={k:m.get(k) for k in ('entity','attribute','unit','on_value','source','latitude','longitude')}
    return role+':'+hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:20]
def mapping(cfg):
    out={k:dict(v) for k,v in cfg['mapping'].items() if v.get('entity') and k in ROLES}
    r=cfg.get('regional',{})
    if r.get('enabled'):
        for k in REGIONAL:
            if k not in out:out[k]={'source':'regional','entity':REGIONAL[k],'attribute':'','unit':ROLES[k][1],'latitude':r['latitude'],'longitude':r['longitude']}
    return out

def add_series(s,rows,a,b):
    """Atomically store a successful source segment, including explicit unknowns."""
    if not rows or b<=a:return
    with db() as c:
        c.executemany('INSERT OR REPLACE INTO events VALUES(?,?,?)',[(s,float(t),v) for t,v in rows if a-0.01<=t<=b+0.01])
        # Coalesce overlapping coverage segments. Never bridge unobserved gaps.
        existing=c.execute('SELECT start,end FROM coverage WHERE series=? AND end>=? AND start<=?',(s,a-0.001,b+0.001)).fetchall()
        for r in existing:a=min(a,r['start']);b=max(b,r['end'])
        c.executemany('DELETE FROM coverage WHERE series=? AND start=? AND end=?',[(s,r['start'],r['end']) for r in existing])
        c.execute('INSERT OR REPLACE INTO coverage VALUES(?,?,?)',(s,a,b))
def series_end(s):
    with db() as c:r=c.execute('SELECT MAX(end) FROM coverage WHERE series=?',(s,)).fetchone();return r[0]
def load(s,a,b,counter=False):
    with db() as c:
        rows=c.execute('SELECT t,value FROM events WHERE series=? AND t>=? AND t<=? ORDER BY t',(s,a,b)).fetchall()
        pre=c.execute('SELECT t,value FROM events WHERE series=? AND t<? ORDER BY t DESC LIMIT 1',(s,a)).fetchone()
        post=c.execute('SELECT t,value FROM events WHERE series=? AND t>? ORDER BY t LIMIT 1',(s,b)).fetchone() if counter else None
        cov=c.execute('SELECT start,end FROM coverage WHERE series=? AND end>? AND start<? ORDER BY start',(s,a,b)).fetchall()
    rows=([pre] if pre else [])+list(rows)+([post] if post else [])
    return (np.array([r[0] for r in rows],dtype=float), np.array([r[1] if r[1] is not None else np.nan for r in rows],dtype=float),[(r[0],r[1]) for r in cov])
def interpolate_step(t,ts,vs,cov,counter=False,max_gap=300):
    out=np.full(t.shape,np.nan)
    if not len(ts):return out
    i=np.searchsorted(ts,t,side='right')-1
    if counter:
        ok=(i>=0)&(i+1<len(ts));j=i[ok];delta=vs[j+1]-vs[j];dur=ts[j+1]-ts[j]
        vals=np.divide(delta*3600,dur,out=np.full(delta.shape,np.nan),where=dur>0)
        vals[(delta<0)|(dur>max_gap)|(vals>100000)]=np.nan;out[ok]=vals
    else:
        ok=i>=0;out[ok]=vs[i[ok]]
    # use only intervals for which successful history retrieval is known
    valid=np.zeros(t.shape,dtype=bool)
    for x,y in cov: valid|=(t>=x)&(t<y)
    out[~valid]=np.nan
    return out

def aligned(cfg,a,b):
    if b<=a:raise ValueError('End must be after start.')
    if b-a>32*86400:raise ValueError('Maximum analysis window is 32 days; choose smaller blocks.')
    m=mapping(cfg); data={}; edges=[np.array([a,b])]
    for k,v in m.items():
        data[k]=load(series_id(k,v),a,b,k in COUNTER_ROLES);ts,vs,cov=data[k]
        edges.append(ts[(ts>a)&(ts<b)])
        for x,y in cov:edges.append(np.array([max(a,x),min(b,y)]))
    e=np.unique(np.concatenate(edges));t=e[:-1];duration=np.diff(e)
    vals={k:interpolate_step(t,*d,k in COUNTER_ROLES,cfg['counter_max_gap']) for k,d in data.items()}
    # derive dew point using Magnus approximation only for co-observed outdoor T/RH
    if 'dewpoint' not in vals and ('weather_temperature' in vals or 'outside' in vals) and 'humidity' in vals:
        temp=vals.get('weather_temperature',vals.get('outside'));rh=vals['humidity'];g=np.log(np.maximum(rh,0.0001)/100)+17.62*temp/(243.12+temp)
        vals['dewpoint']=243.12*g/(17.62-g);vals['dewpoint'][(rh<=0)|~np.isfinite(temp)]=np.nan
    if 'flow' not in vals and 'flow_counter' in vals:vals['flow']=vals['flow_counter']
    if 'reference_flow' not in vals and 'reference_flow_counter' in vals:vals['reference_flow']=vals['reference_flow_counter']
    return t,duration,vals

def r(v,d=3):return round(float(v),d) if np.isfinite(v) else None
def flow_comparison(t,d,x):
    if 'reference_flow' not in x:return None
    p=x.get('flow',np.full(t.shape,np.nan));q=x['reference_flow'];total=d.sum()
    both=np.isfinite(p)&np.isfinite(q);delta=q-p
    def stats(mask):
        seconds=d[mask].sum()
        if not seconds:return {'hours':0,'primary_lh':None,'reference_lh':None,'bias_lh':None,'mae_lh':None,'relative_bias_pct':None}
        def mean(y):return r(np.sum(y[mask]*d[mask])/seconds)
        positive=mask&(p>0)
        denominator=np.sum(p[positive]*d[positive])
        return {'hours':r(seconds/3600,4),'primary_lh':mean(p),'reference_lh':mean(q),'bias_lh':mean(delta),'mae_lh':mean(np.abs(delta)),'relative_bias_pct':r(100*np.sum(delta[positive]*d[positive])/denominator) if denominator>0 else None}
    df=x.get('defrost',np.full(t.shape,np.nan))
    return {**stats(both),'coverage_pct':r(100*d[both].sum()/total,2),'defrost':stats(both&(df==1)),'non_defrost':stats(both&(df==0)),'flow_bands':[{'min_lh':lo,'max_lh':hi,**stats(both&(p>=lo)&((p<hi) if hi is not None else True))} for lo,hi in [(0,500),(500,1000),(1000,1500),(1500,2000),(2000,None)]],'warning':'Reference minus primary; relative bias uses only positive primary flow and is volume-weighted. Recorder coverage does not prove MQTT measurement freshness. No calibration or automatic substitution.'}

def metrics(cfg,a,b):
    t,d,x=aligned(cfg,a,b);total=b-a; nan=np.full(t.shape,np.nan)
    def v(k):return x.get(k,nan)
    def valid(y):return np.isfinite(y)
    def cover(y):return r(d[valid(y)].sum()/total*100,2)
    def avg(y):
        ok=valid(y);return r(np.sum(y[ok]*d[ok])/np.sum(d[ok])) if ok.any() else None
    def energy(y):
        ok=valid(y);return r(np.sum(y[ok]*d[ok])/3.6e6,5) if ok.any() else None
    def hours(y):return r(d[y].sum()/3600,4)
    q=cfg['water_factor']*v('flow')*(v('supply')-v('return'))
    # q is signed heat transferred at the measurement boundary. Only space heating (or defrost).
    if not cfg['heat_only']:
        heating=v('heating');q=np.where((heating==1)|(v('defrost')==1),q,np.nan) if 'heating' in x else nan
    p=v('power');buh=v('buh');mode=cfg['buh_mode'];thermal_mode=cfg['buh_thermal']
    if not cfg['heat_only']:
        active=(v('heating')==1)|(v('defrost')==1)
        p=np.where(active,p,np.nan);buh=np.where(active,buh,np.nan)
    if mode=='separate':pel=p+buh
    elif mode in ('included','none'):pel=p
    else:pel=nan
    # If separately metered and outside the heat measurement boundary, resistive heat approximated at 1 W/W.
    if thermal_mode=='outside' and mode=='separate':q_system=q+buh
    elif thermal_mode=='inside' or mode=='none':q_system=q
    elif thermal_mode=='unknown' and mode=='separate':q_system=np.where(buh==0,q,np.nan)
    else:q_system=nan
    # COP only based on synchronized, mutually observed thermal and electrical samples.
    match=valid(q_system)&valid(pel)&(pel>=0)
    e_q=energy(np.where(match,q_system,np.nan));e_p=energy(np.where(match,pel,np.nan))
    hp_match=valid(q)&valid(p)&(p>=0)
    hp_e_q=energy(np.where(hp_match,q,np.nan));hp_e_p=energy(np.where(hp_match,p,np.nan))
    freq=v('frequency');de=v('defrost');known=valid(de);on=de==1
    starts=int(np.sum((de[1:]==1)&(de[:-1]==0))) if len(de)>1 else 0
    # Boundary and unknown-to-on episodes are left censored, not known starts.
    episodes=int(np.sum(on & np.r_[True,~on[:-1]])) if len(on) else 0
    cycles=[]
    if on.any():
        begins=np.where(on & np.r_[True,~on[:-1]])[0];ends=np.where(on & np.r_[~on[1:],True])[0]
        for i,j in zip(begins,ends):
            qseg=q[i:j+1];ds=d[i:j+1];ok=np.isfinite(qseg)
            neg=float(np.sum(np.minimum(qseg[ok],0)*ds[ok])/3.6e6) if ok.any() else None
            cycles.append({'start':local_iso(t[i]),'end':local_iso(t[j]+d[j]),'minutes':r(ds.sum()/60,2),'negative_heat_kwh':r(neg,4) if neg is not None else None,'thermal_coverage_pct':r(ds[ok].sum()/ds.sum()*100,2),'start_observed':bool(i>0 and de[i-1]==0),'end_observed':bool(j+1<len(de) and de[j+1]==0)})
    deficit=np.maximum(v('target')-v('inside'),0)
    summary={'start':local_iso(a),'end':local_iso(b),'hours':r(total/3600,3),'means':{k:avg(y) for k,y in x.items()},'coverage_pct':{k:cover(y) for k,y in x.items()},'net_thermal_kwh':energy(q),'positive_thermal_kwh':energy(np.maximum(q,0)),'negative_thermal_kwh':energy(np.minimum(q,0)),'net_thermal_kw':(r(avg(q)/1000) if avg(q) is not None else None),'thermal_coverage_pct':cover(q),'electrical_input_kwh':energy(p),'buh_kwh':energy(buh) if mode=='separate' else (0 if mode=='none' else None),'system_electrical_kwh':energy(pel),'system_thermal_kwh':energy(q_system),'system_cop':r(e_q/e_p) if e_q is not None and e_p and e_p>0 else None,'cop_coverage_pct':r(d[match].sum()/total*100,2),'boundary_cop':r(hp_e_q/hp_e_p) if hp_e_q is not None and hp_e_p and hp_e_p>0 else None,'boundary_cop_coverage_pct':r(d[hp_match].sum()/total*100,2),'defrost_starts':starts if known.any() else None,'defrost_episodes':episodes if known.any() else None,'defrost_minutes':r(d[on].sum()/60,2) if known.any() else None,'defrost_pct_observed':r(d[on].sum()/d[known].sum()*100,2) if known.any() else None,'defrost_negative_kwh':energy(np.where(on,np.minimum(q,0),np.nan)) if known.any() else None,'compressor_high_pct_observed':r(d[valid(freq)&(freq>=cfg['hz_threshold'])].sum()/d[valid(freq)].sum()*100,2) if valid(freq).any() else None,'compressor_high_hours':hours(valid(freq)&(freq>=cfg['hz_threshold'])) if valid(freq).any() else None,'comfort_deficit_degree_hours':r(np.nansum(deficit*d)/3600) if valid(deficit).any() else None,'comfort_coverage_pct':cover(deficit),'reported_thermal_kwh':energy(v('thermal')),'weather_sources':{k:('regional model (hourly)' if m.get('source')=='regional' else 'HA entity: '+m['entity']) for k,m in mapping(cfg).items() if k in REGIONAL or k in ('weather_temperature','illuminance','wind_direction','wind_gust','rain_rate','wet','air_pressure','pv')},'cycles':cycles,'warnings':[]}
    # Comfort metrics use only intervals where indoor temperature and target coexist.
    error=v('inside')-v('target');paired=valid(error);observed=d[paired].sum()
    excess=np.maximum(error,0)
    def comfort_pct(mask):return r(100*d[paired&mask].sum()/observed,2) if observed else None
    summary.update(comfort_observed_hours=r(observed/3600,4),
        comfort_mean_deficit_c=avg(deficit),
        comfort_max_deficit_c=r(np.max(deficit[paired])) if observed else None,
        comfort_excess_degree_hours=r(np.sum(excess[paired]*d[paired])/3600) if observed else None,
        comfort_mean_excess_c=avg(excess),
        comfort_within_band_pct=comfort_pct(np.abs(error)<=0.5),
        comfort_below_band_pct=comfort_pct(error < -0.5),
        comfort_above_band_pct=comfort_pct(error > 0.5),
        comfort_band_c=0.5,
        comfort_mean_inside_c=avg(np.where(paired,v('inside'),np.nan)),
        comfort_mean_target_c=avg(np.where(paired,v('target'),np.nan)))
    summary['flow_comparison']=flow_comparison(t,d,x)
    if 'wind_direction' in x:
        direction=v('wind_direction');ok=valid(direction)
        if ok.any():
            angle=np.deg2rad(direction[ok]);sx=np.sum(np.sin(angle)*d[ok]);cx=np.sum(np.cos(angle)*d[ok]);summary['means']['wind_direction']=r(np.rad2deg(np.arctan2(sx,cx))%360) if np.hypot(sx,cx)>1e-9*d[ok].sum() else None
    if 'dewpoint' in x and 'dewpoint' not in mapping(cfg):summary['weather_sources']['dewpoint']='derived from mapped weather-station T and RH (Magnus)' if 'weather_temperature' in x else 'derived from outdoor T and RH (Magnus)'
    if 'flow' not in mapping(cfg) and 'flow_counter' in mapping(cfg):summary['warnings'].append('Flow derived from successive cumulative readings; resets and long gaps excluded.')
    if cover(q)<95:summary['warnings'].append('Thermal coverage below 95%; energy is observed partial energy, not extrapolated.')
    if summary['cop_coverage_pct']<95:summary['warnings'].append('System COP coverage below 95% or system boundary not configured.')
    if mode=='unknown' or (thermal_mode=='unknown' and mode!='none' and not (mode=='separate' and np.all(~valid(q)|(valid(buh)&(buh==0))))):summary['warnings'].append('Confirm BUH metering and thermal boundary; system COP may be unavailable.')
    if not cfg['heat_only'] and 'heating' not in x:summary['warnings'].append('Confirm heating-only operation or map a space-heating status; complete space-heating metrics unavailable.')
    elif not cfg['heat_only']:summary['warnings'].append('Space-heating mode selected: energy and COP exclude intervals not marked as heating or defrost. Coverage is relative to the entire window.')
    if mode=='separate' and thermal_mode=='outside':summary['warnings'].append('BUH outside thermal measurement: assumed resistance heater 1 W heat/W input.')
    if summary['boundary_cop'] is not None:summary['warnings'].append('Boundary COP = water heat / mapped electrical input; not necessarily compressor-only or whole-system COP.')
    return summary

def hourly(cfg,a,b):
    if b-a>32*86400:raise ValueError('Maximum 32 days.')
    # UTC hours prevent DST ambiguity; explicit local offset is returned.
    edges=[a];n=(math.floor(a/3600)+1)*3600
    while n<b:edges.append(n);n+=3600
    edges.append(b)
    return [metrics(cfg,x,y) for x,y in zip(edges[:-1],edges[1:])]

def heat_loss(cfg,a,b):
    import regression
    """Exploratory steady-state model, not EN12831 design sizing."""
    # Bounded chunks keep the general dashboard limit unchanged.
    if not 0<b-a<=90*86400:raise ValueError('Heat loss model supports up to 90 days.')
    rows=[];start=a
    while start<b:
        end=min(b,(math.floor(start/3600)+24*28)*3600);rows.extend(hourly(cfg,start,end));start=end
    used=[];rejected={'partial_hour':0,'thermal_or_boundary_coverage':0,'temperature_coverage':0,'small_delta_t':0,'no_adjacent_hour':0,'indoor_temperature_change':0,'other_heat_coverage':0}
    for h in rows:
        m=h['means'];q=h['system_thermal_kwh'];n=h['hours']
        if not n or n<0.99:rejected['partial_hour']+=1;continue
        if q is None or h['thermal_coverage_pct']<95 or h['cop_coverage_pct']<95:rejected['thermal_or_boundary_coverage']+=1;continue
        if any(m.get(k) is None or h['coverage_pct'].get(k,0)<95 for k in ('inside','outside')):rejected['temperature_coverage']+=1;continue
        if m['inside']-m['outside']<5:rejected['small_delta_t']+=1;continue
        if 'other_heat' in mapping(cfg) and (m.get('other_heat') is None or h['coverage_pct'].get('other_heat',0)<95):rejected['other_heat_coverage']+=1;continue
        # Compare adjacent hourly inside means to screen thermal storage transients.
        used.append((h,m,q/n))
    filtered=[]
    if used:rejected['no_adjacent_hour']+=1
    for i in range(1,len(used)):
        h,m,q=used[i];prev,pm,_=used[i-1]
        if abs(parse_time(h['start'])-parse_time(prev['end']))>1:rejected['no_adjacent_hour']+=1;continue
        if abs(m['inside']-pm['inside'])>0.15:rejected['indoor_temperature_change']+=1;continue
        if m.get('other_heat') is not None:q+=m['other_heat']/1000
        filtered.append((m,q,h))
    diagnostics={'total_hour_bins':len(rows),'rejected':rejected,'minimum_hours':24,'minimum_delta_t_span_c':4,'start':local_iso(a),'end':local_iso(b),'analysis_hours':r((b-a)/3600,3)}
    if len(filtered)<24:return {**diagnostics,'status':'insufficient_data','hours':len(filtered),'minimum_hours':24,'warning':'Need at least 24 nearly steady, covered heating hours. Confirm BUH boundary and other heat sources.'}
    delta=np.array([m['inside']-m['outside'] for m,q,h in filtered]);y=np.array([q for m,q,h in filtered]);features=['delta_t'];columns=[delta]
    # include weather covariates only when every selected hour is observed; report their role, not causal claims.
    solar_proxy=next((k for k in ('solar','illuminance','pv') if all(m.get(k) is not None and h['coverage_pct'].get(k,0)>=95 for m,q,h in filtered) and np.std([m[k] for m,q,h in filtered])>1e-8),None)
    for k in ([solar_proxy] if solar_proxy else [])+['wind']:
        if all(m.get(k) is not None and h['coverage_pct'].get(k,0)>=95 for m,q,h in filtered):
            col=np.array([m[k] for m,q,h in filtered]);
            if np.std(col)>1e-8:columns.append(col);features.append(k)
    if np.ptp(delta)<4:return {**diagnostics,'status':'insufficient_temperature_range','hours':len(filtered),'delta_t_span_c':r(np.ptp(delta))}
    times=[parse_time(h['start']) for m,q,h in filtered]
    variants=[]
    subsets=[[0]]+[[0,i] for i in range(1,len(features))]+([list(range(len(features)))] if len(features)>2 else [])
    if 'wind' in features:
        wi=features.index('wind');features.append('delta_wind');columns.append(delta*columns[wi])
        subsets.append([0,wi,len(features)-1])
        if len(features)>3:subsets.append(list(range(len(features))))
    for subset in subsets:
        cols=[columns[i] for i in subset];names=[features[i] for i in subset]
        model=regression.fit(y,cols,names,times)
        if model:
            model.update(regression.diagnostics(y,cols,names,times,model))
            variants.append(model)
    if not variants:return {**diagnostics,'status':'unstable_model','hours':len(filtered),'warning':'Regression cannot identify a positive heat-loss slope.'}
    # Default to the strongest adjusted in-sample fit among positive slopes;
    # user may select another specification. Not a validated causal model.
    eligible=[m for m in variants if m['heat_loss_w_per_k']>0]
    best=max(eligible,key=lambda m:m['adjusted_r2'] if m['adjusted_r2'] is not None else -1e9) if eligible else variants[0]
    if best['heat_loss_w_per_k']<=0:return {**diagnostics,'status':'unstable_model','hours':len(filtered),'models':variants,'warning':'Regression cannot identify a positive heat-loss slope.'}
    # Preserve legacy top-level fields; all variants use identical eligible hours.
    points=[{'time':local_iso(t),'delta_t':r(dx),'observed_kw':r(q),'predicted_kw':p,'predictors':{k:r(v[i],6) for k,v in zip(features,columns)}} for i,(t,dx,q,p) in enumerate(zip(times,delta,y,best['predicted_kw']))]
    models=[{k:v for k,v in m.items() if k!='predicted_kw'} for m in variants]
    return {**diagnostics,'status':'exploratory','hours':len(filtered),'heat_loss_w_per_k':best['heat_loss_w_per_k'],'heat_loss_ci95_w_per_k':best['heat_loss_ci95_w_per_k'],'intercept_kw':best['coefficients']['intercept'],'features':best['features'],'coefficients':{k:v for k,v in best['coefficients'].items() if k!='intercept'},'rmse_kw':best['rmse_kw'],'r2':best['r2'],'delta_t_range_c':[r(delta.min()),r(delta.max())],'models':models,'points':points,'selected_model':next(m for m in models if m['features']==best['features']),'warning':'Exploratory observational regression; approximate HAC intervals do not account for model selection, thermal mass or unmeasured gains. Not certified design sizing.'}


def weather_defrost(cfg,a,b):
    """Observed exposure in outdoor-temperature bins, with measured RH and signed thermal losses."""
    t,d,x=aligned(cfg,a,b);nan=np.full(t.shape,np.nan);out=x.get('outside',nan);df=x.get('defrost',nan);rh=x.get('humidity',nan);dew=x.get('dewpoint',nan);evap=x.get('evaporator',nan)
    heat=cfg['water_factor']*x.get('flow',nan)*(x.get('supply',nan)-x.get('return',nan));rows=[]
    for lo,hi in [(-100,-7),(-7,-3.5),(-3.5,0),(0,3.5),(3.5,7),(7,100)]:
        ok=np.isfinite(out)&(out>=lo)&(out<hi);both=ok&np.isfinite(df)
        if not ok.any():continue
        def mean(y):
            v=ok&np.isfinite(y);return r(np.sum(y[v]*d[v])/d[v].sum(),2) if v.any() else None
        active=both&(df==1);negative=active&np.isfinite(heat)
        rows.append({'outside_range_c':[None if lo==-100 else lo,None if hi==100 else hi],'exposure_hours':r(d[ok].sum()/3600,3),'defrost_coverage_pct':r(d[both].sum()/d[ok].sum()*100,2),'defrost_pct_observed':r(d[active].sum()/d[both].sum()*100,2) if both.any() else None,'defrost_minutes':r(d[active].sum()/60,3) if both.any() else None,'defrost_thermal_coverage_pct':r(d[negative].sum()/d[active].sum()*100,2) if active.any() else None,'negative_heat_kwh':r(np.sum(np.minimum(heat[negative],0)*d[negative])/3.6e6,4) if negative.any() else (0 if both.any() and not active.any() else None),'rh_mean_pct':mean(rh),'wind_mean_ms':mean(x.get('wind',nan)),'solar_mean_wm2':mean(x.get('solar',nan)),'dewpoint_mean_c':mean(dew),'coil_minus_dewpoint_c':mean(evap-dew),'illuminance_mean_lx':mean(x.get('illuminance',nan)),'wind_gust_mean_ms':mean(x.get('wind_gust',nan)),'rain_rate_mean_mmh':mean(x.get('rain_rate',nan)),'wet_pct_observed':(r(100*mean(x.get('wet',nan)),2) if mean(x.get('wet',nan)) is not None else None),'weather_temperature_mean_c':mean(x.get('weather_temperature',nan)),'air_pressure_mean_hpa':mean(x.get('air_pressure',nan))})
    return {'start':local_iso(a),'end':local_iso(b),'bins':rows,'warning':'Descriptive association only, not evidence of causality. A coil sensor is a proxy for surface temperature; a negative coil–dew point margin indicates potential condensation, not measured icing. Regional model weather is not an on-site measurement.'}

def latest_measurements(cfg):
    output={}
    with db() as c:
        for k,v in mapping(cfg).items():
            row=c.execute('SELECT t,value FROM events WHERE series=? ORDER BY t DESC LIMIT 1',(series_id(k,v),)).fetchone()
            output[k]={'value':row['value'] if row else None,'timestamp':local_iso(row['t']) if row else None,'unit':v['unit'] if k in ('fan','eev') else ROLES[k][1],'source':v.get('source','HA')}
    return output

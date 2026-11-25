"""Standalone, ingress-only, on-demand research exporter. No uploads."""
import csv, io, json, os, re, tempfile, threading, zipfile, hashlib, time, secrets
from pathlib import Path
import numpy as np
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response
import core, collector, profiles, research_flow, virtual_flow, vfm_export

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
LOCK = threading.Lock()
PREVIEW = None
PREVIEW_TTL = 900
DATA = Path(os.getenv("DATA_DIR", "/data"))
BASE = ("frequency","outside","supply","return","power","heating","defrost")
REF = ("flow","flow_counter")
WEATHER = ("humidity","dewpoint","wind","wind_direction","wind_gust","solar","rain_rate","air_pressure","weather_temperature")
CIRCUIT = ("evaporator","condenser","discharge","suction","high_pressure","low_pressure","evap_sat","cond_sat","fan","eev")
PUMP = ("pump_pwm","flow","flow_counter")
CONTEXT = ("supply_target","thermal","buh","other_heat")
COMFORT = ("inside","target","zone_temperature","zone_humidity","co2_indoor")
PROFILES = {
    "vfm-reference": BASE + REF + ("pump_pwm","buh"),
    "defrost": BASE + REF + WEATHER + CIRCUIT + CONTEXT + ("pump_pwm",),
    "compressor": BASE + REF + WEATHER + CIRCUIT + CONTEXT + ("pump_pwm",),
    "pump-pwm": PUMP + BASE + CONTEXT,
    "heat-loss": ("inside","outside","heating","defrost","supply","return","power") + REF + WEATHER + CONTEXT,
    "intervention": BASE + REF + WEATHER + CONTEXT + ("pump_pwm","inside","target"),
    "comfort": COMFORT + ("outside","heating","supply","return","supply_target"),
}
ROLES = sorted(set().union(*map(set,PROFILES.values())))
REQUIRED = {
    "vfm-reference": BASE, "defrost": ("defrost","outside","frequency"),
    "compressor": ("frequency","power","supply","return","outside","heating","defrost"),
    "pump-pwm": ("pump_pwm",), "heat-loss": ("inside","outside","heating"),
    "intervention": ("outside","heating"), "comfort": ("inside","outside","target"),
}

@app.middleware("http")
async def ingress(request, call_next):
    if not request.client or request.client.host != "172.30.32.2":
        return Response("Ingress only", 403)
    if request.method == "POST" and request.headers.get("content-type","").split(";")[0] != "application/json":
        return Response("JSON required", 415)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

def detect_integrations(entities):
    # Match existing source-reviewed suffix sets, not arbitrary brand name guesses.
    result=[]
    for name,p in profiles.PROFILES.items():
        if name=="openquatt": continue
        groups={}
        for row in entities:
            eid=row["entity_id"].split(".",1)[-1]
            for role in ("supply","return","outside","frequency","defrost","pump_pwm"):
                suffix=p.get(role)
                if suffix and eid.endswith("_"+suffix):
                    prefix=eid[:-len(suffix)-1]
                    groups.setdefault(prefix,set()).add(role)
        for prefix,roles in groups.items():
            if {"supply","return","frequency"}<=roles:
                result.append({"profile":name,"prefix":prefix,"matches":sorted(roles)})
    return sorted(result,key=lambda r:(-len(r["matches"]),r["profile"],r["prefix"]))

def candidates(entities):
    result = {}
    for role in ROLES:
        units = core.ROLES[role][4]
        binary = units == ["on/off"]
        rows = []
        suffixes = {p[role] for name,p in profiles.PROFILES.items() if name != "openquatt" and role in p}
        for e in entities:
            eid = e["entity_id"]
            unit = "on/off" if binary and eid.startswith(("binary_sensor.","sensor.","input_boolean.","switch.")) else next((u for u in units if core.unit_norm(u)==core.unit_norm(e.get("unit"))),None)
            if not unit: continue
            match = any(eid.split(".",1)[1].endswith("_"+s) or eid.split(".",1)[1]==s for s in suffixes)
            rows.append({"entity":eid,"name":e["name"],"unit":unit,"state":e["state"],"suggested":match})
        result[role] = sorted(rows,key=lambda r:(not r["suggested"],r["entity"]))
    return result

def eligibility(mapping, model, buh_mode, intervention):
    keys = set(mapping)
    physical = bool(keys.intersection(REF))
    result = {}
    for name, req in REQUIRED.items():
        missing = sorted(set(req)-keys)
        if name in ("vfm-reference","pump-pwm") and not physical: missing.append("physical flow")
        if name=="vfm-reference" and model not in virtual_flow.MODELS: missing.append("Amber model")
        if name=="vfm-reference" and (buh_mode not in ("none","separate") or buh_mode=="separate" and "buh" not in keys): missing.append("BUH boundary")
        if name=="heat-loss" and not ("thermal" in keys or physical and {"supply","return"}<=keys): missing.append("measured heat or physical flow + temperatures")
        if name=="intervention" and not intervention: missing.append("intervention record")
        result[name]=missing
    return result

@app.get("/")
def index(request:Request):
    prefix=request.headers.get("x-ingress-path","")
    if not re.fullmatch(r"/api/hassio_ingress/[A-Za-z0-9_-]+/?",prefix): raise HTTPException(400,"Invalid ingress path")
    return HTMLResponse(Path("/app/exporter/index.html").read_text().replace("__BASE__",prefix.rstrip("/")+"/"))

@app.get("/api/setup")
def setup():
    try:
        entities=collector.entities()
        return {"integrations":detect_integrations(entities),"roles":{k:core.ROLES[k][0] for k in ROLES},"candidates":candidates(entities),"profiles":list(PROFILES),"models":sorted(virtual_flow.MODELS),"saved":load_setup(),"required":REQUIRED}
    except Exception: raise HTTPException(502,"Cannot read Home Assistant states")

def validate(payload, entities):
    if payload.get("confirmed") is not True: raise ValueError("Confirm physical meters and measurement boundaries")
    selected=payload.get("profiles",[])
    if not isinstance(selected,list) or not selected or any(k not in PROFILES for k in selected): raise ValueError("Select research profiles")
    model=payload.get("model")
    if model not in (*virtual_flow.MODELS,"generic"): raise ValueError("Invalid model")
    hours=payload.get("hours")
    if hours not in (24,72,168): raise ValueError("Invalid period")
    buh=payload.get("buh_mode","unknown")
    if buh not in ("unknown","none","separate"): raise ValueError("Invalid BUH mode")
    factor=float(payload.get("water_factor",1.163))
    if not 0.5<=factor<=1.5: raise ValueError("Invalid water factor")
    allowed=candidates(entities)
    mapping={}
    for role,m in payload.get("mapping",{}).items():
        if role not in allowed: raise ValueError("Unknown role")
        row=next((r for r in allowed[role] if r["entity"]==m.get("entity")),None)
        if not row: raise ValueError("Invalid sensor selection")
        on=str(m.get("on_value","on")).strip()
        if row["unit"]=="on/off" and not on: raise ValueError("Specify active state")
        mapping[role]={"entity":row["entity"],"unit":row["unit"],"attribute":"","on_value":on}
    if "flow" in mapping and "flow_counter" in mapping: raise ValueError("Select one physical flow source")
    intervention=payload.get("intervention")
    if intervention:
        if not isinstance(intervention,dict) or intervention.get("parameter") not in ("heating_curve","pump_pwm","defrost","frequency_limit","hysteresis","other"):
            raise ValueError("Invalid intervention parameter")
        for k in ("before","after","minute_index"):
            if type(intervention.get(k)) not in (int,float) or not np.isfinite(intervention[k]): raise ValueError("Intervention values must be numeric")
        if not 0<=intervention["minute_index"]<hours*60: raise ValueError("Intervention outside period")
        intervention={k:intervention[k] for k in ("parameter","before","after","minute_index")}
    missing=eligibility(mapping,model,buh,intervention)
    if any(missing[k] for k in selected): raise ValueError("Missing requirements: "+json.dumps({k:missing[k] for k in selected if missing[k]}))
    if ("comfort" in selected or any(k in mapping for k in ("inside","target","zone_temperature","zone_humidity","co2_indoor")) and any(k in selected for k in ("heat-loss","intervention"))) and payload.get("comfort_consent") is not True: raise ValueError("Separate comfort data consent required")
    use=set().union(*(PROFILES[k] for k in selected))
    if not payload.get("comfort_consent"): use-=set(COMFORT)
    cfg={**core.DEFAULT,"model":model,"buh_mode":buh,"water_factor":factor,"mapping":{k:v for k,v in mapping.items() if k in use},"installation":installation_metadata(payload.get("installation",{}))}
    return cfg,selected,hours,intervention

INSTALL_CHOICES={
    "integration":("openamber","bommer","leejow","other","unknown"),
    "flow_meter":("yf_b10","aquaro","ultrasonic","other","unknown"),
    "power_meter":("shelly","mid","other","unknown"),
    "emitters":("floor","radiators","mixed","fan_coils","other","unknown"),
    "hydraulics":("direct","series_buffer","parallel_buffer","other","unknown"),
    "ventilation":("natural","mechanical","heat_recovery","other","unknown"),
    "pump_control":("fixed","pwm","other","unknown"),
}
INSTALL_NUMBERS={"heated_area_m2":(1,2000),"heated_volume_m3":(1,10000),"glycol_pct":(0,60),"flow_accuracy_pct":(0,100)}

def installation_metadata(raw):
    if not isinstance(raw,dict): raise ValueError("Invalid installation metadata")
    result={}
    for k,choices in INSTALL_CHOICES.items():
        v=raw.get(k,"unknown")
        if v not in choices: raise ValueError("Invalid installation choice: "+k)
        result[k]=v
    for k,(lo,hi) in INSTALL_NUMBERS.items():
        v=raw.get(k)
        if v is None: continue
        if type(v) not in (int,float) or not np.isfinite(v) or not lo<=v<=hi: raise ValueError("Invalid installation number: "+k)
        result[k]=v
    return result

def build_package(cfg, selected, hours, intervention, installation_id, end):
    start=end-hours*3600
    old=core.DATA
    with tempfile.TemporaryDirectory(prefix="ohpa-export-") as tmp:
        core.DATA=Path(tmp)
        try:
            core.init()
            maps=list(core.mapping(cfg).items())
            for a in range(start-300,end,10800):
                for i in range(0,len(maps),8):
                    collector.fetch_history(maps[i:i+8],a,min(a+10800,end))
            t,d,x=core.aligned(cfg,start,end)
            quality={k:round(100*float(d[np.isfinite(v)].sum())/(end-start),2) for k,v in x.items()}
            output=io.BytesIO()
            counts={}
            with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as z:
                for name in selected:
                    if name=="vfm-reference":
                        rows=research_flow.observations(cfg,start,end,{"enabled":True,"confirmed":True,"installation_id":installation_id,"mapping_hash":research_flow.fingerprint(cfg)})
                        if len(rows)<30: raise ValueError("VFM requires at least 30 suitable minutes")
                        z.writestr("vfm-reference.csv",research_flow.export_csv(rows)); counts[name]=len(rows)
                        continue
                    keys=sorted(set(PROFILES[name])&set(x))
                    req=list(REQUIRED[name])
                    if name=="pump-pwm": req.append("flow")
                    if name=="heat-loss" and "thermal" not in keys: req.extend(("flow","supply","return"))
                    elif name=="heat-loss": req.append("thermal")
                    if not all(k in x for k in req): raise ValueError("Missing historical series for "+name)
                    paired=np.logical_and.reduce([np.isfinite(x[k]) for k in req])
                    quality[name+"_paired_pct"]=round(100*float(d[paired].sum())/(end-start),2)
                    if not paired.any(): raise ValueError("No jointly observed required measurements for "+name)
                    f=io.StringIO(); w=csv.writer(f); w.writerow(["relative_seconds","duration_seconds",*keys])
                    for i in range(len(t)):
                        if not any(np.isfinite(x[k][i]) for k in keys): continue
                        w.writerow([round(float(t[i]-start),3),round(float(d[i]),3),*[round(float(x[k][i]),6) if np.isfinite(x[k][i]) else "" for k in keys]])
                    counts[name]=sum(any(np.isfinite(x[k][i]) for k in keys) for i in range(len(t)))
                    if not counts[name]: raise ValueError("No usable history for "+name)
                    z.writestr(name+".csv",f.getvalue())
                z.writestr("manifest.json",json.dumps({"schema":"ohpa-research/1","installation_id":installation_id,"hours":hours,"profiles":selected,"rows":counts,"time_basis":"relative seconds; event-aligned step intervals; not measurement freshness"},indent=2))
                z.writestr("installation.json",json.dumps({"model":cfg["model"],"water_factor":cfg["water_factor"],"buh_mode":cfg["buh_mode"],**cfg.get("installation",{})}))
                z.writestr("measurement-setup.json",json.dumps({k:{"source_unit":v["unit"],"canonical_unit":core.ROLES[k][1]} for k,v in cfg["mapping"].items()}))
                z.writestr("data-quality.json",json.dumps({"observed_coverage_pct":quality,"warning":"Recorder coverage does not prove sensor freshness."}))
                if "intervention" in selected: z.writestr("interventions.json",json.dumps(intervention))
            return output.getvalue()
        finally: core.DATA=old


def load_setup():
    path=DATA/"exporter-setup.json"
    if path.is_symlink(): return {}
    try:
        result=json.loads(path.read_text())
        return result if isinstance(result,dict) else {}
    except (OSError,ValueError): return {}

def store_setup(payload):
    # Local configuration only; do not persist consent, intervention, or credentials.
    allowed=candidates(collector.entities())
    mapping={}
    for role,m in payload.get("mapping",{}).items():
        if role not in allowed or not isinstance(m,dict): raise ValueError("Invalid mapping")
        if not any(r["entity"]==m.get("entity") for r in allowed[role]): raise ValueError("Unknown entity")
        mapping[role]={"entity":m["entity"],"on_value":str(m.get("on_value","on"))[:100]}
    model=payload.get("model")
    if model not in (*virtual_flow.MODELS,"generic"): raise ValueError("Invalid model")
    buh=payload.get("buh_mode")
    if buh not in ("unknown","none","separate"): raise ValueError("Invalid BUH boundary")
    factor=float(payload.get("water_factor",1.163))
    if not 0.5<=factor<=1.5: raise ValueError("Invalid water factor")
    DATA.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",dir=DATA,delete=False) as f:
        json.dump({"mapping":mapping,"model":model,"buh_mode":buh,"water_factor":factor,"installation":installation_metadata(payload.get("installation",{}))},f)
        tmp=f.name
    os.replace(tmp,DATA/"exporter-setup.json")

@app.post("/api/save")
def save(payload:dict):
    try: store_setup(payload); return {"saved":True}
    except (ValueError,TypeError,KeyError): raise HTTPException(400,"Invalid setup")
    except Exception: raise HTTPException(502,"Could not save setup")

@app.post("/api/eligibility")
def check(payload:dict):
    return eligibility(payload.get("mapping",{}),payload.get("model"),payload.get("buh_mode"),payload.get("intervention"))

def summarize(content):
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        manifest=json.loads(z.read("manifest.json"))
        quality=json.loads(z.read("data-quality.json"))
        samples={}
        for name in manifest["profiles"]:
            with z.open(name+".csv") as f:
                reader=csv.reader(io.TextIOWrapper(f,encoding="utf-8"))
                samples[name]=[row for _,row in zip(range(4),reader)]
        return {"manifest":manifest,"quality":quality,"samples":samples,"bytes":len(content),"sha256":hashlib.sha256(content).hexdigest()}

def expire_preview(token):
    global PREVIEW
    with LOCK:
        if PREVIEW and PREVIEW[0]==token:
            PREVIEW=None

@app.post("/api/preview")
def preview(payload:dict):
    global PREVIEW
    if not LOCK.acquire(blocking=False): raise HTTPException(409,"Export already running")
    try:
        PREVIEW=None
        cfg,selected,hours,intervention=validate(payload,collector.entities())
        DATA.mkdir(parents=True,exist_ok=True)
        iid=vfm_export.read_installation_id(DATA)
        end=int((core.now()-15)//60)*60
        content=build_package(cfg,selected,hours,intervention,iid,end)
        if len(content)>25_000_000: raise ValueError("ZIP exceeds 25 MB; select fewer profiles or a shorter period")
        summary=summarize(content)
        token=secrets.token_urlsafe(24)
        PREVIEW=(token,time.monotonic()+PREVIEW_TTL,content)
        timer=threading.Timer(PREVIEW_TTL,expire_preview,args=(token,))
        timer.daemon=True
        timer.start()
        return {"token":token,**summary}
    except (ValueError,TypeError,KeyError) as e: raise HTTPException(400,str(e))
    except Exception: raise HTTPException(502,"Export failed; check Recorder history and retry")
    finally: LOCK.release()

@app.post("/api/download")
def download(payload:dict):
    global PREVIEW
    with LOCK:
        if not PREVIEW or time.monotonic()>PREVIEW[1]:
            PREVIEW=None
            raise HTTPException(410,"Preview expired; generate again")
        if not isinstance(payload.get("token"),str) or not secrets.compare_digest(payload["token"],PREVIEW[0]):
            raise HTTPException(404,"Preview not found")
        if payload.get("confirmed") is not True: raise HTTPException(400,"Confirm reviewed export")
        content=PREVIEW[2]
        PREVIEW=None
        return Response(content,media_type="application/zip",headers={"Content-Disposition":'attachment; filename="ohpa-research.zip"'})

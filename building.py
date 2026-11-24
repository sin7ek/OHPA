"""Optional local dwelling profile and explicitly partial envelope estimate."""
import math
KINDS=('wall','roof','floor','window','door','other')
BOUNDARIES=('outside','ground','unheated','adjacent','unknown')
SOURCES=('unknown','estimated','measured','documented')
def number(v,lo,hi):
    if v is None or v=='':return None
    if isinstance(v,bool):raise ValueError('Invalid number')
    v=float(v)
    if not math.isfinite(v) or not lo<=v<=hi:raise ValueError('Number outside permitted range')
    return v
def choice(v,options):
    if v in (None,''):return None
    if v not in options:raise ValueError('Invalid option')
    return v
def normalize(raw):
    if not isinstance(raw,dict):raise ValueError('Expected profile object')
    p={k:number(raw.get(k),lo,hi) for k,lo,hi in [('orientation',0,360),('year',1000,2100),('floor_area',0,100000),('volume',0,1000000),('ventilation_flow',0,100000),('wtr',0,100),('infiltration_flow',0,100000),('n50',0,100),('qv10',0,10000)]}
    if p['orientation']==360:p['orientation']=0
    for k,opts in [('type',('terraced','corner','semi','detached','apartment','other')),('ventilation',('natural','natural_local','mechanical','balanced','wtr','other')),('insulation',('unknown','low','medium','high')),('side',('left','right','both','none','unknown')),('source',SOURCES)]:
        p[k]=choice(raw.get(k),opts)
    air=raw.get('air_exchange') or {}
    p['air_exchange']={'mode':choice(air.get('mode'),('separate','total','ach','unknown')) or 'separate',
        'source':choice(air.get('source'),SOURCES),
        'ach':number(air.get('ach'),0,20),'ach_low':number(air.get('ach_low'),0,20),'ach_high':number(air.get('ach_high'),0,20),
        'fan_nominal_m3h':number(air.get('fan_nominal_m3h'),0,10000)}
    av=p['air_exchange']
    if av['ach_low'] is not None and av['ach_high'] is not None and av['ach_low']>av['ach_high']:raise ValueError('ACH lower bound exceeds upper bound')
    if av['ach'] is not None and ((av['ach_low'] is not None and av['ach']<av['ach_low']) or (av['ach_high'] is not None and av['ach']>av['ach_high'])):raise ValueError('ACH central estimate outside bounds')
    p['facades']={}
    for k in ('front','rear','left','right'):
        f=raw.get('facades',{}).get(k,{})
        p['facades'][k]={'orientation':number(f.get('orientation'),0,360),'boundary':choice(f.get('boundary'),BOUNDARIES),'shelter':choice(f.get('shelter'),('open','partial','strong','unknown'))}
    p['surfaces']=[];ids=set()
    if len(raw.get('surfaces',[]))>100:raise ValueError('Maximum 100 surfaces')
    for row in raw.get('surfaces',[]):
        sid=str(row.get('id',''))[:64]
        if not sid or sid in ids:raise ValueError('Duplicate or missing surface ID')
        ids.add(sid)
        item={'id':sid,'name':str(row.get('name',''))[:100],'kind':choice(row.get('kind'),KINDS),'boundary':choice(row.get('boundary'),BOUNDARIES),'source':choice(row.get('source'),SOURCES),'parent':str(row.get('parent') or '')[:64]}
        if not item['kind']:raise ValueError('Surface kind required')
        for k,lo,hi in [('area',0,100000),('u',0,20),('rc',0,50),('orientation',0,360),('pitch',0,90),('g',0,1),('factor',0,1)]:
            item[k]=number(row.get(k),lo,hi)
        item['shading']=choice(row.get('shading'),('none','internal','external','unknown'))
        p['surfaces'].append(item)
    by={s['id']:s for s in p['surfaces']}
    for s in p['surfaces']:
        if s['parent'] and (s['kind'] not in ('window','door') or s['parent'] not in by or by[s['parent']]['kind'] not in ('wall','roof')):raise ValueError('Opening must reference a wall or roof')
    for s in p['surfaces']:
        kids=[x for x in p['surfaces'] if x['parent']==s['id']]
        if s['area'] is not None and sum(x['area'] or 0 for x in kids)>s['area']+1e-8:raise ValueError('Openings exceed gross surface area')
    p['bridges']=[]
    if len(raw.get('bridges',[]))>100:raise ValueError('Maximum 100 thermal bridges')
    for b in raw.get('bridges',[]):
        p['bridges'].append({'name':str(b.get('name',''))[:100],'length':number(b.get('length'),0,10000),'psi':number(b.get('psi'),-2,10),'source':choice(b.get('source'),SOURCES)})
    geometry=raw.get('geometry') or {}
    p['geometry']={'storeys':number(geometry.get('storeys'),1,30),'extensions':number(geometry.get('extensions'),0,30),'roof_type':choice(geometry.get('roof_type'),('flat','pitched','mixed')),'roof_planes':number(geometry.get('roof_planes'),0,30),'roof_inside':choice(geometry.get('roof_inside'),('yes','no','unknown'))}
    for k in ('storeys','extensions','roof_planes'):
        v=p['geometry'][k]
        if v is not None and v!=int(v):raise ValueError('Geometry counts must be integers')
    if p['geometry']['roof_type']=='flat' and p['geometry']['roof_planes'] not in (None,0):raise ValueError('Flat roof has no sloping roof planes')
    p['roof_calculations']=[]
    if len(raw.get('roof_calculations',[]))>100:raise ValueError('Maximum 100 roof calculations')
    for item in raw.get('roof_calculations',[]):
        p['roof_calculations'].append({'name':str(item.get('name') or '')[:100],
            'width':number(item.get('width'),0.001,1000),
            'length':number(item.get('length'),0.001,1000),
            'pitch':number(item.get('pitch'),0,89.9),
            'surface_id':str(item.get('surface_id') or '')[:64],
            'source':choice(item.get('source'),SOURCES)})
    p['volume_parts']=[]
    if len(raw.get('volume_parts',[]))>100:raise ValueError('Maximum 100 volume parts')
    for part in raw.get('volume_parts',[]):
        p['volume_parts'].append({'name':str(part.get('name',''))[:100],
            'shape':choice(part.get('shape'),('rect','tri','custom')) or 'rect',
            'length':number(part.get('length'),0.001,1000),
            'width':number(part.get('width'),0.001,1000),
            'height':number(part.get('height'),0.001,1000),
            'custom_m3':number(part.get('custom_m3'),0.001,1000000),
            'source':choice(part.get('source'),SOURCES)})
    p['ui_level']=choice(raw.get('ui_level'),('basic','extended','expert')) or 'basic'
    p['notes']=str(raw.get('notes',''))[:2000]
    return p
def volume_calculation(parts):
    values=[p.get('custom_m3') if p['shape']=='custom' else round(p['length']*p['width']*p['height']*(.5 if p['shape']=='tri' else 1),6)
        if all(p.get(k) is not None for k in ('length','width','height')) else None for p in parts]
    return {'parts_m3':values,'known_subtotal_m3':round(sum(v for v in values if v is not None),3) if any(v is not None for v in values) else None,
        'complete':bool(values) and all(v is not None for v in values),
        'total_m3':round(sum(values),3) if values and all(v is not None for v in values) else None}
def roof_area(item):
    if any(item.get(k) is None for k in ('width','length','pitch')):return None
    return round(item['width']*item['length']/math.cos(math.radians(item['pitch'])),3)

def estimate(p):
    rows=[];missing=[];total=0.;known=0
    surfaces=p.get('surfaces',[]);by={s['id']:s for s in surfaces}
    for s in surfaces:
        parent=by.get(s['parent']);boundary=parent['boundary'] if parent else s['boundary'];factor=parent['factor'] if parent else s['factor']
        children=[x for x in surfaces if x['parent']==s['id']]
        area=s['area'];net=None if area is None or any(x['area'] is None for x in children) else area-sum(x['area'] for x in children)
        # Rc to approximate U only with explicit conventional surface resistances.
        u=s['u'];method='direct_u'
        if u is None and s['rc'] is not None and s['kind'] in ('wall','roof','floor','other') and boundary=='outside':
            u=1/(s['rc']+{'wall':.17,'roof':.14,'floor':.21,'other':.17}[s['kind']]);method='approx_rc'
        f=1 if boundary=='outside' else factor if boundary in ('ground','unheated','adjacent') else None
        value=net*u*f if net is not None and u is not None and f is not None else None
        reasons=[]
        if net is None:reasons.append('area')
        if u is None:reasons.append('u')
        if f is None:reasons.append('boundary_factor')
        if value is None:missing.append(s['id'])
        else:total+=value;known+=1
        rows.append({'id':s['id'],'name':s['name'],'net_area_m2':net,'u':u,'method':method if u is not None else None,'factor':f,'w_per_k':value,'missing':reasons})
    bridge_vals=[b['length']*b['psi'] for b in p.get('bridges',[]) if b['length'] is not None and b['psi'] is not None]
    flow=p.get('ventilation_flow');vent=p.get('ventilation');eff=p.get('wtr')
    ventilation=.34*flow*(1-eff/100 if vent=='wtr' else 1) if flow is not None and vent and (vent!='wtr' or eff is not None) else None
    infiltration=.34*p['infiltration_flow'] if p.get('infiltration_flow') is not None else None
    air=p['air_exchange'];mode=air['mode'];volume=p.get('volume')
    # Total exchange already includes infiltration. HRV cannot be applied uniformly
    # to total outdoor exchange because bypass/infiltration fractions are unknown.
    combined=None;bounds=None
    scenarios=[{'ach':ach,'flow_m3h':volume*ach,'w_per_k':.34*volume*ach} for ach in (.3,.5,.8)] if volume is not None and volume>0 else []
    if mode!='separate':
        ventilation=infiltration=None
        if vent and vent!='wtr':
            if mode=='total' and flow is not None:combined=.34*flow
            elif mode=='ach' and volume is not None and volume>0:
                if air['ach'] is not None:combined=.34*volume*air['ach']
                if air['ach_low'] is not None and air['ach_high'] is not None:bounds=[.34*volume*air[k] for k in ('ach_low','ach_high')]
    components=[total if known else None,sum(bridge_vals) if bridge_vals else None,ventilation,infiltration,combined]
    missing_components=[]
    if not surfaces:missing_components.append('surfaces')
    if mode=='separate':
        if ventilation is None:missing_components.append('ventilation')
        if infiltration is None:missing_components.append('infiltration')
    elif combined is None:missing_components.append('air_exchange')
    if not bridge_vals or len(bridge_vals)<len(p.get('bridges',[])):missing_components.append('bridges')
    return {'air_exchange_mode':mode,'combined_air_exchange_w_per_k':combined,'air_exchange_range_w_per_k':bounds,'air_exchange_scenarios':scenarios,'missing_components':missing_components,'roof_areas_m2':[roof_area(item) for item in p.get('roof_calculations',[])],'volume_calculation':volume_calculation(p.get('volume_parts',[])),'status':'partial_estimate','surfaces':rows,'unknown_surfaces':missing,'known_surfaces':known,'surface_count':len(surfaces),'transmission_w_per_k':components[0],'bridges_w_per_k':components[1],'ventilation_w_per_k':ventilation,'infiltration_w_per_k':infiltration,'known_subtotal_w_per_k':sum(x for x in components if x is not None) if any(x is not None for x in components) else None,'warning':'Partial envelope estimate only; completeness not verified. Ground and adjoining spaces require explicit effective temperature factors. No automatic infiltration from n50/qv10. No certified design load.'}

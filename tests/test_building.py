import pytest
import building
def test_openings_and_partial():
    p=building.normalize({'surfaces':[{'id':'w','kind':'wall','boundary':'outside','area':40,'u':.3},{'id':'g','kind':'window','parent':'w','area':10,'u':1.2},{'id':'r','kind':'roof','area':50}]})
    e=building.estimate(p)
    assert e['transmission_w_per_k']==pytest.approx(21)
    assert e['unknown_surfaces']==['r']
    assert e['known_subtotal_w_per_k']==pytest.approx(21)
def test_ground_unknown_and_ventilation():
    p=building.normalize({'ventilation':'wtr','ventilation_flow':100,'wtr':80,'surfaces':[{'id':'f','kind':'floor','boundary':'ground','area':50,'u':.2}]})
    e=building.estimate(p)
    assert e['transmission_w_per_k'] is None
    assert e['ventilation_w_per_k']==pytest.approx(6.8)
def test_invalid_opening():
    with pytest.raises(ValueError):building.normalize({'surfaces':[{'id':'w','kind':'wall','area':3},{'id':'g','kind':'window','area':4,'parent':'w'}]})
def test_empty():
    assert building.estimate(building.normalize({}))['known_subtotal_w_per_k'] is None

def test_volume_parts_flat_and_pitched():
    p=building.normalize({'volume':200,'volume_parts':[{'name':'ground','length':10,'width':6,'height':2.5},{'name':'extension','length':3,'width':6,'height':2.5},{'shape':'tri','length':10,'width':6,'height':2}]})
    result=building.volume_calculation(p['volume_parts'])
    assert result['total_m3']==255
    assert p['volume']==200  # explicit adoption, no silent overwrite
    assert building.estimate(p)['volume_calculation']['complete']
def test_volume_incomplete():
    p=building.normalize({'volume_parts':[{'length':10,'width':6,'height':2.5},{'length':3}]})
    result=building.volume_calculation(p['volume_parts'])
    assert result['known_subtotal_m3']==150
    assert result['total_m3'] is None
    assert not result['complete']

def test_scalable_geometry_and_custom_roof():
    p=building.normalize({'geometry':{'storeys':3,'extensions':1,'roof_type':'flat','roof_planes':0},'volume_parts':[{'shape':'custom','custom_m3':42}]})
    assert p['geometry']['storeys']==3
    assert building.volume_calculation(p['volume_parts'])['total_m3']==42
    with pytest.raises(ValueError):building.normalize({'geometry':{'storeys':2.5}})
    with pytest.raises(ValueError):building.normalize({'geometry':{'roof_type':'flat','roof_planes':2}})

def test_roof_calculations_persist_and_compute():
    p=building.normalize({'roof_calculations':[{'name':'main roof','width':6,'length':10,'pitch':0},{'name':'extension','width':3,'length':6,'pitch':0},{'width':3,'length':10,'pitch':60},{'width':3}]})
    assert building.estimate(p)['roof_areas_m2']==[60,18,60,None]
    assert building.normalize(p)['roof_calculations']==p['roof_calculations']
    assert not p['surfaces']  # calculations do not automatically create envelope surfaces

def test_estimate_missing_reasons_and_flat_drainage():
    p=building.normalize({'ui_level':'expert','roof_calculations':[{'width':6,'length':10,'pitch':2}], 'surfaces':[{'id':'roof','kind':'roof','area':60,'boundary':'outside'}]})
    e=building.estimate(p)
    assert p['ui_level']=='expert'
    assert e['roof_areas_m2'][0]>60
    assert e['surfaces'][0]['missing']==['u']
    assert e['known_subtotal_w_per_k'] is None
    assert 'ventilation' in e['missing_components']

def test_ach_no_double_count():
    p=building.normalize({'volume':400,'ventilation':'natural_local','ventilation_flow':100,'infiltration_flow':50,'air_exchange':{'mode':'ach','ach':.5,'ach_low':.3,'ach_high':.8}})
    e=building.estimate(p)
    assert e['combined_air_exchange_w_per_k']==pytest.approx(68)
    assert e['known_subtotal_w_per_k']==pytest.approx(68)
    assert e['ventilation_w_per_k'] is None and e['infiltration_w_per_k'] is None
    assert e['air_exchange_range_w_per_k']==pytest.approx([40.8,108.8])
def test_total_wtr_not_assumed():
    p=building.normalize({'volume':400,'ventilation':'wtr','air_exchange':{'mode':'ach','ach':.5}})
    assert building.estimate(p)['combined_air_exchange_w_per_k'] is None

def test_simple_scenario_and_exact_override():
    p=building.normalize({'floor_area':150,'simple_estimate':'medium','surfaces':[{'id':'r','kind':'roof','boundary':'outside','area':60},{'id':'w','kind':'wall','boundary':'outside','area':20,'u':.2},{'id':'f','kind':'floor','boundary':'ground','area':50}]})
    e=building.estimate(p)
    assert e['whole_dwelling_scenario_w_per_k']==[150,270,450]
    assert e['transmission_w_per_k']==pytest.approx(31)
    assert e['estimated_surface_count']==1
    assert e['surfaces'][0]['method']=='scenario_u'
    assert e['surfaces'][1]['method']=='direct_u'
    assert e['surfaces'][2]['w_per_k'] is None
    assert e['known_subtotal_w_per_k']==pytest.approx(31)
def test_scenario_off_and_unknown():
    p=building.normalize({'simple_estimate':'medium','surfaces':[{'id':'r','kind':'roof','boundary':'outside','area':60,'insulation':'unknown'}]})
    assert building.estimate(p)['transmission_w_per_k'] is None
    p['simple_estimate']='off'
    assert building.estimate(p,'expert')['whole_dwelling_scenario_w_per_k'] is None

def test_levels_auto_scenario_and_expert_exact():
    p=building.normalize({'floor_area':150,'volume':449.65,'ventilation':'natural_local','air_exchange':{'mode':'ach','ach':.5},'surfaces':[{'id':'r','kind':'roof','boundary':'outside','area':60.23},{'id':'e','kind':'roof','boundary':'outside','area':24}]})
    basic=building.estimate(p,'basic')
    assert basic['whole_dwelling_scenario_w_per_k']==[150,270,450]
    assert basic['missing_components']==[]
    extended=building.estimate(p,'extended')
    assert extended['transmission_w_per_k']==pytest.approx(84.23*.45)
    assert extended['known_surfaces']==2
    assert 'bridges' not in extended['missing_components']
    expert=building.estimate(p,'expert')
    assert expert['transmission_w_per_k'] is None
    assert expert['whole_dwelling_scenario_w_per_k'] is None
    assert 'bridges' in expert['missing_components']

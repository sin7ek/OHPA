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

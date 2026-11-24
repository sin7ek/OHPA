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

import profiles,core
def test_profile_preserves_mapping_and_units():
    e=[{'entity_id':'sensor.my_amber_cv_aanvoertemperatuur_tuo','unit':'°C','state':'30'},{'entity_id':'sensor.my_amber_cv_retourtemperatuur_tui','unit':'W','state':'25'}]
    r=profiles.proposals('openamber','my_amber',e,{'supply':{}},'amber95')
    rows={x['role']:x for x in r['rows']}
    assert rows['supply']['status']=='existing'
    assert rows['return']['status']=='unit_check'
    assert rows['evap_sat']['disabled_default']
    assert r['boundary_hint']
def test_exact_prefix_and_text_state():
    e=[{'entity_id':'sensor.amber_defrost_status','unit':'','state':'OFF'},{'entity_id':'sensor.other_water_outlet_temperature_tuo','unit':'°C','state':'30'}]
    rows={x['role']:x for x in profiles.proposals('remmob','amber',e,{})['rows']}
    assert rows['defrost']['candidates'][0]['on_value']=='ON'
    assert rows['supply']['status']=='missing'
def test_duo_rejected():
    import pytest
    with pytest.raises(ValueError):profiles.proposals('openquatt','openquatt',[],{},'quatt_duo')

import exporter_app as e
from fastapi.testclient import TestClient

def test_direct_access_denied():
    assert TestClient(e.app).get('/').status_code==403

def test_eligibility_and_privacy():
    result=e.eligibility({'defrost':{},'outside':{},'frequency':{}},'amber95','none',None)
    assert result['defrost']==[]
    assert 'physical flow' in result['vfm-reference']
    assert 'zone_presence' not in e.ROLES

def test_unique_suffix_candidates():
    rows=e.candidates([{'entity_id':'sensor.openamber_cv_aanvoertemperatuur_tuo','name':'Supply','state':'32','unit':'°C'}])
    assert rows['supply'][0]['suggested']
    assert not rows['power']

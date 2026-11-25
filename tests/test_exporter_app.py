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

def test_summary_is_actual_zip():
    import io, zipfile, json, hashlib
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('manifest.json',json.dumps({'profiles':['defrost']}))
        z.writestr('data-quality.json',json.dumps({'observed_coverage_pct':{'defrost':95}}))
        z.writestr('defrost.csv','relative_seconds,defrost\n0,1\n')
    result=e.summarize(b.getvalue())
    assert result['samples']['defrost'][1]==['0','1']
    assert result['sha256']==hashlib.sha256(b.getvalue()).hexdigest()

def test_download_requires_review(monkeypatch):
    import time
    from fastapi import HTTPException
    import pytest
    monkeypatch.setattr(e,'PREVIEW',('secret',time.monotonic()+30,b'zip'))
    with pytest.raises(HTTPException): e.download({'token':'secret'})
    with pytest.raises(HTTPException): e.download({'token':'wrong','confirmed':True})
    assert e.download({'token':'secret','confirmed':True}).body==b'zip'
    assert e.PREVIEW is None

def test_expired_preview(monkeypatch):
    import time, pytest
    from fastapi import HTTPException
    monkeypatch.setattr(e,'PREVIEW',('secret',time.monotonic()-1,b'zip'))
    with pytest.raises(HTTPException) as ex: e.download({'token':'secret','confirmed':True})
    assert ex.value.status_code==410

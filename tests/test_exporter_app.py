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

def test_detection_groups_prefixes():
    rows=[{"entity_id":"sensor."+prefix+"_"+suffix} for prefix in ("one","two") for suffix in ("cv_aanvoertemperatuur_tuo","cv_retourtemperatuur_tui","compressor_frequentie")]
    found=e.detect_integrations(rows)
    assert {x["prefix"] for x in found if x["profile"]=="openamber"}=={"one","two"}

def test_metadata_allowlist():
    import pytest
    out=e.installation_metadata({"flow_meter":"aquaro","heated_area_m2":80,"address":"private"})
    assert out["flow_meter"]=="aquaro" and out["heated_area_m2"]==80 and "address" not in out
    with pytest.raises(ValueError): e.installation_metadata({"glycol_pct":100})

def test_synthetic_package_privacy(monkeypatch):
    import io,zipfile,json
    import numpy as np
    from pathlib import Path
    previous=e.core.DATA
    monkeypatch.setattr(e.collector,"fetch_history",lambda *args:1)
    monkeypatch.setattr(e.core,"aligned",lambda cfg,a,b:(np.array([a],dtype=float),np.array([b-a],dtype=float),{"defrost":np.array([1.]),"frequency":np.array([40.]),"outside":np.array([2.])}))
    mapping={k:{"entity":"sensor.private_"+k,"unit":e.core.ROLES[k][1]} for k in ("defrost","frequency","outside")}
    cfg={**e.core.DEFAULT,"mapping":mapping,"model":"amber95","installation":e.installation_metadata({"flow_meter":"aquaro"})}
    blob=e.build_package(cfg,["defrost"],24,None,"a"*32,1800000000)
    assert e.core.DATA==previous
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert set(z.namelist())=={"manifest.json","installation.json","measurement-setup.json","data-quality.json","defrost.csv"}
        for name in z.namelist():
            assert b"sensor.private" not in z.read(name)
            assert b"1800000000" not in z.read(name)
        assert json.loads(z.read("data-quality.json"))["observed_coverage_pct"]["defrost_paired_pct"]==100
        assert json.loads(z.read("installation.json"))["flow_meter"]=="aquaro"

def test_local_overlap(monkeypatch,tmp_path):
    monkeypatch.setattr(e,"DATA",tmp_path)
    e.record_download({"start":0,"end":100,"profiles":["defrost"],"sha256":"x"})
    assert len(e.overlapping(99,200,["defrost"]))==1
    assert not e.overlapping(100,200,["defrost"])
    assert not e.overlapping(0,100,["comfort"])

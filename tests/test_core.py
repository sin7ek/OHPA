import os, sys, tempfile, pathlib, copy
import pytest
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import core

@pytest.fixture
def cfg(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DATA',tmp_path);core.init()
    c=copy.deepcopy(core.DEFAULT);c.update(heat_only=True,buh_mode='separate',buh_thermal='inside')
    return c

def add(cfg,role,rows,a=0,b=3600,unit=None):
    m={'entity':'sensor.'+role,'attribute':'','unit':unit or core.ROLES[role][1],'on_value':'on'}
    cfg['mapping'][role]=m;core.add_series(core.series_id(role,m),rows,a,b)

def baseline(c):
    for k,v in {'flow':1200,'supply':35,'return':30,'power':1600,'buh':400,'inside':20,'target':21.5,'outside':0,'frequency':90,'defrost':0}.items():add(c,k,[(0,v)])

def test_steady_energy_and_buh(cfg):
    baseline(cfg);s=core.metrics(cfg,0,3600)
    assert s['net_thermal_kwh']==pytest.approx(6.978)
    assert s['system_electrical_kwh']==pytest.approx(2)
    assert s['system_cop']==pytest.approx(3.489)
    assert s['comfort_deficit_degree_hours']==1.5
    assert s['compressor_high_pct_observed']==100
    assert s['thermal_coverage_pct']==100

def test_signed_defrost_and_alignment(cfg):
    baseline(cfg);add(cfg,'supply',[(0,35),(1800,27),(2400,35)]);add(cfg,'defrost',[(0,0),(1800,1),(2400,0)])
    s=core.metrics(cfg,0,3600)
    assert s['defrost_starts']==1 and s['defrost_minutes']==10
    assert s['negative_thermal_kwh']==pytest.approx(-0.6978)
    assert s['net_thermal_kwh']==pytest.approx(5.1172)
    assert s['cycles'][0]['start_observed'] and s['cycles'][0]['end_observed']

def test_coverage_and_unknown_not_zero(cfg):
    baseline(cfg);add(cfg,'power',[(0,1600),(1800,None),(2700,1600)])
    s=core.metrics(cfg,0,3600)
    assert s['cop_coverage_pct']==75
    assert s['system_electrical_kwh']==pytest.approx(1.5)
    assert s['system_cop']==pytest.approx(3.489)
    assert s['thermal_coverage_pct']==100

def test_no_mapped_sensors(cfg):
    s=core.metrics(cfg,0,3600);assert s['net_thermal_kwh'] is None and s['system_cop'] is None and s['defrost_starts'] is None

def test_buh_outside_boundary(cfg):
    baseline(cfg);cfg['buh_thermal']='outside';s=core.metrics(cfg,0,3600)
    assert s['system_thermal_kwh']==pytest.approx(7.378) and s['system_cop']==pytest.approx(3.689)

def test_unconfirmed_buh(cfg):
    baseline(cfg);cfg['buh_mode']='unknown';assert core.metrics(cfg,0,3600)['system_cop'] is None

def test_counter_reset_and_gap(cfg):
    add(cfg,'flow_counter',[(0,100),(60,120),(120,5),(180,25),(600,165)],0,660)
    _,d,x=core.aligned(cfg,0,660);assert np.isfinite(x['flow']).sum()==2
    assert list(x['flow'][np.isfinite(x['flow'])])==[1200,1200]

def test_nonoverlapping_coverage(cfg):
    add(cfg,'outside',[(0,1)],0,600);add(cfg,'outside',[(1200,3)],1200,1800)
    s=core.metrics(cfg,0,1800);assert s['coverage_pct']['outside']==pytest.approx(66.67);assert s['means']['outside']==2

def test_defrost_boundary_censor(cfg):
    add(cfg,'defrost',[(0,1),(600,0),(1200,None),(1800,1),(2400,0)],0,3600)
    s=core.metrics(cfg,0,3600);assert s['defrost_starts']==0 and s['defrost_episodes']==2
    assert s['defrost_minutes']==20 and s['coverage_pct']['defrost']==pytest.approx(83.33)

def test_units():
    assert core.convert('20','L/min','flow')==1200
    assert core.convert('1.2','m³/h','flow')==1200
    assert core.convert('32','°F','outside')==0
    assert core.convert('1.5','kW','power')==1500
    assert core.convert('36','km/h','wind')==10
    assert core.convert('unavailable','W','power') is None
    assert core.convert('unknown','on/off','defrost') is None

def test_mode_gate(cfg):
    baseline(cfg);cfg['heat_only']=False;s=core.metrics(cfg,0,3600);assert s['net_thermal_kwh'] is None
    add(cfg,'heating',[(0,1),(1800,0)]);s=core.metrics(cfg,0,3600)
    assert s['net_thermal_kwh']==pytest.approx(3.489) and s['system_electrical_kwh']==1

def test_model_rejects_insufficient_data(cfg):
    baseline(cfg);assert core.heat_loss(cfg,0,3600)['status']=='insufficient_data'

import copy
import numpy as np
import core

def test_flow_units():
    for val,unit,want in [(1,'l/hr',1),(2,'L/s',7200),(0.001,'m³/s',3600),(1,'L/min',60)]:
        assert core.convert(val,unit,'reference_flow')==want
    assert core.convert(-1,'L/h','reference_flow') is None

def test_reference_flow_comparison_and_primary_preserved(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DATA',tmp_path);core.init()
    cfg=copy.deepcopy(core.DEFAULT);cfg.update(heat_only=True,buh_mode='none',buh_thermal='none')
    for k,value in [('flow',1200),('reference_flow',1140),('supply',35),('return',30),('power',1500),('defrost',0)]:
        m={'entity':'sensor.'+k,'attribute':'','unit':core.ROLES[k][1],'on_value':'on'}
        cfg['mapping'][k]=m
        core.add_series(core.series_id(k,m),[(0,value)],0,3600 if k!='reference_flow' else 1800)
    s=core.metrics(cfg,0,3600);f=s['flow_comparison']
    assert f['coverage_pct']==50 and f['bias_lh']==-60 and f['mae_lh']==60
    assert f['relative_bias_pct']==-5 and f['non_defrost']['hours']==0.5
    assert s['net_thermal_kw']==6.978
    assert f['flow_bands'][2]['bias_lh']==-60
    del cfg['mapping']['reference_flow']
    assert core.metrics(cfg,0,3600)['net_thermal_kw']==s['net_thermal_kw']

def test_zero_and_missing_flow():
    t=np.array([0.,10.,20.]);d=np.array([10.,10.,10.])
    f=core.flow_comparison(t,d,{'flow':np.array([0.,100.,np.nan]),'reference_flow':np.array([10.,90.,50.])})
    assert f['coverage_pct']==66.67 and f['relative_bias_pct']==-10 and f['bias_lh']==0
    assert core.flow_comparison(t,d,{'flow':np.zeros(3)}) is None

def test_old_config_defaults(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DATA',tmp_path);core.init()
    cfg=copy.deepcopy(core.DEFAULT);del cfg['flow_profile'];del cfg['reference_flow_profile']
    core.save_config(cfg)
    assert core.config()['flow_profile']=='manual'

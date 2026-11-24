import sys,pathlib,copy
import pytest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import core,collector

def test_ha_climate_attribute_and_empty_history(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DATA',tmp_path);core.init()
    m={'entity':'climate.test','attribute':'current_temperature','unit':'°C','on_value':'on'}
    missing={'entity':'sensor.missing','attribute':'','unit':'°C','on_value':'on'}
    payload=[[{'entity_id':'climate.test','state':'heat','last_updated':core.iso(0),'attributes':{'current_temperature':20}}, {'entity_id':'climate.test','state':'heat','last_updated':core.iso(600),'attributes':{'current_temperature':21}}]]
    monkeypatch.setattr(collector,'ha_get',lambda path,params:payload)
    assert collector.fetch_history([('inside',m),('outside',missing)],0,1200)==1
    c=copy.deepcopy(core.DEFAULT);c['mapping']={'inside':m,'outside':missing}
    s=core.metrics(c,0,1200)
    assert s['means']['inside']==20.5 and s['coverage_pct']['outside']==0
    assert core.series_end(core.series_id('outside',missing)) is None

def test_weather_defrost_temperature_bins(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DATA',tmp_path);core.init();c=copy.deepcopy(core.DEFAULT)
    for k,rows in [('outside',[(0,-2),(1800,2)]),('defrost',[(0,0),(900,1),(2700,0)]),('humidity',[(0,90)])]:
        m={'entity':'sensor.'+k,'unit':core.ROLES[k][1],'attribute':'','on_value':'on'};c['mapping'][k]=m;core.add_series(core.series_id(k,m),rows,0,3600)
    r=core.weather_defrost(c,0,3600)
    assert [b['defrost_pct_observed'] for b in r['bins']]==[50,50]
    assert r['bins'][0]['rh_mean_pct']==90

def test_recent_first_and_backfill_cursors(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DATA',tmp_path);core.init()
    m={'entity':'sensor.test','attribute':'','unit':'°C','on_value':'on'}
    cfg=copy.deepcopy(core.DEFAULT);cfg['mapping']={'outside':m};cfg['backfill_days']=2
    monkeypatch.setattr(collector,'config',lambda:cfg)
    monkeypatch.setattr(collector,'mapping',lambda c:c['mapping'])
    monkeypatch.setattr(collector,'now',lambda:200000)
    monkeypatch.setattr(collector,'weather',lambda *args:None)
    calls=[]
    def empty(maps,a,b):
        calls.append((a,b))
        return 0
    monkeypatch.setattr(collector,'fetch_history',empty)
    sid=core.series_id('outside',m)
    assert collector.collect_once()==1
    assert len(calls)==2
    assert calls[0][1]==199985
    assert calls[1][1]==calls[0][0]
    assert core.getmeta('live_v2:'+sid)==calls[0][1]
    assert core.getmeta('back_v2:'+sid)==calls[1][0]
    assert core.series_end(sid) is None
    status=core.getmeta('collector',{})
    assert not status['errors'] and status['missing_history']
    old=core.getmeta('back_v2:'+sid)
    calls.clear()
    collector.collect_once()
    assert calls[0][1]==199985 and calls[1][1]==old
    assert core.getmeta('back_v2:'+sid)<old

def test_failed_live_query_does_not_advance_cursor(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DATA',tmp_path);core.init()
    m={'entity':'sensor.test','attribute':'','unit':'°C','on_value':'on'}
    cfg=copy.deepcopy(core.DEFAULT);cfg['mapping']={'outside':m};cfg['backfill_days']=2
    monkeypatch.setattr(collector,'config',lambda:cfg)
    monkeypatch.setattr(collector,'mapping',lambda c:c['mapping'])
    monkeypatch.setattr(collector,'now',lambda:200000)
    monkeypatch.setattr(collector,'weather',lambda *args:None)
    calls=[]
    def fail(maps,a,b):
        calls.append((a,b))
        raise RuntimeError('test API error')
    monkeypatch.setattr(collector,'fetch_history',fail)
    sid=core.series_id('outside',m)
    collector.collect_once()
    assert len(calls)==1
    assert core.getmeta('live_v2:'+sid) is None
    assert core.getmeta('back_v2:'+sid) is None
    assert core.getmeta('collector',{})['errors']

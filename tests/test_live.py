import live,core,copy
import pytest
def setup():
    cfg=copy.deepcopy(core.DEFAULT);cfg.update(buh_mode='separate',buh_thermal='inside')
    states=[]
    for k,val in [('supply',35),('return',30),('flow',1200),('power',1500),('buh',0)]:
        eid='sensor.'+k;cfg['mapping'][k]={'entity':eid,'unit':core.ROLES[k][1],'attribute':''}
        states.append({'entity_id':eid,'state':str(val),'last_updated':core.iso(990)})
    return cfg,states
def test_live_snapshot():
    cfg,states=setup();s=live.snapshot(cfg,states,1000)
    assert s['thermal_w']==pytest.approx(6978) and s['system_power_w']==1500
    assert s['system_cop']==pytest.approx(6978/1500)
def test_stale_missing_and_signed_heat():
    cfg,states=setup();states[0]['last_updated']=core.iso(700)
    assert live.snapshot(cfg,states,1000)['thermal_w'] is None
    states[0]['last_updated']=core.iso(990);states[0]['state']='25'
    assert live.snapshot(cfg,states,1000)['thermal_w']<0
    states[-1]['state']='unavailable'
    assert live.snapshot(cfg,states,1000)['system_cop'] is None
def test_unknown_boundary_zero_buh():
    cfg,states=setup();cfg['buh_thermal']='unknown'
    assert live.snapshot(cfg,states,1000)['system_cop'] is not None
    states[-1]['state']='100'
    assert live.snapshot(cfg,states,1000)['system_cop'] is None

def test_contextual_thermostat_attributes_remain_available(cfg=None):
    cfg,states=setup()
    cfg['mapping']['inside']={'entity':'climate.room','attribute':'current_temperature','unit':'°C'}
    cfg['mapping']['target']={'entity':'climate.room','attribute':'temperature','unit':'°C'}
    thermostat={'entity_id':'climate.room','state':'heat','attributes':{'current_temperature':20.9,'temperature':21.5},'last_updated':core.iso(100)}
    states.append(thermostat)
    s=live.snapshot(cfg,states,1000)
    assert s['measurements']['inside']['value']==20.9
    assert s['measurements']['target']['value']==21.5
    assert s['measurements']['target']['status']=='state_available'
    assert s['measurements']['inside']['age_seconds']==900
    thermostat['state']='unavailable'
    s=live.snapshot(cfg,states,1000)
    assert s['measurements']['inside']['value'] is None
    assert s['measurements']['target']['status']=='missing'

def test_older_fast_measurement_still_blocks_derived_heat():
    cfg,states=setup()
    states[0]['last_updated']=core.iso(100)
    s=live.snapshot(cfg,states,1000)
    assert s['measurements']['supply']['status']=='older_state'
    assert s['thermal_w'] is None

def test_old_zero_buh_snapshot_estimate_only():
    cfg,states=setup();states[-1]['last_updated']=core.iso(100)
    s=live.snapshot(cfg,states,1000)
    assert s['system_power_w'] is None and s['system_cop'] is None
    assert s['estimated_system_power_w']==1500
    assert s['estimated_system_cop']==pytest.approx(6978/1500)
    states[-1]['state']='unavailable'
    assert live.snapshot(cfg,states,1000)['estimated_system_cop'] is None
    states[-1]['state']='100'
    assert live.snapshot(cfg,states,1000)['estimated_system_power_w'] is None

def test_unchanged_compressor_and_defrost():
    cfg,states=setup()
    for role,value in [('frequency','55'),('defrost','off')]:
        cfg['mapping'][role]={'entity':'sensor.'+role,'unit':core.ROLES[role][1]}
        states.append({'entity_id':'sensor.'+role,'state':value,'last_updated':core.iso(100)})
    s=live.snapshot(cfg,states,1000)
    assert s['measurements']['frequency']['value']==55
    assert s['measurements']['defrost']['value']==0
    assert s['measurements']['defrost']['status']=='state_available'

import live,core,copy
def setup():
    cfg=copy.deepcopy(core.DEFAULT);cfg.update(buh_mode='separate',buh_thermal='inside')
    states=[]
    for k,val in [('supply',35),('return',30),('flow',1200),('power',1500),('buh',0)]:
        eid='sensor.'+k;cfg['mapping'][k]={'entity':eid,'unit':core.ROLES[k][1],'attribute':''}
        states.append({'entity_id':eid,'state':str(val),'last_updated':core.iso(990)})
    return cfg,states
def test_live_snapshot():
    cfg,states=setup();s=live.snapshot(cfg,states,1000)
    assert s['thermal_w']==6978 and s['system_power_w']==1500
    assert s['system_cop']==6978/1500
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

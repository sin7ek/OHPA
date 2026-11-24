import copy
import tempfile
import unittest
from pathlib import Path

import core
import research_flow as rf
import virtual_flow as vf


class ResearchFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.old = core.DATA
        core.DATA = Path(self.tmp.name); core.init()

    def tearDown(self):
        core.DATA = self.old; self.tmp.cleanup()

    def test_export_and_guard(self):
        cfg = copy.deepcopy(core.DEFAULT); cfg.update(model='amber95',buh_mode='none')
        for role,value in dict(frequency=45,outside=5,supply=35,**{'return':32},power=1100,defrost=0,heating=1,flow=1200,pump_pwm=70).items():
            m={'entity':'sensor.'+role,'attribute':'','unit':core.ROLES[role][1],'on_value':'on'}
            cfg['mapping'][role]=m; core.add_series(core.series_id(role,m),[(0,value)],0,3600)
        core.save_config(cfg); setup=rf.configure(True,True)
        rows=rf.observations(cfg,300,3600,setup)
        self.assertEqual(len(rows),55); self.assertEqual(rows[0]['measured_flow_lh'],1200)
        self.assertNotIn('sensor.',rf.export_csv(rows))
        for method in ('thermal','hydraulic','hybrid'):
            artifact=rf.train_csv(rf.export_csv(rows),'amber95',method)
            self.assertEqual(artifact['installation_count'],1)
            result=rf.report(cfg,300,3600,setup,method)
            self.assertEqual(result['predicted_minutes'],55)
            self.assertAlmostEqual(result['mean_flow_lh'],1200)
        cfg['water_factor']=1.2
        with self.assertRaises(ValueError):rf.observations(cfg,300,3600,setup)

    def test_defrost_and_missing_coverage(self):
        cfg=copy.deepcopy(core.DEFAULT); cfg.update(model='amber95',buh_mode='none')
        for role,value in dict(frequency=45,outside=5,supply=35,**{'return':32},power=1100,defrost=0,heating=1,flow=1200).items():
            m={'entity':'sensor.'+role,'attribute':'','unit':core.ROLES[role][1],'on_value':'on'};cfg['mapping'][role]=m
            events=[(0,value),(600,1),(660,0)] if role=='defrost' else [(0,value)]
            core.add_series(core.series_id(role,m),events,0,1200)
        core.save_config(cfg); setup=rf.configure(True,True)
        rows=rf.observations(cfg,300,1200,setup)
        self.assertEqual([r['minute_index'] for r in rows],[0,1,2,3,4,11,12,13,14])

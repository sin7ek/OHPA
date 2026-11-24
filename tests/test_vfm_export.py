import csv
import io
from unittest.mock import patch

import collector
import core
import research_flow
import vfm_export
import virtual_flow


def test_export_uses_shared_schema_and_trains():
    values = {
        'frequency': 43, 'outside': 4, 'supply': 33, 'return': 30,
        'power': 0.855, 'heating': 'on', 'defrost': 'off', 'flow': 20.7,
        'pump_pwm': 70,
    }
    cfg = {**core.DEFAULT, 'model': 'amber95', 'buh_mode': 'none', 'mapping': {}}
    for role in values:
        unit = {'power': 'kW', 'flow': 'L/min'}.get(role, core.ROLES[role][1])
        cfg['mapping'][role] = {'entity': 'sensor.private_' + role, 'unit': unit, 'on_value': 'on'}
    cfg['mapping']['heating']['entity'] = 'binary_sensor.private_heating'
    cfg['mapping']['defrost']['entity'] = 'binary_sensor.private_defrost'

    def history(path, params):
        assert path.startswith('/api/history/period/')
        assert set(params['filter_entity_id'].split(',')) == {m['entity'] for m in cfg['mapping'].values()}
        return [[{'entity_id': cfg['mapping'][role]['entity'], 'state': state,
                  'last_updated': path.removeprefix('/api/history/period/')}]
                for role, state in values.items()]

    data_path = core.DATA
    with patch.object(collector, 'ha_get', side_effect=history):
        rows = vfm_export.export_history(cfg, 300, 3900, 'test-installation')
    assert core.DATA == data_path
    assert len(rows) == 60
    exported = research_flow.export_csv(rows)
    assert 'private_' not in exported
    reader = csv.DictReader(io.StringIO(exported))
    assert reader.fieldnames == list(research_flow.FIELDS)
    data = list(reader)
    assert float(data[0]['measured_flow_lh']) == 1242
    assert float(data[0]['power_w']) == 855
    for method in ('thermal', 'hydraulic', 'hybrid'):
        assert virtual_flow.fit(data, 'amber95', method)['installation_count'] == 1


def test_reuses_installation_id(tmp_path):
    assert vfm_export.read_installation_id(tmp_path) == vfm_export.read_installation_id(tmp_path)


def test_suggests_openamber_sensor_but_requires_confirmation():
    entities = [{'entity_id': 'sensor.openamber_compressor_frequentie', 'unit': 'Hz',
                 'name': 'Compressor frequentie'}]
    with patch('builtins.input', return_value=''):
        chosen = vfm_export.pick_entity('frequency', entities)
    assert chosen['entity'] == entities[0]['entity_id']

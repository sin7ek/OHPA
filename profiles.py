"""Source-reviewed, conservative HA entity proposals; no writes to HA."""
from core import ROLES, unit_norm
import re
PROFILES={
  "openamber": {
    "supply": "cv_aanvoertemperatuur_tuo",
    "return": "cv_retourtemperatuur_tui",
    "outside": "buitentemperatuur_ta",
    "frequency": "compressor_frequentie",
    "defrost": "defrost",
    "supply_target": "huidig_setpoint",
    "thermal": "thermisch_vermogen",
    "evaporator": "verdampingstemperatuur_tp",
    "condenser": "condensatietemperatuur_tup",
    "discharge": "persgastemperatuur_td",
    "suction": "zuigastemperatuur_ts",
    "high_pressure": "persgasdruk_pd",
    "low_pressure": "zuiggasdruk_ps",
    "evap_sat": "evaporating_temperature",
    "cond_sat": "condensing_temperature",
    "fan": "fan_rpm",
    "eev": "expansieklep"
  },
  "remmob": {
    "supply": "water_outlet_temperature_tuo",
    "return": "water_inlet_temperature_tui",
    "outside": "ambient_temperature_ta",
    "inside": "room_temperature_tr",
    "frequency": "compressor_speed",
    "defrost": "defrost_status",
    "supply_target": "actual_setpoint_heating_zone_1",
    "evaporator": "coil_temperature_tp",
    "condenser": "condenser_temperature_tup",
    "discharge": "compressor_discharge_temperature_td",
    "suction": "compressor_suction_temperature_ts",
    "high_pressure": "compressor_high_pressure",
    "low_pressure": "compressor_low_pressure",
    "fan": "fan_speed",
    "eev": "eev_opening"
  },
  "electropaultje": {
    "supply": "heat_exchanger_water_outlet_temperature",
    "return": "heat_exchanger_water_inlet_temperature",
    "outside": "ambient_temperature",
    "inside": "inside_temperature",
    "frequency": "compressor_working_speed",
    "defrost": "defrost",
    "heating": "heating_in_progress",
    "supply_target": "actual_setpoint_heating_zone_1",
    "flow": "pulse_meter",
    "flow_counter": "total_pulses",
    "evaporator": "outdoor_coil_temperature",
    "condenser": "indoor_coil_temperature",
    "discharge": "discharge_temperature",
    "suction": "suction_temperature",
    "high_pressure": "high_pressure",
    "low_pressure": "low_pressure",
    "fan": "fan_speed",
    "eev": "expansion_valve_setting"
  },
  "openquatt": {
    "supply": "hp1_water_out_temperature",
    "return": "hp1_water_in_temperature",
    "outside": "outside_temperature_selected",
    "inside": "room_temperature_selected",
    "target": "room_setpoint_selected",
    "flow": "flow_average_selected",
    "frequency": "hp1_compressor_frequency",
    "defrost": "hp1_defrost",
    "heating": "hp1_working_mode_label",
    "supply_target": "heating_supply_target_selected",
    "thermal": "hp1_heat_power",
    "cop": "hp1_cop",
    "evaporator": "hp1_evaporator_coil_temperature",
    "condenser": "hp1_inner_coil_temperature",
    "evap_sat": "hp1_evaporating_temperature",
    "cond_sat": "hp1_condensing_temperature",
    "discharge": "hp1_gas_discharge_temperature",
    "suction": "hp1_gas_return_temperature",
    "high_pressure": "hp1_condenser_pressure",
    "low_pressure": "hp1_evaporator_pressure",
    "fan": "hp1_fan_speed",
    "eev": "hp1_eev_steps"
  }
}
DISABLED={'openamber':['evaporator','condenser','discharge','suction','high_pressure','low_pressure','evap_sat','cond_sat'],'openquatt':['cond_sat']}
MODELS=('generic','amber65','amber95','amber120','quatt_single','quatt_duo')
SOURCES={'openamber':'https://github.com/Jordi1990/openamber','remmob':'https://github.com/remmob/itho_amber','electropaultje':'https://github.com/electropaultje/itho-daalderop-amber-firmware','openquatt':'https://github.com/OpenQuatt/OpenQuatt'}
def proposals(profile,prefix,entities,existing,model='generic'):
    if profile not in PROFILES:raise ValueError('Unknown integration profile')
    if model=='quatt_duo' and profile=='openquatt':raise ValueError('Duo requires per-unit support; use manual mapping.')
    prefix=prefix.strip().lower().rstrip('_')
    if not prefix or not re.fullmatch(r'[a-z0-9_]+',prefix):raise ValueError('Enter the HA device entity prefix.')
    if profile=='openquatt' and any(e['entity_id'].split('.',1)[-1].startswith(prefix+'_hp2_') for e in entities):raise ValueError('HP2 detected; Single profile cannot be applied to Duo.')
    result=[]
    for role,suffix in PROFILES[profile].items():
        binary=ROLES[role][1]=='on/off'
        domains=('sensor',) if (profile=='remmob' or role=='heating' and profile=='openquatt') else ('binary_sensor',) if binary else ('sensor',)
        matches=[]
        for e in entities:
            if e['entity_id'] not in [f'{domain}.{prefix}_{suffix}' for domain in domains]:continue
            units=ROLES[role][4];raw=e.get('unit','')
            unit='on/off' if binary else next((u for u in units if unit_norm(u)==unit_norm(raw)),None)
            if role=='cop' and not raw:unit='ratio'
            if role=='eev' and raw=='p' and profile=='openquatt':unit='steps'
            matches.append({'entity':e['entity_id'],'attribute':'','unit':unit,'on_value':'Heating' if role=='heating' and profile=='openquatt' else 'ON' if profile=='remmob' and role=='defrost' else 'on','state':e.get('state',''),'source_unit':raw})
        status='existing' if role in existing else 'missing' if not matches else 'ambiguous' if len(matches)>1 else 'unit_check' if not matches[0]['unit'] else 'unavailable' if str(matches[0]['state']).lower() in ('unknown','unavailable','none','') else 'ready'
        result.append({'role':role,'suffix':suffix,'status':status,'disabled_default':role in DISABLED.get(profile,[]),'candidates':matches})
    return {'rows':result,'source':SOURCES[profile],'boundary_hint':model.startswith('amber') and profile in ('openamber','remmob','electropaultje'),'power_note':'External active power preferred; integration estimates are not independently metered.'}

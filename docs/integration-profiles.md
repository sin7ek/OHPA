# Home Assistant integration profiles / Integratieprofielen

Research-based mapping proposal, 2026-11-24. These are source-inspected candidates, not a claim of tested compatibility. Actual entity IDs depend on device names, integration prefixes, firmware and user renames. OHPA reads Home Assistant only; do not enable write/control entities for analytics.

## Common prerequisites / Algemene voorwaarden

Enable supply and return at the same hydraulic boundary, calibrated volumetric flow (or cumulative volume), instantaneous electrical active power, outdoor temperature and indoor temperature. Indoor target, compressor frequency and actual defrost status are strongly recommended. Confirm actual operating mode when DHW/cooling is possible. Check Recorder includes every mapped entity and that history exists. A flow switch, pump PWM, voltage times current, requested compressor frequency, or daily kWh is not a substitute for the corresponding measured quantity. Confirm BUH electrical and thermal boundaries separately. Use external power meters preferentially. A BUH status alone is not power. Never infer zero from unavailable data.

HA: Settings > Devices & services > Entities > filter by device and disabled status > enable the relevant measurement entities. Newly enabled entities have no retrospective history. / Instellingen > Apparaten en diensten > Entiteiten > filter op apparaat en uitgeschakelde status > schakel de relevante meetentiteiten in. Controleer Recorder en werkelijke eenheden.

## OpenAmber (Amber 65/95/120)

Sources: [Modbus sensors](https://github.com/Jordi1990/openamber/blob/main/src/openamber/modbus/sensors.yaml), [binary sensors](https://github.com/Jordi1990/openamber/blob/main/src/openamber/modbus/binary_sensors.yaml), [core sensors](https://github.com/Jordi1990/openamber/blob/main/src/openamber/core/sensors.yaml).

| OHPA role | Firmware display name | Unit | Enable manually by default? |
|---|---|---|---|
| outside | Buitentemperatuur (Ta) | °C | No |
| supply | CV-aanvoertemperatuur (Tuo) | °C | No |
| return | CV-retourtemperatuur (Tui) | °C | No |
| frequency | Compressor frequentie | Hz | No |
| defrost | Defrost | on/off | No |
| supply_target | Huidig setpoint | °C | No |
| thermal (cross-check) | Thermisch vermogen | W | No |
| power (estimated fallback only) | Stroomverbruik | W | No |
| evaporator | Verdampingstemperatuur (Tp) | °C | Yes |
| condenser | Condensatietemperatuur (Tup) | °C | Yes |
| discharge | Persgastemperatuur (Td) | °C | Yes |
| suction | Zuigastemperatuur (Ts) | °C | Yes |
| high_pressure | Persgasdruk (Pd) | bar | Yes |
| low_pressure | Zuiggasdruk (Ps) | bar | Yes |
| evap_sat | Evaporating Temperature | °C | Yes |
| cond_sat | Condensing Temperature | °C | Yes |
| fan | Fan RPM | rpm | No |
| eev | Expansieklep | verify steps | No |

External calibrated flow and true active power meter(s), and HA thermostat current_temperature/temperature attributes as appropriate. Verify any available pulse meter's calibration and unit. Verwarmingselement is BUH status only. Do not map Tc instead of Tuo, or hourly/daily COP as instantaneous COP. Tr is internal in inspected firmware. Verify actual heating mode rather than demand. Tp/Tup are coil/pipe temperature proxies, not saturation values. Confirm model/installation-specific BUH position using manufacturer schematic; do not automatically set electrical metering mode.

## remmob/itho_amber (Modbus TCP integration)

Sources: [sensor definitions](https://github.com/remmob/itho_amber/blob/main/custom_components/itho_amber/const.py), [entity naming](https://github.com/remmob/itho_amber/blob/main/custom_components/itho_amber/sensor.py), [decoding](https://github.com/remmob/itho_amber/blob/main/custom_components/itho_amber/hub.py).

Default prefix amber, configurable. Display names below are appended to the configured hub name. Relevant measurement descriptors explicitly enabled by default unless noted.

| OHPA role | Display name | Register/key | Unit |
|---|---|---|---|
| supply | water outlet temperature (TUO) | 505 | °C |
| return | water inlet temperature (TUI) | 506 | °C |
| condenser | Condenser temperature (TUP) | 507 | °C |
| frequency | Compressor speed | 515 | Hz |
| eev | EEV opening | 516 | confirm steps |
| outside | Ambient temperature (TA) | 517 | °C |
| high_pressure | Compressor high pressure | 521 | bar |
| low_pressure | Compressor low pressure | 522 | bar |
| discharge | Compressor discharge temperature (Td) | 523 | °C |
| suction | Compressor suction temperature (Ts) | 524 | °C |
| evaporator | Coil temperature (TP) | 525 | °C |
| fan | Fan speed | 526 | RPM |
| defrost | Defrost status | 530 | text ON/OFF |
| inside | Room temperature (TR) | 531 | °C |
| supply_target | Actual setpoint heating zone 1 | 703 | °C |

EEV descriptor has no explicit enabled flag or unit; check locally. Current operating mode (514) decodes Heating/Cooling/Standby/test; Current working mode (499) is separately decoded status. Verify DHW discrimination before using 514 alone for space heating. Defrost active value ON. Flow switch (532) is not a flowmeter. Running Current (528) and Supply Voltage (529) are not true electrical power. The integration's delta-T is absolute, unsuitable for signed defrost heat. External flow, active power and room target required where appropriate. No separate saturation-temperature mapping established.

## Electropaultje Amber Control Module

Sources: [firmware Modbus package](https://github.com/electropaultje/itho-daalderop-amber-firmware/blob/HEAD/yaml/packages/amber.yaml), [pulse meter configuration](https://github.com/electropaultje/itho-daalderop-amber-firmware/blob/HEAD/yaml/ithodaalderop-amber.yaml), [product information](https://electropaultje.nl/itho-daalderop-amber-control-module/).

| OHPA role | Firmware display name | Unit |
|---|---|---|
| supply | Heat exchanger water outlet temperature | °C |
| return | Heat exchanger water inlet temperature | °C |
| outside | Ambient temperature | °C |
| inside | Inside temperature | °C |
| frequency | Compressor working speed | Hz |
| defrost | Defrost | on/off |
| heating | Heating in progress | on/off |
| supply_target | Actual setpoint heating zone 1 | °C |
| flow | Pulse meter | l/hr |
| flow_counter | Total pulses | l |
| condenser | Indoor coil temperature | °C |
| evaporator | Outdoor coil temperature | °C |
| discharge | Discharge temperature | °C |
| suction | Suction temperature | °C |
| high_pressure | High pressure | bar |
| low_pressure | Low pressure | bar |
| fan | Fan speed | rpm |
| eev | Expansion valve setting | verify steps |

Inspected relevant firmware entries do not declare disabled_by_default. Pulse meter requires attached calibrated hardware; Total pulses is published in liters, verify scaling. External active power meter needed. OHPA needs l/hr alias support for this profile (manual L/h selection is possible after checking units). Separate DHW/cooling flags available; verify heating flag covers only space heating. No independent saturation readings established.

## OpenQuatt Single

Sources: [firmware heat pump IO](https://github.com/OpenQuatt/OpenQuatt/blob/HEAD/openquatt/oq_HP_io.yaml), [official companion dashboard](https://github.com/OpenQuatt/home-assistant-openquatt/blob/main/dashboards/single-en.yaml).

Example suffixes below omit sensor.openquatt_ unless binary_sensor is specified. Use actual IDs and same device.

| OHPA role | Entity suffix | Unit |
|---|---|---|
| inside | room_temperature_selected | °C |
| target | room_setpoint_selected | °C |
| outside | outside_temperature_selected | °C |
| supply | hp1_water_out_temperature | °C |
| return | hp1_water_in_temperature | °C |
| flow | flow_average_selected (verify same circuit as HP1) | L/h |
| power | hp1_power_input or total_power_input (confirm boundary) | W |
| thermal (cross-check) | hp1_heat_power | W |
| cop (cross-check) | hp1_cop | ratio |
| frequency | hp1_compressor_frequency | Hz |
| defrost | binary_sensor.openquatt_hp1_defrost | on/off |
| heating | hp1_working_mode_label | Heating |
| supply_target | heating_supply_target_selected | °C |
| evaporator | hp1_evaporator_coil_temperature | °C |
| condenser | hp1_inner_coil_temperature | °C |
| evap_sat | hp1_evaporating_temperature | °C |
| cond_sat | hp1_condensing_temperature (enable manually) | °C |
| discharge | hp1_gas_discharge_temperature | °C |
| suction | hp1_gas_return_temperature | °C |
| high_pressure | hp1_condenser_pressure | bar in heating |
| low_pressure | hp1_evaporator_pressure | bar in heating |
| fan | hp1_fan_speed | RPM |
| eev | hp1_eev_steps | p (steps) |
| other_heat | boiler_heat_power (only if valid thermal estimate) | W |

Firmware power input uses a generation-dependent estimator; don't label it independently metered. Prefer an external meter. Heat Power is mode-dependent calculated output, not independent signed defrost heat. Use water inlet/outlet and matching flow for signed heat. Don't use selected system supply with an individual HP return. Working Mode Label supports Heating, Cooling, Defrost, Standby; verify exact current strings. Heating enable is permission, not actual heating. Gas boiler is not BUH; don't count boiler thermal output in electric HP COP. Confirm no electric auxiliary heater before setting BUH none. Optional advanced Condensing temperature is disabled by default. No need to enable voltage/current solely for OHPA; firmware can use internal data.

## OpenQuatt Duo — future support

Do not silently apply the Single profile. Two compressors, defrost flags and hydraulic boundaries require per-unit analysis and topology-aware aggregation. Shared series flow must not be summed twice; parallel circuits need individual measured flows or a confirmed combined measurement boundary. Aggregate synchronized signed thermal energy and electrical energy before dividing; never average two COPs. Preserve per-unit defrost and modulation. Verify firmware generation-dependent max frequency instead of assuming Amber's 90 Hz.

## Proposed wizard implementation (not yet implemented)

- Select manufacturer/model and integration separately; keep generic/manual mode.
- Profile catalog with source links, version, role aliases, domains, expected units, default enabled state, confidence, power provenance and warnings. Match normalized suffix/name within selected device/prefix; no fuzzy auto-save, no hardcoded private entities. Show alternatives and missing/ambiguous candidates.
- HA REST /api/states returns loaded entities, not complete disabled registry. For missing candidates show enabling instructions, not an assertion that they are disabled. Optional read-only registry discovery only with supported authorized API; never enable automatically.
- Normalize l/hr to L/h and p to steps when explicitly documented; test aliases. Handle unitless EEV only after user confirms. Case-insensitive active state; distinguish unknown mode from off. Verify physical boundaries and sources; never assume power is measured.
- Preview proposed mapping with actual ID, state, unit and provenance. Preserve existing mappings unless user explicitly replaces them. Save only after confirmation. Show required/optional/externally measured roles; report recorder availability separately. No hardware settings changed.
- Regression tests for renamed prefixes, ambiguity, missing entities, disabled sensors, unit mismatch, textual statuses, estimated power, existing mapping preservation, Single/Duo rejection, BUH boundary.
- Translate UI and documentation NL/EN; persistent language preference. Profiles remain versioned and independently testable.

Compatibility status: source review only for external integrations; real installation validation needed. No affiliation with manufacturers or integration authors.

# User guide / Gebruikershandleiding

## Getting started
Open Sensors & setup (Sensoren & setup), fetch entities, select a profile or map manually, review actual entity IDs, attributes, units and physical boundaries, then save and fetch history. Profiles propose only; no HA settings are changed. Confirm heating mode, backup heater and flow meter boundaries. See [integration profiles](integration-profiles.md).

### Minimum useful measurement set
| Measurement | Purpose |
|---|---|
| Supply + return at same boundary | Signed temperature difference |
| Calibrated flow L/h or volume counter L | Water-side heat |
| Instantaneous active electrical power W/kW | Electrical energy and COP |
| Indoor/outdoor temperature | Comfort / heat loss |
| Target, heating mode, defrost, compressor frequency | Context and diagnostics |
| Separate BUH power when applicable | System boundary |
| Optional wind, humidity, solar, reference flow | Diagnostic comparisons |

Do not use daily kWh as power, PWM as flow, or an unverified thermal estimate as independent measured heat. Local weather sensors take precedence by role; regional Open-Meteo is optional, modeled weather, and sends configured coordinates to the provider.

## Tabs
- **Live:** current HA states, ages, instantaneous derived values only when coherent; a clearly labeled last-known zero-BUH estimate may be shown separately.
- **History:** choose period, inspect actual interval and valid coverage, energy, COP, defrost, comfort, hourly CSV, weather and exploratory heat-loss diagnostics. Compare periods with similar conditions; log interventions. Manual capacity curves are session-only and require matched conditions.
- **Sensors & setup:** map roles, independent reference flow, model/integration and options. Existing values must be reviewed before replacing.
- **Building profile:** optional; basic whole-dwelling scenario, extended geometry/surface scenarios, expert explicit U/Rc and other parameters. Enter dimensions, heated volume, orientation, boundary and shelter, ventilation. Roof calculations and volume subtotals require explicit adoption. Save to recalculate. Missing surfaces mean partial totals, not a complete certified estimate.
- **Rooms:** optional; add manually or import HA areas/floors, use unique area suggestions or device selection, verify sensors and save. Empty mappings are retained in configuration but omitted from analysis. History scan is not coverage.
- **MCP / AI:** only when enabled in standalone mode; no requirement for other features.

## Rooms in detail
Room name, floor, area, volume, heated flag, emitter type and sensor mappings are independent of HA area configuration. Supported emitter types include underfloor/wall/ceiling heating, convector, radiator, fan-assisted convector/radiator, fan coil, combination and other/none/unknown. Keep manual setup available. Auto-suggestions fill empty roles only.

Optional measurements: temperature/target, RH, CO₂, presence, illuminance, extraction fan, window/door, electrical power, emitter fan state and emitter fan electrical power. Distinguish extract fan from heating fan. The latter can represent HeatMeister, SpeedComfort, Jaga DBE or DIY assistance; no brand-specific requirement.

Room reports include observed mean/range/time/coverage, temperature trend and adjacent fully observed hourly changes, humidity derived from paired temperature/RH, paired comfort, and descriptive fan-on/off temperature change. Presence is observed detection, not proof of occupancy or headcount. Comfort conditional on presence, moisture decay, comparison charts and adjusted fan-assistance experiments are planned.

For CO₂ decay, enter outdoor CO₂ as measured or assumed. Candidate search is local to the selected zone; absence detection and fit checks reduce but do not eliminate confounding. Never directly extrapolate one room's ACH to the dwelling.

## Interpretation
See [methodology](methodology.md). Local data coverage, scan progress and sensor freshness mean different things. Low coverage can bias comparisons; the software reports observed data, not full-period extrapolation. No per-room heat-loss estimate or aggregate room-derived dwelling coefficient is implemented yet.

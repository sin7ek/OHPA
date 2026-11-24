# Virtual Flow Meter (experimental v1)

OHPA can explore virtual flow without treating estimated heat or COP as a measurement. The Research & Virtual Flow tab uses retained local recorder history, supports opt-in CSV export and local training, and reports estimates separately from measured analytics. It does not feed control, sizing or energy totals. No pretrained Amber coefficients are supplied.

## Source review

- [OpenAmber Modbus sensors](https://github.com/Jordi1990/openamber/blob/dev/src/openamber/modbus/sensors.yaml): Tuo and Tui (registers 1202/1203), P0 PWM (1303, already transformed to displayed percent), actual compressor frequency (2103), fan RPM (2105), expansion valve (2107), Ta (2110). Optional refrigerant sensors may be disabled by default. P0 PWM is not a flow measurement; hydraulic resistance and pump curve also matter.
- [OpenAmber core sensors](https://github.com/Jordi1990/openamber/blob/dev/src/openamber/core/sensors.yaml): thermal power is calculated from water flow and heat-exchanger delta T and returns zero if flow sensing is disabled. Stroomverbruik is an estimate from voltage × current and auxiliary assumptions; do not use as measured active electrical power. Neither reported COP nor thermal power can be a predictor if derived from flow.
- [OpenQuatt V2 performance model](https://github.com/OpenQuatt/OpenQuatt/blob/main/openquatt/includes/performance/hp_perf_map_v2.h): predicts thermal power and COP from actual compressor Hz, ambient and supply temperature, with explicit unavailable/outside-domain states. Adopt the separation of model and measurement, not Quatt-specific coefficients.
- [OpenQuatt data sharing](https://github.com/OpenQuatt/OpenQuatt/blob/main/docs/gegevens-delen-technisch.md): separate optional performance telemetry and versioned metadata. OHPA v1 sends nothing; share selected exports voluntarily only.

## Model and data contract

Use measured reference flow to construct the training target Pth [W] = water_factor [Wh/L/K] × flow [L/h] × (Tuo − Tui). Fit regularized log thermal power using actual Hz, Ta, Tuo and externally metered active electrical input; one model per Amber 65/95/120. Infer flow = exp(predicted log power)/(water_factor × delta T). This is a baseline, not a calibrated physical pump curve. Derived COP is not independent. Bounds are rectangular training ranges, not proof of dense support.

UTF-8 CSV header:

```csv
installation_id,model,mode,defrost,buh,steady,power_source,frequency_hz,outside_c,supply_c,return_c,power_w,water_factor,measured_flow_lh
```

Use pseudonymous IDs (one per installation), `amber65`, `amber95` or `amber120`, `heating`, `0` for confirmed inactive defrost and BUH, `1` for confirmed steady state, `metered` for consistent external active power across installations, and 1.163 for water if appropriate. No measured-flow column is needed for prediction. Unknown flags must not be set to zero. For glycol use a verified fluid factor. The electrical boundary must be documented and consistent, including auxiliary heaters; avoid sessions with changes in auxiliary load. Collect temperature, flow and power from the same physical heat-exchanger boundary. Record timestamp UTC, firmware, flowmeter type/calibration, sampling interval, pump PWM, pump operating state, hydraulic layout, fluid and power meter boundary in the original export/metadata. The minimal CLI reads only the listed columns.

Before training, align samples and remove stale/unavailable data; use stable 1-minute summaries from 10–30 s observations. As an initial screening proposal, require at least five minutes after start/defrost/mode change and no significant frequency or pump-speed changes in the preceding two minutes; inspect temperature lag and tune rules against reference data. The CLI trusts the caller's `steady` annotation and does not infer it from history. Exclude cooling, DHW, defrost, BUH, unknown state and delta T below 2 K. Never use estimated flow for minimum-flow protection, pump control or certification.

```sh
python virtual_flow.py fit reference.csv --model amber95 --artifact amber95.json
python virtual_flow.py predict observations.csv --artifact amber95.json
```

One installation can produce an unvalidated local proof of concept; two or more enable leave-one-installation-out evaluation. Minimum 30 eligible rows per installation is a software guard, not evidence of adequacy. Validation gives per-installation bias, mean absolute percentage error and in-domain coverage. The worst installation's held-out 90th percentile absolute relative error is descriptive, not a calibrated prediction interval. Report unavailable points separately; do not hide low coverage. Training weights installations equally. Do not interpret synthetic tests as physical validation.

## Community research and integration

Start with two distinct reference installations (one with a YF-B10 and the other with an Aquaro 35 mm). Differences in their flow readings are not evidence of meter bias. Establish calibrated reference measurements and uncertainty before training. Aim initially for 10–20 distinct installations over 4–8 weeks spanning weather, frequency and temperature regimes, with multiple independent examples per model. The PWM-only and hybrid regressions are exploratory, not calibrated hydraulic pump curves. Fixed pump-speed installations may have stable flow, but do not generalize a single flow value to other homes. Use chronological holdout within installations for future local calibration and untouched installations for final cross-home validation; avoid random row splits. Evaluate by model, pump regime and delta T with MAE L/h, bias, percentage error and coverage. Target <10% mean absolute relative error for indicative monitoring, pending evidence. Quantify reference meter and temperature sensor uncertainty. Develop calibrated prediction intervals only with adequate independent validation.

## OHPA v0.4.9 workflow

1. In Sensor Setup choose the correct Amber model, map true space-heating status (not a mere heat request), defrost, frequency, local outdoor, supply and return temperatures and independently metered active power. Confirm BUH is absent or map separate BUH power; optionally map P0 PWM. For reference exports map physical primary flow.
2. Open Research / VFM, enable research and explicitly confirm measurement boundaries. Changes to sensor configuration require reconfirmation. Existing history collection remains local and automatic; the research module reads that history, not additional HA requests.
3. Select a window up to seven days and preview eligible rows before downloading CSV. A random persistent installation ID and relative minute index replace identifying metadata and absolute timestamps. Review the full CSV locally before sharing; telemetry values can still reveal operating patterns. Do not combine overlapping exports from the same installation.
4. Select one or more nonoverlapping reference CSVs for the same Amber model, choose Thermal, Hydraulic (PWM-only) or Hybrid (combined predictors), then train locally. The latter two require a mapped PWM in both training and prediction. Only model coefficients and anonymized validation diagnostics are saved, not uploaded raw CSV rows. Training replaces the previously saved model for that Amber/method. No network upload takes place.
5. Show estimated flow, COP, observed coverage and per-installation validation diagnostics. A physical measurement, when available, is shown separately; measured analytics always use the original mapping. Estimates are not inserted into history, COP, energy or sizing calculations. A report is a historical estimate, not an instantaneous live sensor.

Automatic filtering requires 100% recorder coverage in a five-minute lookback plus the target minute, confirmed heating mode, no defrost/BUH, compressor variation ≤3 Hz, supply/return variation ≤1 K and PWM variation ≤3 percentage points if mapped. Recorder coverage does not establish physical freshness. These are initial screening thresholds, not validated criteria. The export uses time-weighted minute means; verify sensor time alignment and meter calibration.

The optional CLI `--method hydraulic` fits log flow from PWM; `--method hybrid` fits log flow from all thermal predictors plus PWM and return temperature. All variants require metered active power and steady heating in v1. Model fits and leave-one-installation-out scores are exploratory; no validated prediction interval or automatic control. Community benchmark datasets and independent test results remain to be collected.

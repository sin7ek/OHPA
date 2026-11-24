# HeatPump Analytics — v0.1.0 (prototype)

Standalone, read-only Home Assistant heat-pump analytics, with a local dashboard, sensor mapping wizard, SQLite storage, regional weather support and MCP tools for an external AI client. The software collects HA history directly; the existing HA-MCP container is optional and can remain running for other HA tasks. No model or paid AI API is needed to calculate the metrics.

## Quick start (Unraid / Docker Compose)

1. Extract this folder to a persistent project directory, e.g. `/mnt/user/appdata/heatpump-analytics-project` (not the separate data mount).
2. In Home Assistant, create a dedicated account with the minimum necessary access and create a long-lived access token. A regular user may be sufficient; only consider additional privileges after a concrete permission error. The collector uses GET requests only. A HA access token itself is not intrinsically read-only.
3. On Unraid:

```bash
cd /mnt/user/appdata/heatpump-analytics-project
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
openssl rand -hex 32
```

Edit `.env`: enter the HA URL and token, two different generated secrets (`ADMIN_PASSWORD`, `MCP_SECRET`), and the LAN IP of Unraid as `BIND_IP` (default is localhost only). `HOST_PORT=8095`; change if occupied. `DATA_PATH` can be adjusted to your preferred persistent appdata location. `TZ` must be your HA timezone. For local MCP tests, include `LAN-IP:*` in `MCP_ALLOWED_HOSTS` if needed.

```bash
mkdir -p /mnt/user/appdata/heatpump-analytics
chown 1000:1000 /mnt/user/appdata/heatpump-analytics
chmod 700 /mnt/user/appdata/heatpump-analytics
docker compose up -d --build
docker compose logs -f
```

Open `http://UNRAID-LAN-IP:8095` in your browser (use only on trusted LAN/VPN; Basic authentication over plain HTTP does not encrypt credentials). Username `admin`, password from `.env`. Do not expose this dashboard publicly. Under **Sensoren & setup**, click **Entiteiten ophalen**, select the sensors from the searchable dropdowns and confirm their units. Use **OpenAmber-profiel voorstellen** if your entity IDs match the example installation. Verify mappings; the preset does not configure the BUH boundary or change HA.

Click **Configuratie opslaan & historie ophalen**. Backfill proceeds in one-hour windows, in small batches; newly enabled sensors may have little or no recorded history. The status panel shows last attempts, errors and pending work. The database is retained under `/data` and is not subject to HA Recorder's purge policy. Back up this directory; for a simple consistent backup, stop the container first. No raw-data retention cap is set in this release.

## Sensor mapping

Use instantaneous **power** sensors (W/kW), not daily energy totals (kWh). Always verify units and physical measurement boundaries. Every role is optional in the wizard, but missing roles suppress or limit the corresponding analytics.

| Role | Needed for | Expected units / value |
|---|---|---|
| Indoor temperature | Comfort and heat-loss model | °C/°F/K; climate `current_temperature` attribute also works |
| Indoor target | Degree-hours of comfort deficit | °C; climate `temperature` attribute |
| Outdoor temperature | Heat loss, operating conditions | °C; regional fallback if enabled |
| Supply and return | Signed water-side thermal power | °C each, at the same hydraulic boundary |
| Direct flow **or** volume counter | Thermal power | L/h, L/min, m³/h; alternatively L or m³ cumulative with adequate updates |
| Electrical input | COP and consumption | W/kW, instantaneous, with defined system boundary |
| Separate backup heater | Total system COP if separately supplied | W/kW; explicit choice for included / absent / unknown |
| Compressor frequency | Modulation, time above chosen Hz threshold | Hz |
| Defrost flag | Duration and observed starts | Binary state, configurable active value |
| Space-heating active | Separate DHW/cooling from heating | Required unless heating-only operation for the analyzed period is explicitly confirmed |
| Supply target | Curve and supply comparison | °C |
| Thermal power / COP reported | Optional independent cross-check | W/kW; dimensionless COP |
| Humidity / dew point | Icing conditions | % RH / °C; outdoor only |
| Solar / wind | Weather covariates | W/m² / m/s, km/h, etc. |
| PV production | Optional solar proxy (not irradiance) | W/kW instantaneous, not energy total |
| Coil / refrigerant temperatures | Diagnostics | °C; distinguish pipe/coil sensor from saturation temperature |
| Fan / EEV / pressures | Optional refrigerant diagnostics | rpm or %, steps or %, bar/kPa/MPa/psi |
| Other thermal source | Heat-loss screening | Thermal W/kW, not electrical input of an air conditioner |

### Example OpenAmber mappings

The sample preset recognizes these **exact IDs** if present. Other installations can select differently named entities in the dropdowns.

- `climate.amber_thermostaat_warmtevraag` — attributes `current_temperature`, `temperature`
- `sensor.openamber_buitentemperatuur_ta`
- `sensor.openamber_cv_aanvoertemperatuur_tuo`
- `sensor.openamber_cv_retourtemperatuur_tui`
- `sensor.bijkeuken_openamber_pulse_meter` (verify L/h)
- `sensor.kwh_meter_3_phase_actueel_vermogen_fase_2` (verify measurement boundary)
- `sensor.kwh_meter_3_phase_actueel_vermogen_fase_3` (separate BUH in the example)
- `sensor.openamber_compressor_frequentie`, `binary_sensor.openamber_defrost`
- `sensor.openamber_huidig_setpoint`, `sensor.warmtepomp_cop_2`

For the example Amber 95: select heat-only **only for periods with no DHW or cooling**; separate BUH electricity; 90 Hz max and 89 Hz high-load threshold. Confirm whether the BUH heat is included in the measured supply/return boundary. Do not assume it. Add additional OpenAmber diagnostic sensors by selecting their actual IDs.

## Expert weather

1. Map your own HA weather-station sensors for RH, dew point, irradiance and wind. A KNMI or other weather integration already exposing these as HA sensor states or numeric attributes can be mapped the same way.
2. Optionally enable Open-Meteo and enter approximate latitude/longitude. It fetches **regional modeled** hourly weather via the Historical Forecast API (fallback to forecast API recent past when the former returns an HTTP error). It is not a direct KNMI station integration, and it is not actual on-site observation. Check the source label. Local mapped sensors take precedence by role, even if their history is unavailable. The server sends coordinates to Open-Meteo only when this option is enabled. Open-Meteo usage terms apply; see https://open-meteo.com/en/terms.
3. If RH and outdoor temperature are present but dew point is not mapped, calculate it with the Magnus approximation. Regional solar radiation is an hourly preceding-period mean; regional T, RH, wind and dew point are hourly samples treated as step values. No extrapolation into the future.

## Calculation contract

- All event timestamps are stored as UTC seconds, and displayed in the configured HA timezone with offset. The browser's date input assumes local time matches HA. Use ISO offsets for unambiguous DST queries.
- Historical state changes are collected from the HA REST history endpoint. A state is treated as piecewise constant until its next event; mapped numeric climate attributes are supported. Intervals outside successfully collected coverage, or explicit `unknown`/`unavailable`, remain missing. This is recorder coverage, not a guarantee of sensor freshness or calibration.
- Integrate at the union of all event timestamps and coverage boundaries, not simple row averages. Power is `water_factor × flow(L/h) × (supply − return)` in W. Default factor 1.163 Wh/L/K for water. Preserve negative heat, especially during defrost. A cumulative flow meter uses interval differences; resets and long intervals are excluded. Recorder snapshots at query boundaries can introduce small counter-derived flow errors; direct calibrated flow preferred.
- COP uses only overlapping valid heat and electricity intervals. If BUH electricity is separate, add it to the electrical denominator. If BUH heat is outside the thermal boundary, estimate resistance heat at 1 W/W and label the assumption. Do not double count BUH heat. Confirm the boundary in settings. Missing data is not silently filled with zero, and partial energies are not extrapolated. The reported boundary COP is not necessarily the system COP.
- Count observed off→on starts separately from on-periods censored at window boundaries or unknowns. Negative heat during defrost is direct measured loss; **not** the full counterfactual loss of missed heating and post-defrost recovery.
- Comfort deficit = time integral of `max(target − indoor, 0)`.
- The weather/defrost analysis groups measured exposure by temperature bins, including −3.5 to 0 and 0 to +3.5 °C. It is descriptive, not a causal model. Coil minus dew point is only a proxy for possible condensation.
- Heat-loss model is an exploratory least-squares regression across at least 24 nearly steady hourly observations, sufficient temperature span, known system boundary and ≥95% coverage. It optionally uses observed wind and solar covariates. Internal gains, thermal storage, ventilation and other heat may bias results. It is not EN 12831 sizing and does not predict a certified bivalence point. No model-specific manufacturer capacity curves are embedded.
- Before/after is an **unadjusted** comparison. Compare similar conditions and log interventions. Do not attribute changes solely to stooklijn from this tool. Changing mapping creates a separate normalized series; changing global boundary assumptions changes interpretation of historical windows.

## MCP connection (optional)

This is an additional specialized MCP server, not a replacement for `homeassistant-ai/ha-mcp`. It exposes eight read-only tools: `get_performance`, `get_hourly_performance`, `get_defrost_analysis`, `compare_periods`, `get_heat_loss_model`, `get_weather_defrost_analysis`, `get_latest_measurements`, `get_measurement_setup`. No arbitrary HA calls or write actions.

Local URL:

```
http://UNRAID-LAN-IP:8095/mcp/<MCP_SECRET>/
```

Test locally, using the exact trailing slash and configured host allowlist. For remote AI clients, use HTTPS and a **separate reverse-proxy route that permits only this exact MCP URL**, never the dashboard or `/api/*`. The secret path is a credential. Do not log it in the proxy or share it in screenshots. Use additional authentication at the proxy where your client supports it; no built-in OAuth in this prototype. Do not expose port 8095 directly to the Internet. The separate admin password authenticates the dashboard only. UI setup is protected with Basic auth and a custom write header; keep access local or via VPN/TLS. Set `MCP_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,your-mcp-domain.example` and recreate the container for external connections. NPM should forward the approved Host header and preserve the full path.

Example client question: “Use HeatPump Analytics, get_performance(hours=48). Check data coverage and electrical boundary before interpreting COP. Then retrieve get_weather_defrost_analysis and assess available compressor reserve.”

## Verification and limitations

- Core test suite: `python -m pip install -r requirements.txt pytest && python -m pytest -q tests`.
- Python and JavaScript syntax checked; core tests include stable power, signed defrost, synchronized COP, BUH boundary, sensor gaps, counter reset, censored defrosts, mode separation, unit conversions, weather grouping and mocked HA attribute history.
- This first prototype was not deployed against your live HA or built and tested in Docker in the authoring environment. MCP SDK could not be installed there, so the actual MCP handshake, proxy and Mistral connection remain to be verified on your Unraid machine. Regional API calls also need live validation. No pretense of certified analytics.
- The UI currently offers hourly CSV, not full raw import or export. Automated capacity-curve comparison, certified sizing, weather-normalized intervention estimates and post-defrost recovery metrics are future extensions. No OAuth inside this version.

References: https://developers.home-assistant.io/docs/api/rest/ · https://open-meteo.com/en/docs/historical-forecast-api · https://github.com/modelcontextprotocol/python-sdk

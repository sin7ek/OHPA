# Changelog

Historical development notes retained from the previous README. Some paragraphs describe the state at that time, not current behavior. Refer to current guides for installation and methodology.

## v0.1.1 — optional local weather observations

Map illuminance (lx/klx), independent station temperature, wind direction (circular mean), gust speed, rain rate, wetness (configure the actual active state), and atmospheric pressure. No mapping is required and existing SQLite configuration and series IDs remain unchanged. Illuminance and PV are proxies, not irradiance; the exploratory heat-loss model uses at most one solar covariate (irradiance first, then illuminance, then PV), plus wind if covered. Weather summaries include wetness as percentage of observed time. Derived dew point prefers mapped station temperature when available; use humidity from the same station. Regional fallback is unchanged. New fields require a saved mapping and backfill. No automatic weather correction or causal claims.

## Independent flow meters (implemented)
Select a primary and optional reference meter profile independently in Setup. Profiles filter candidate names, never automatically map or change HA. Reference direct flow or cumulative volume is optional; use the same hydraulic circuit and distinct measurements. The primary alone drives heat and COP. Dashboard, hourly CSV and MCP get_flow_comparison report synchronized coverage, signed bias, absolute error, volume-weighted relative bias, flow bands and defrost/non-defrost comparisons. MQTT freshness beyond recorder coverage, automatic calibration, and lag estimation are not implemented. Verify actual flow unit and calibration. New supported direct flow units include l/hr, L/s and m³/s. Existing mapping and database are retained.

## v0.2.0 – integration profile preview
Source-reviewed OpenAmber, remmob, Electropaultje and OpenQuatt Single profiles use an explicit HA entity prefix and exact suffix/domain/unit match. Missing or ambiguous candidates are not mapped; existing mappings remain unchanged. Preview and select before saving. Quatt Duo requires manual mapping and future per-unit analytics. Amber BUH boundary is a user-confirmed suggestion only. UI language preference is stored in SQLite; English translations cover core navigation/setup/dashboard labels, with some explanatory and diagnostic text still pending. No HA write operations. See docs/integration-profiles.md.

### Live and history tabs
Live reads one HA state snapshot every 15 seconds while visible; history remains independent and uses integrated Recorder data. Live derived heat, delta T, system power and COP require recent and mutually coherent HA timestamps (120 s age, 60 s skew); unavailable values remain blank. HA state timestamps are not proof of physical sensor freshness. Volume-counter-only installations have no derived instantaneous flow. Live water heat is signed across the selected hydraulic boundary and includes cooling/defrost. Live system COP is an instantaneous signed ratio, not period efficiency. No additional writes to HA or database. History explicitly labels average net thermal power.

Historical KPI cards display the actual analyzed duration and start/end timestamps (including UTC offsets), not the currently selected dropdown value. The hourly chart uses the same resolved interval. Average power is time-weighted over valid covered intervals; observed energy is not extrapolated. Live cards have no historical period label.

### Thermal comfort
Historical cards show analysis duration only; exact start/end appear once above the cards. Comfort metrics use mutually observed indoor temperature and target intervals. Degree-hours integrate positive deficit/excess; mean deficit/excess divide by paired observed hours including zero-deficit/excess intervals. ±0.5 °C inclusive is a descriptive reference band, not a clinical comfort threshold. Coverage, paired means, maximum deficit, and below/within/above percentages are exported in hourly CSV, performance API and read-only MCP get_comfort_analysis. Missing data are not zero or extrapolated.

Live contextual measurements (room temperature, target, outdoor and selected slow-changing weather values) display the last known HA state regardless of entity timestamp age. This is not a guarantee of physical freshness. Fast measurements retain the conservative timestamp gate for derived KPIs. Unavailable parent entities invalidate attribute values. Setup previews the selected attribute rather than the parent climate state.

Live cards display available HA states even when timestamps are older, with age/last-known labels. Strict derived metrics are unchanged. When separately metered BUH explicitly reports zero but fails timestamp coherence, a separate labelled estimate may use that last-known state with recent coherent heat and WP power. Missing/nonzero old BUH is not substituted. Estimates do not affect historical calculations.

Expert heat-loss model now has an independent period selector (default seven days) and mutually exclusive hourly rejection counts; minimum eligibility thresholds remain unchanged. Weather/defrost UI provides observed minutes, thermal coverage during active defrost, and descriptive summary in NL/EN. No causal inference; negative heat excludes missed production.

### Extended heat-loss model
Independent 14/30/60/90-day analysis uses retained local data in bounded 28-day chunks; HA backfill remains limited to nine days (older Recorder data not automatically imported). Same-hour model comparisons, approximate 95% gap-aware Newey-West HAC intervals, coefficients and observed/predicted samples are exposed in API/MCP. UI scatterplot holds other predictors at observed means. Manual capacity curve (empty by default) uses linear interpolation only within entered temperatures, matching net capacity and supply conditions is user responsibility. Demand includes intercept and other predictors at observed means, clipped at zero; extrapolation flagged. Indicative crossing and shortfall are not certified sizing. Capacity input is session-only.

### Advanced model diagnostics
Variants include hierarchical delta-T × wind interaction. Default is highest adjusted R² among positive baseline slopes; UI model selection controls diagnostics and sizing. VIF, Pearson correlations, actual-hour residual ACF, absolute residual/fitted correlation, expanding chronological validation and seven-calendar-day rolling slopes are available. Validation uses known test-hour weather, not a forecast; rolling and interaction slope are at zero wind. No causal claims; adjusted R² selection is exploratory. Sizing evaluates interaction at average observed wind. No extra dependencies.

### Optional dwelling profile
A separate local SQLite metadata profile survives sensor configuration updates. Basic orientation, editable facade suggestions and shelter; extended dimensions, ventilation, roof calculator and linked openings; expert U/Rc, explicit adjacent/ground factors, solar metadata, airflow, airtightness and bridges. All optional; no default physical values. Estimates are explicitly partial, with unknown surfaces reported. No automatic ground calculation, infiltration conversion or empirical wind/solar regression integration yet. Read-only MCP get_building_profile exposes the profile and estimate; no address required. Manual source field per surface/bridge and overall basic profile.

The extended dwelling profile includes a persistent heated volume calculator with rectangular and triangular non-overlapping parts, optional flat-roof two-storey/extension template, provenance and explicit adoption into the volume field. Incomplete parts produce only a known subtotal. Saving the profile persists dimensions; no silent overwrite of existing volume.

Scalable dwelling geometry stores storey count, extensions, flat/pitched/mixed roof, sloping plane count and whether roof space is within the heated envelope. Explicit generation creates editable non-overlapping volume parts; roof plane count does not imply volume count. Complex roof volume can be entered directly. Optional separate roof-plane rows in the thermal envelope do not replace existing surfaces. No automatic overwrite of saved heated volume.

Roof calculations persist individually with their horizontal dimensions, pitch, provenance and optional linked roof surface. Flat roofs use 0°. Explicit adoption copies gross area and pitch into an existing roof surface or creates a confirmed new one. Calculations alone do not change the thermal envelope; multiple planes and extension roofs are supported.

Dwelling profile saves now persist a timestamp and read the profile back from SQLite, preserve the selected input level, and show unsaved changes and missing calculation inputs. Flat roof pitch is explicitly entered (drainage slope can be nonzero). No assumed pitch for new roof calculations.

Ventilation supports natural with local extract, separate or total outdoor exchange, explicit ACH scenarios and ranges, and provenance. Combined flow excludes separate infiltration from the subtotal. WTR requires separate flows. Optional HA roles co2_indoor (ppm) and bathroom_fan (on/off) feed read-only local CO2 decay and fan runtime analyses; nominal fan volume is never added to heat loss. CO2 analysis is manually selected and local-zone only, with coverage/sample/decay checks; no automatic adoption.

Basic profile offers an explicitly selected illustrative whole-dwelling W/(m² heated floor area·K) scenario, including air exchange, independent of the component subtotal. Extended profile optionally uses broad illustrative U ranges per exterior surface; per-surface insulation overrides the scenario, explicit unknown disables it. Entered U or applicable Rc takes precedence. No automatic estimates for ground or other boundaries; no certification or population-calibrated defaults. Scenario ranges are assumptions, not confidence intervals. Expert values and existing profiles are preserved; scenarios are off by default.

Calculation levels now differ: Basic uses whole-dwelling illustrative floor-area scenario only in UI; Extended uses surface scenarios when exact values are absent, without expert-only missing-data prompts; Expert uses explicit U/Rc only. Automatic scenarios use declared insulation or a visibly labelled medium example. Saved level controls API result; changing level requires save to refresh calculation. Estimates are not calibrated or certified.

## v0.3.0 — dwelling and analytics update
Dwelling profile levels, air exchange scenarios, optional CO₂ decay and local extract analysis, comfort metrics, regression diagnostics, grouped live sensors and newest-first defrost history. VERSION is the release version; every CI image additionally embeds its exact Git revision. Increment VERSION for subsequent releases; the footer and health endpoint read it automatically. The short revision identifies each build even between release bumps.

## v0.3.1 — CO₂ decay candidates and zone context
Optional CO₂-zone presence, temperature and humidity, plus bathroom temperature/humidity roles. Zone name and volume are optional metadata; seven-day candidate search uses observed CO₂ events, rejects detected presence, reports weather, temperature difference and fan activity with coverage. No absence guarantee or automatic profile adoption. Single CO₂ zone for now; further zones and bathroom moisture analysis are future work.

## v0.4.0 — Rooms
Optional independent room registry, manual or HA area/floor import, device-based mapping suggestions from real HA entities, editable sensor selection and units. Room histories collected with canonical series identities, local temperature/humidity/CO₂/presence and other sensor summaries, paired comfort, per-room CO₂ candidate search. Registry permission failure leaves manual entry available. No automatic whole-house regression changes or aggregate temperature substitution.

## v0.4.1 — Room setup and dynamic diagnostics
Unique per-area HA sensor suggestions (never overwrite), sorted floors, hidden unmapped rooms in analysis, emitter dropdown retaining old text, optional emitter fan state/power, observed hours, canonical units and binary runtime percentages, temperature trends and adjacent fully covered hourly pairs, simultaneous T/RH derived humidity and dew point. Fan-on/off temperature changes are descriptive only, not energy savings or causal estimates.

## v0.4.2 — Emitter terminology
Use fan-assisted convector/radiator labels, distinguish fan coil units, and add wall and ceiling heating. Existing stored emitter codes and sensor roles are unchanged.

## v0.4.3 — Room loading and history collection
Room configuration renders without waiting for HA registries, lazy per-room sensor editors, filtered suggestions limited to 80 matches, five-minute server registry cache and explicit refresh, no duplicate REST state fetch after registry load. Short history windows use batches of up to 24 mappings with fallback splitting; backward scan advances by up to three hours per cycle. Per-room minimum scan progress is distinct from valid measurement coverage. Existing history series and cursors are preserved.

## v0.4.4 — Shared Docker / Home Assistant app
See [installation guide](docs/installation.md). HA OS app uses the same versioned multi-architecture image and Supervisor Core API proxy, with ingress-only access. MCP is optional for Docker; existing configured secrets remain compatible. MCP is not exposed by the HA app. Experimental HA distribution until real Supervisor testing is completed.

## Documentation refresh (v0.4.4)
Reorganized user, installation, optional MCP, methodology, architecture, working document and roadmap. Added missing .env.example (requires user values). No application code change; existing runtime version remains 0.4.4.

## v0.4.5 — HA persistent storage startup fix
Address SQLite unable to open database on Supervisor-managed /data. Dedicated HA image target prepares directory and known SQLite files then drops privileges; standalone image stays non-root. Add root-owned storage smoke test, restart and direct-access rejection. Real HA confirmation pending.

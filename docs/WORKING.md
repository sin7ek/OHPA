# OHPA — living development document

Updated 2026-11-24 · baseline v0.4.7 · [roadmap](../ROADMAP.md).
Purpose: handoff between development sessions; update on each substantive change. Distinguish implemented, verified, proposed and blocked. No dates promised.

## Product principles
Local analytics; HA read-only; vendor neutral; manual configuration always possible; optional dwelling/room/MCP features; measured, estimated and unknown never conflated; no silent defaults that imply precision; common Docker and HA app release; no automatic heat pump control.

## Current evidence
- v0.4.2, v0.4.3 and v0.4.4 CI succeeded. v0.4.4 native Docker smoke and AMD64/ARM64 publish succeeded. Real HA app runtime, ARM runtime, ingress auth and migration unverified.
- Room registry and analysis exist; temperature changes, humidity and descriptive fan comparison are implemented. No integrated room heat-loss model.
- Optional building scenarios and empirical regression are separate; no automatic physical model fusion.
- User field report showed room coverage increasing from ~10% to ~98% during import in older build; not a benchmark of v0.4.3. Do not include private installation data in public examples.
- Documentation now separates current behavior from plans.

## Decisions
| Decision | Rationale |
|---|---|
| One codebase and version, two modes | Avoid drift |
| HA app ingress only, MCP off | Minimize exposure, no extra credentials |
| Docker MCP optional, legacy valid secret compatible | Preserve upgrades |
| Manual room setup and non-overwriting suggestions | HA registry may be incomplete or ambiguous |
| Fan-assisted convector/radiator distinct from fan coil | Vendor-neutral terminology |
| Presence is context only | Binary detection is not headcount |
| Room internal heat transfer cancels at dwelling boundary | Avoid double counting |
| Temperature-only room data do not identify heat-loss coefficient | Physical identifiability |

## P0 — stabilization before deeper models
- [ ] Real HA OS test (amd64 and ARM64 if available): install, start, ingress HTML/assets/API, no public port, auth rejection, Supervisor API and registry, data writable, restart/update retention, backups and timezone.
- [ ] Add automated ingress security tests (direct connection denied, spoofed headers denied, relative assets, unsafe writes denied), MCP disabled/enabled and legacy tests; validate app metadata with Supervisor tooling.
- [ ] Check versioned GHCR manifests and prevent republishing same release tag with different behavioral code.
- [ ] Improve app options for timezone and explicit error handling if Supervisor registry is denied. Document fallback.
- [ ] Benchmark room opening, HA API request count and backfill duration with representative large registry; avoid claiming speedups without measurements. Check per-room scan progress near moving backfill boundary.
- [ ] Improve searchable device picker, unit inference, bulk suggestions preview/confirmation, floor level sorting, room editor preservation and manual override. Keep existing mappings intact.
- [ ] Add representative tests for room dynamics with gaps, irregular samples, paired RH, presence, fan states, and progress. Verify trend denominator matches endpoint times and canonical output units.
- [ ] Audit README/docs and UI translations on every release.

## P1 — room and physical analyses
- [ ] Time-aligned per-room graphs, occupied vs unoccupied comfort with joint coverage and detector caveats; no false absence claim.
- [ ] Moisture decay after showering, temperature/RH pairing, extract fan run time and outdoor absolute humidity; distinguish local effective ventilation from dwelling ACH.
- [ ] Optional volume-weighted indoor temperature with explicit heated-zone inclusion, coverage threshold and missing-room policy; compare with central sensor, never silently replace.
- [ ] Link exterior surfaces and adjacent zones to rooms; area allocation reconciliation, no duplicate openings or heat bridges. Separate ground/adjacent/outside and ventilation boundaries. Explicit partial totals.
- [ ] Implement dynamic energy-balance hypotheses in staged models. Identify effective thermal capacitance only with adequate excitation and known/estimated heat input. Report parameter uncertainty, identifiability, residuals and validation; no room H from temperature alone.
- [ ] Aggregate exterior losses once, compare with whole-dwelling empirical and theoretical estimates without forcing agreement.

## P1 — regression improvements
- [ ] Separate prediction selection from sizing. Show selected model consistently in KPI, diagnostics, export and sizing.
- [ ] Wind direction components from synchronized speed/direction, facade shelter as explicit optional profile, solar orientation and shading proxies, lagged temperature/storage. No private-house hardcoding.
- [ ] Center interactions and report slope at reference/observed wind; assess VIF, coefficient plausibility, autocorrelation, chronological CV, physical constraints and extrapolation. Distinguish exploratory fit from validated model.
- [ ] Synthetic multi-zone and known-parameter tests, weather-separated validation windows and sensitivity analysis.

## P2 — intervention / fan assistance
- [ ] Optional experiment log and alternating fan-on/off blocks, not automatic control. Account for carryover, supply temperature, outdoor temperature, wind/solar, setpoint, heating state and internal gains.
- [ ] Distinguish temperature response, emitter output, COP and total electricity including fan power. Without per-room heat metering, do not claim measured room output.
- [ ] Report uncertainty, exposure and comparable conditions; if data inadequate, return inconclusive. Comfort may improve without net energy savings.

## Open questions
- How should HA app timezone be configured across regions?
- Can Supervisor token access each optional registry endpoint on supported installations?
- What room weighting and minimum joint coverage should be defaults? How to handle overlapping HA areas and open-plan spaces?
- Which emitter telemetry exists (actual fan status, electrical power, valves, per-loop flow)? Do not infer power from on/off alone.
- Which independent validation data are available for thermal mass, envelope and airflow? How to handle unknown heat gains?
- What safe external MCP design, if any, is appropriate for ingress users?

## Handoff checklist
Record commit/version, CI result/link, test environment and exact limitations; update docs/roadmap status; avoid marking a proposed capability implemented. Do not embed credentials, private entity IDs or personal field data in public docs. Preserve raw history and existing configurations.

## v0.4.5 field issue
HA app v0.4.4 repeatedly failed opening /data/analytics.sqlite at startup (502). Likely Supervisor mount ownership. Dedicated HA image startup prepares only /data and known database files, rejects symlinks, then drops to UID/GID 1000. Standalone remains unchanged. CI adds root-owned bind mount and restart smoke test plus direct ingress denial. Actual HA retest pending.

- v0.4.5 first CI attempt (45418149627) failed with `setpriv: No program specified`: changing ENTRYPOINT clears inherited CMD. Explicit HA CMD and entrypoint default argv added. Standalone smoke test and Python/JS checks passed in the failed run; HA retest and publication pending.

## v0.4.6 — release notes
Maintain root CHANGELOG.md for shared/Docker releases and ohpa/CHANGELOG.md for HA update UI. Include shared changes in both. CI requires exact current version headings in both before publication. v0.4.5 CI 45418684969 succeeded; actual HA changelog display and v0.4.6 build still require verification. No runtime changes in this release.

## v0.4.7 — repository rename
Confirmed canonical GitHub repository sin7ek/OHPA. Preserve old GHCR tags in CI; add short aliases. Keep HA image reference and slug unchanged until anonymous pull and real Supervisor upgrade verified. Check public package visibility and update from existing repository URL; never delete existing app to migrate. CI pending; no analytic changes.

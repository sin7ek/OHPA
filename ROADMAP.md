# OHPA roadmap

Status as of 2026-11-24. Priorities are proposals, not commitments or dates. See [working document](docs/WORKING.md) for actionable acceptance criteria. Current release v0.4.5. Keep manual configuration, manufacturer independence and both distributions throughout.

| Milestone | Scope | Status |
|---|---|---|
| v0.4.x | Room registry, descriptive dynamics, fan assistance, performance, shared app packaging | Implemented; HA app field test pending |
| v0.4.x stabilization | Supervisor/ARM validation, authentication tests, persistence, configuration UX, localization, docs, historical scan diagnostics | Next / P0 |
| v0.5 | Room comparison graphs, occupied comfort, paired moisture/CO₂/fan analysis; optional room aggregation | Planned / P1 |
| v0.6 | Dynamic dwelling and multi-zone model; directional weather and physically interpretable heat-loss modelling | Planned / P1 |
| v0.7 | Controlled intervention analysis (stooklijn, emitter fans), energy/comfort comparisons, uncertainty | Planned / P2 |
| v0.8 | HA integration exposing selected analytics as sensor entities, additional profiles including topology-aware multi-unit support | Planned / P2 |
| v0.9 | Validation datasets, backup/retention/export, accessibility, translation, performance and deployment hardening | Planned |
| v1.0 | Reproducible documented stable analytics with explicit scope and limitations | Target, no date |

## Cross-cutting backlog
- Secure optional external MCP for HA app only if a supported threat model/transport exists; add room analysis tools and capability documentation.
- Independent flow comparison: reporting freshness, lag investigation and calibration provenance; no automatic calibration.
- Better defrost recovery/counterfactual analysis, distinguishing observed loss from modeled lost production.
- Capacity curve persistence and provenance; distinguish sizing from predictive model choice.
- Integration profile evidence and field testing across manufacturers; no blanket compatibility claims.

## Release gates
Shared code and version; passing tests and image builds; real install/upgrade checks where relevant; no fabricated measurements; transparent coverage and uncertainty; avoid causal claims without suitable design. Prioritize safety and correctness over feature count.

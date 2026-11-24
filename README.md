# Open HeatPump Analytics (OHPA)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="branding/logos/primary-dark.svg">
  <img alt="Open HeatPump Analytics" src="branding/logos/primary-light.svg" width="360">
</picture>

**Monitor · Analyze · Optimize**

**Current release: v0.4.8 — experimental / pre-1.0**

Local, read-only heat pump analytics for Home Assistant. OHPA turns recorded sensor data into transparent performance, comfort, defrost, weather and exploratory heat-loss analyses. It is manufacturer-independent and does not control your heat pump. No AI subscription or MCP connection is necessary.

## Install

| Installation | Best for | Status |
|---|---|---|
| [Home Assistant OS app](docs/installation.md#home-assistant-os) | Supervisor-managed HA, Green, Yellow, compatible x86/ARM64 | Experimental; real Supervisor validation pending |
| [Docker / Portainer / Unraid](docs/installation.md#docker--portainer--unraid) | HA Container and standalone servers | Docker CI smoke test passed |
| [Docker Compose](docs/installation.md#docker-compose) | Reproducible self-managed install | Same application |
| [Optional MCP](docs/mcp.md) | External AI-assisted analytics | Standalone Docker only; optional |

Both distribution modes share the same code, version, database schema and web UI. The HA image has a dedicated startup layer for Supervisor-owned persistent storage; standalone Docker remains non-root from startup. Images are published for linux/amd64 and linux/arm64. Use one instance per database.

**Quick start HA OS:** add this repository in the App Store, install Open HeatPump Analytics, start and open Web UI. No separate HA token or MCP required. See the installation guide before use.

**Quick start Docker:** use `ghcr.io/sin7ek/ohpa:0.4.8` (or `:latest`), set HA_URL, HA_TOKEN and ADMIN_PASSWORD, persist /data, map port 8095 on a trusted network. See the installation guide for complete configuration and security.

## What OHPA does

- Live readings with timestamps and strict coherence checks for derived power/COP.
- Historical signed water-side heat, electricity, COP, compressor modulation, defrost exposure and coverage; hourly CSV.
- Independent primary/reference flow meter comparison.
- Sensor mapping profiles for OpenAmber, remmob Amber, Electropaultje and OpenQuatt Single; generic manual mode.
- Local and optional regional weather, before/after comparison, exploratory heat-loss regression with diagnostics and manual capacity curves.
- Optional building profile with geometry, insulation assumptions, ventilation, and partial thermal-envelope estimates.
- Optional room profiles, HA area/device discovery, temperature dynamics, humidity/dew point, comfort, CO₂ decay candidates and descriptive fan-assistance comparisons.

OHPA does not estimate missing energy as zero, automatically adjust heating settings, certify heat loss, or establish causal savings from a simple before/after comparison. Per-room dynamic heat-loss modelling and integration into the dwelling regression are planned, not implemented.

## Documentation

| Guide | Contents |
|---|---|
| [Installation](docs/installation.md) | HA OS, Docker, Portainer, Compose, updates, backups and troubleshooting |
| [User guide](docs/user-guide.md) | Mapping, tabs, rooms, ventilation and interpretation |
| [Integration profiles](docs/integration-profiles.md) | Source-reviewed sensor candidates and measurement boundaries |
| [Calculation methodology](docs/methodology.md) | Equations, coverage, assumptions, model diagnostics |
| [Optional MCP](docs/mcp.md) | AI interface, tools and security |
| [Architecture](docs/architecture.md) | Shared distribution, persistence, security, release process |
| [Working document](docs/WORKING.md) | Current state, decisions, open questions, next work and acceptance criteria |
| [Brand guidelines](branding/brand-guidelines.md) | Visual identity and usage |
| [Roadmap](ROADMAP.md) | Priorities and proposed milestones, not promised dates |
| [Docker / shared changelog](CHANGELOG.md) | Release notes and historical development notes |
| [HA app changelog](ohpa/CHANGELOG.md) | Supervisor-visible update notes |

## Verification

[v0.4.4 GitHub Actions](https://github.com/sin7ek/OHPA/actions/runs/45416452335) passed Python tests, JavaScript checks, AMD64 Docker smoke test, metadata consistency and multi-architecture build/publish. This does not establish real HA Supervisor installation, ARM runtime, external MCP interoperability, or scientific validation.

Report problems via GitHub with version/revision, install type, relevant logs and reproduction steps. Remove tokens, secret URLs, private entity identifiers and personal details before sharing.

See [LICENSE](LICENSE). No affiliation with manufacturers, Home Assistant or integration authors.

## Repository rename
The canonical repository is now https://github.com/sin7ek/OHPA. CI publishes short image aliases `ghcr.io/sin7ek/ohpa` and `ghcr.io/sin7ek/ohpa-ha` alongside the original image names. Existing installations should keep their current image and data path. HA app slug and configured legacy image remain unchanged during migration. New package public pull access must be verified before recommending a switch; if unavailable, use the original image.

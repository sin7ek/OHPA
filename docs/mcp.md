# Optional MCP (standalone Docker only)

OHPA calculates everything locally without AI. The specialized read-only Model Context Protocol interface is separate from Home Assistant API access and from general HA-MCP. It is not required for installation, history collection or the dashboard.

## Enable only when needed
Set MCP_ENABLED=true, a distinct random URL-safe MCP_SECRET of at least 24 characters, and MCP_ALLOWED_HOSTS for exact approved client/proxy hosts. Use a different ADMIN_PASSWORD. Omit MCP_SECRET or set MCP_ENABLED=false to disable. Existing valid secrets remain enabled by default for compatibility. HA app ingress mode does not mount MCP.

Local endpoint: `http://SERVER:8095/mcp/<MCP_SECRET>/` (trusted local network only). Remote access requires HTTPS and an exact-path reverse proxy exposing only the MCP endpoint, not /api/*, static assets, dashboard or port 8095 directly. Preserve Host and full path. The secret URL is a credential: never share, log or screenshot it. Use additional proxy authentication where supported. No built-in OAuth; verify client compatibility. Rotate leaked secrets.

## Tools currently registered
| Tool | Scope |
|---|---|
| get_performance | Energy, COP, comfort, coverage |
| get_hourly_performance | Hourly KPIs, max seven days |
| get_defrost_analysis | Observed defrost and negative heat |
| compare_periods | Unadjusted before/after |
| get_heat_loss_model | Exploratory regression, up to 90 days |
| get_building_profile | Optional dwelling profile and partial estimate |
| get_measurement_setup | Mapping, boundaries, health, interventions |
| get_weather_defrost_analysis | Weather-conditioned descriptive exposure |
| get_comfort_analysis | Paired comfort statistics |
| get_flow_comparison | Synchronized primary/reference flow |
| get_latest_measurements | Last locally collected values |

Room-specific MCP tools are not implemented. The tools can reveal measurement and configuration context; treat results as private. No arbitrary HA commands or HA write access are exposed. Example: Analyze the last 48 hours, report coverage and measurement boundaries before interpreting COP, and distinguish observed defrost losses from counterfactual losses.

Actual external client/proxy compatibility requires testing. HA app MCP is a separate future security design, not an exposed ingress workaround.

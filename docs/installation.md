# Install OHPA
## Choose one installation
Both use the same code, version and SQLite data format. HA OS apps are experimental until tested on a real Supervisor. Do not run two installations against the same database.

### Home Assistant OS
1. Open Settings → Apps → App store → menu → Repositories.
2. Add https://github.com/sin7ek/open-heatpump-analytics.
3. Select Open HeatPump Analytics, install and start. The versioned GHCR image must be published first.
4. Open Web UI and optionally show in sidebar.
5. Configure sensors. Room and dwelling profiles are optional.

No separate HA token, admin password, MCP secret, port or reverse proxy is needed. The app uses the Supervisor Core API proxy and accepts only Supervisor ingress traffic. If registry access fails, use manual entity mappings. Back up app data through HA backups. No direct MCP endpoint is provided in this mode.

### Docker / Portainer / Unraid
Use ghcr.io/sin7ek/open-heatpump-analytics:latest or a published version tag (amd64/arm64). Set HA_URL, HA_TOKEN and a random ADMIN_PASSWORD of at least 16 characters. Persist /data (UID 1000 must be able to write). Map container port 8095 only on a trusted LAN or loopback; use HTTPS or VPN as appropriate. Log in as admin. Configure sensor mappings. See main README for Compose.

### Optional MCP (standalone Docker only)
MCP is not required for collection, dashboards or calculations. Omit MCP_SECRET to disable; set MCP_ENABLED=false to explicitly disable even with a previously configured secret. To enable, configure a distinct random URL-safe MCP_SECRET (at least 24 characters) and MCP_ALLOWED_HOSTS for the exact approved client/proxy host. Use a secure HTTPS reverse proxy exposing ONLY the exact MCP endpoint, never the dashboard or configuration API. The URL contains a secret; do not share it. Existing installations with a valid secret remain enabled unless explicitly disabled. HA app ingress is not an external MCP transport. Do not expose its port to work around this limitation.

### Migrating
Stop the source instance and back up its entire /data directory before transferring. Do not share a live SQLite database between instances. Migration into Supervisor-managed app storage has not yet been verified; retain the original backup.

### Release verification
Check footer version and Git revision. CI tests Python and JavaScript and smoke-tests the standalone image before publishing the same source for both architectures. Actual Supervisor installation and ARM hardware validation remain separate checks.

# Installation

Both distributions use the same application. Start with one instance, and never share a writable SQLite database between instances. v0.4.6 is pre-1.0; the HA app is experimental.

## Home Assistant OS

1. Settings → Apps (formerly Add-ons) → App store → menu → Repositories.
2. Add `https://github.com/sin7ek/open-heatpump-analytics`.
3. Select Open HeatPump Analytics, install and start.
4. Open Web UI; optionally enable Show in sidebar.
5. Follow the [user guide](user-guide.md) to map sensors.

Supported image architectures: amd64 and aarch64 (Docker arm64). The app uses the Supervisor Core API proxy and Supervisor Ingress; no separate HA URL, token, admin password, exposed port or MCP is required. Registry access may fail depending on permissions; manual mapping remains available. The default display timezone is Europe/Amsterdam unless configured by the runtime. Check timestamps for other timezones; configurable app timezone is pending.

Check the app logs if startup fails. Real Supervisor installation, data directory ownership, ingress assets/API requests, registry access, timezone handling and ARM runtime still need field validation. Do not bypass ingress or publish the app port to solve access issues.

## Docker / Portainer / Unraid

Create a dedicated HA account with the minimum necessary permissions and a long-lived access token in HA. A token is not intrinsically read-only; OHPA uses read-only API operations. Add permissions only after a concrete error.

Use the following Compose/Portainer stack as a starting point (replace placeholders locally; never commit secrets):

```yaml
services:
  ohpa:
    image: ghcr.io/sin7ek/open-heatpump-analytics:0.4.6
    restart: unless-stopped
    ports:
      - "127.0.0.1:8095:8095"
    environment:
      HA_URL: "http://YOUR_HA_HOST:8123"
      HA_TOKEN: "${HA_TOKEN}"
      ADMIN_PASSWORD: "${ADMIN_PASSWORD}"
      MCP_ENABLED: "false"
      TZ: Europe/Amsterdam
      DATA_DIR: /data
    volumes:
      - /mnt/user/appdata/heatpump-analytics:/data
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    read_only: true
    tmpfs: [/tmp]
```

Set HA_TOKEN and ADMIN_PASSWORD as private stack variables. Generate a random password of at least 16 characters (e.g. `openssl rand -hex 32`). Change the host data directory to suit your platform and make it writable by UID/GID 1000. On Unraid, create it before launching:

```sh
mkdir -p /mnt/user/appdata/heatpump-analytics
chown 1000:1000 /mnt/user/appdata/heatpump-analytics
chmod 700 /mnt/user/appdata/heatpump-analytics
```

Loopback binding is the safe default; to access from another LAN computer, substitute the server's trusted LAN IP for 127.0.0.1, and use a trusted network, VPN or TLS. Basic auth over HTTP does not encrypt credentials. Never expose the dashboard/config API to the public Internet. Open the mapped host port and sign in as admin.

## Docker Compose

Clone the repository to a project directory separate from /data. Copy the included .env.example to .env, restrict its permissions, and fill in values. The repository compose.yaml builds locally rather than pulling the published image; use the stack above for published images.

```sh
cp .env.example .env
chmod 600 .env
docker compose up -d --build
docker compose logs -f
```

MCP is disabled in the example environment. See [optional MCP](mcp.md) only if needed.

## Updates and backups

- HA OS: back up app data, then update through the Supervisor. Published version tag and app metadata must match.
- Docker: back up /data, then pull and recreate using the same volume and environment. Pin a version for predictable upgrades; latest follows main.
- Preserve the complete data directory, including SQLite sidecars if present. Stop the source container for a consistent file-copy backup. No live shared database.
- Changing a sensor mapping can create a new measurement series. Do not delete old data just to change a mapping.
- Cross-mode data migration is not validated. Keep the original backup. No automatic transfer between installations.
- No automatic raw-data retention cap currently exists. Monitor storage.
- Verify footer version and revision after updating.

## Troubleshooting

| Symptom | Check |
|---|---|
| No HA entities | URL reachable from container; token validity; HA permissions |
| HA registry unavailable | Use manual IDs; registry permissions are separate from reading states |
| No history | Recorder includes the entity; correct attribute/unit; actual historical availability |
| Low coverage | Import progress vs valid data coverage; unknown/unavailable states; selected period |
| Slow room import | History scan is asynchronous; up to 24 mappings per short batch and three-hour backward steps; larger batches split on error |
| No COP | Synchronized flow, supply, return, electricity and BUH boundary |
| Missing live derived values | Timestamp age/skew or unavailable sensors |
| Startup permission error / SQLite unable to open database | HA: update to v0.4.5 or newer; dedicated app startup prepares /data then drops privileges. Docker: persistent data directory writable by UID 1000 |
| App loads blank | Check version, ingress logs and assets; report without credentials |

Default backfill is three days, configurable up to nine; locally retained data may support longer analysis. Default polling is two minutes, with a shorter wait while backfill is pending. Scan progress does not mean data exist or are valid.

## Optional AI access

See [MCP guide](mcp.md). It is not part of normal installation. Existing Docker users with a valid MCP secret remain enabled unless explicitly disabled. HA app external MCP is not implemented.

## Release notes
Docker users can read the [shared and Docker changelog](../CHANGELOG.md). Home Assistant users receive [app release notes](../ohpa/CHANGELOG.md) through the native update interface after Supervisor refreshes the repository. Both follow VERSION.

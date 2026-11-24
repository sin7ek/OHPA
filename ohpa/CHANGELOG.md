# Changelog

## 0.4.9

- Experimental local Research & Virtual Flow tab: opt-in reference CSV preview/export, stable heating windows, local model training from selected CSV files, thermal/PWM/hybrid alternatives, held-out installation diagnostics and separate estimated flow/COP report.
- Physical flow, measured COP and existing energy totals remain unchanged. No pretrained model or automatic community upload; real-world validation required.

## 0.4.8

**Visual Identity & Branding**

- Native OHPA icon and logo for the App Store and app details.
- New shared OHPA header, browser icon, automatic light/dark styling, chart colors and line patterns.
- Same web interface as Docker; no changes to analytics, configuration, database, or permissions. Existing image name and slug retained.

## 0.4.7

- Repository renamed to `sin7ek/OHPA`; canonical links updated.
- CI publishes short Docker and HA image aliases alongside existing names.
- Existing HA slug, configured HA image, database paths and analytics unchanged.
- New package public visibility and existing HA repository redirect/update behavior require verification.

## 0.4.6

### Shared
- Added version-specific release notes for both Docker and Home Assistant.
- Release checks require matching version entries in both changelogs.

### Home Assistant
- Native app changelog is available through the Supervisor update interface.
- No change to sensor mappings, calculations or database schema.

## 0.4.5

### Fixed
- Prepare Supervisor-managed persistent storage before starting OHPA as an unprivileged user; resolves the SQLite startup failure that caused a 502 Bad Gateway.
- Restore the explicit web server startup command after overriding the image entrypoint.

### Changed
- Dedicated HA image startup layer; application code remains shared with standalone Docker.
- Added automated startup, restart, database ownership and direct-access rejection checks using simulated Supervisor-style storage.
- AMD64 and ARM64 HA images published. Real Supervisor/ARM runtime verification remains separate.

## 0.4.4

- First experimental Home Assistant app distribution, using Supervisor Core API credentials and Ingress.
- No separate HA token, dashboard password, exposed port or MCP required.
- Includes room sensor suggestions, temperature trends, moisture statistics, emitter fan comparisons, and faster history scanning from the shared application.
- External MCP is not exposed by the HA app.

Earlier OHPA releases were standalone Docker only.

# OHPA visual identity · v1.0

**Open HeatPump Analytics (OHPA)** — Monitor · Analyze · Optimize.

The logo combines a heat pump, thermal circulation and analytics. The artwork is a vector interpretation of the approved concept 1. OHPA is the official abbreviation. Optimization means helping people understand performance; the software remains read-only.

## Asset locations

- Full-name and abbreviated light/dark SVGs: [logos/](logos/). Use the full-name logo in documentation, the OHPA wordmark in compact contexts.
- Shared browser icon and header artwork: [app-icon.svg](../static/branding/app-icon.svg).
- Native HA artwork: [icon.png](../ohpa/icon.png) (128×128) and [logo.png](../ohpa/logo.png) (250×98).
- Shared UI theme: [tokens.css](../static/branding/tokens.css); core palette [tokens.json](tokens.json).
- README uses theme-specific SVGs; the same static assets serve Docker and HA Ingress.

## Color and typography

Navy #0B3A6E (identity), cyan #00B3E6 (cooling/return), teal #14B8A6 (efficiency), orange #FF7A45 (heating/supply), ice #E8F6FF (light surfaces), midnight #0B2038 (dark surfaces). UI variants in CSS use darker strokes on light surfaces and lighter strokes on dark surfaces for contrast. Chart roles are independent of series ordering: thermal/supply orange, electricity navy/blue, return cyan, COP teal, indoor indigo, outdoor slate, reference/secondary purple. Legends and line patterns distinguish series in addition to color. Negative heat remains signed; color must never substitute for sign, label or measurement coverage.

Inter or the local system sans-serif stack; JetBrains Mono or local monospace for technical contexts. No remote fonts or images. The primary SVG wordmarks use outlined lettering.

## Usage

Keep clear space of approximately 1/8 of the mark width. Do not stretch, recolor arbitrarily or add shadows. Use light/dark variants on appropriate backgrounds. Use the icon in small placements; the full wordmark is intended for at least 240px width. Native HA artwork is separate from the configured MDI sidebar icon.

## Verification and maintenance

Review mobile/desktop layouts, both themes, chart legends, native App Store artwork and Ingress-relative URLs after a real HA install. Maintain a single frontend and shared release version. The GitHub repository social preview is configured separately through repository settings and is not applied by a source commit. No change to analytics, database, permissions or app slug.

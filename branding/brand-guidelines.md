# OHPA brand guidelines · v1.0 concept

**Open HeatPump Analytics** — Monitor • Analyze • Optimize.

The mark combines a heat pump, thermal circulation and analytics. Use the primary logo for documentation, the horizontal logo for headers and the app icon for compact contexts. The artwork is a hand-reconstructed vector interpretation of concept 1, not a pixel-exact trace. All wordmarks use outlined Inter glyphs; no font installation is necessary. UI typography: Inter; technical text: JetBrains Mono (install separately).

## Color semantics
Deep blue: identity; cyan: cooling/return; orange: heating/supply; teal: efficiency/COP; ice: light surfaces; midnight: dark surfaces. Use dark text on light surfaces and light text on dark surfaces. Do not use cyan, orange or bright teal as small text on white without checking contrast. Never convey a status by color alone.

## Logo usage
Keep clear space of at least 1/8 of the mark width. Do not stretch, recolor, or add shadows. Use dark-background variants on dark surfaces; black/white variants for single-ink use. Prefer app icon for small sizes; inspect 16px in the target browser. The full logo is intended for larger placements (at least 240px wide).

## Integration
The README uses the full-name light/dark SVGs in `branding/logos/`. The shared web UI uses `static/branding/app-icon.svg` for its header and relative-path favicon (including HA Ingress). The OHPA wordmark is available in light/dark variants. Starter CSS tokens are in `static/branding/tokens.css`; JSON tokens in `branding/tokens.json`. Keep existing semantic chart/status colors until contrast and meaning have been reviewed. The native Home Assistant PNG artwork and repository social preview still need deployment; the latter is set via repository settings.

## Status
OHPA is the official abbreviation. Do not use OPHA. The application remains local and read-only; optimization refers to user insight, not automatic control. Full dashboard redesign and accessibility audit remain separate work. No runtime analytics or configuration changes are intended.

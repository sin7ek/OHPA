# OHPA brand guidelines · v1.0 concept

**Open HeatPump Analytics** — Monitor • Analyze • Optimize.

The mark combines a heat pump, thermal circulation and analytics. Use the primary logo for documentation, the horizontal logo for headers and the app icon for compact contexts. The artwork is a hand-reconstructed vector interpretation of concept 1, not a pixel-exact trace. All wordmarks use outlined Inter glyphs; no font installation is necessary. UI typography: Inter; technical text: JetBrains Mono (install separately).

## Color semantics
Deep blue: identity; cyan: cooling/return; orange: heating/supply; teal: efficiency/COP; ice: light surfaces; midnight: dark surfaces. Use dark text on light surfaces and light text on dark surfaces. Do not use cyan, orange or bright teal as small text on white without checking contrast. Never convey a status by color alone.

## Logo usage
Keep clear space of at least 1/8 of the mark width. Do not stretch, recolor, or add shadows. Use dark-background variants on dark surfaces; black/white variants for single-ink use. Prefer app icon for small sizes; inspect 16px in the target browser. The full logo is intended for larger placements (at least 240px wide).

## Integration
Copy logos and icons into the application's static assets directory. Use `web/tokens.css` as a starting point, not a replacement for the existing theme. Place Home Assistant `icon.png` and `logo.png` alongside the relevant app configuration after verifying the repository layout. Upload `github/social-preview.png` via repository settings. Use SVG in README and documentation; consider GitHub light/dark picture sources. Do not bundle font binaries. Licensing and trademark policy should be set by the project maintainer before publication.

## Status
The existing technical abbreviation OHPA is retained; OPHA-labelled wordmarks from the concept package are not published. The primary full-name artwork and app icon are used in this repository.

Visual assets and starter tokens are supplied. Full UI components, accessibility audit, real dashboard redesign and actual GitHub integration are not included in this first package.
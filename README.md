---
title: IFC KBOB AI Matcher
emoji: "🏗️"
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# IFC-basierte Ökobilanzierung & Material-Matching
Automatisierte Zuordnung von IFC-Bauelementen zu Ökobilanzdaten (KBOB) mit Sentence-Transformer-basiertem Matching und Berechnung von Umweltindikatoren (UBP21, GWP, Primärenergie).

## Anmerkung
Dies ist eine vereinfachte bzw für Hugging Face angepasste Version des Repos [ifc-kbob-ai-matcher](https://github.com/Hygros/ifc-kbob-ai-matcher).
Für weitere Details schau dir dieses Repo an.

## Du möchtest das Tool ausprobieren und der Code interessiert dich weniger?
Dann gehe auf diese Seite: [https://hygroskopisch-ifc-kbob-ai-matcher.hf.space/]

## Experimental: component viewer migration mode

This branch supports a staged no-proxy migration path controlled by
`VIEWER_EMBED_MODE`:

- `VIEWER_EMBED_MODE=iframe` (default): legacy nginx + iframe viewer path.
- `VIEWER_EMBED_MODE=component`: single Streamlit entrypoint on port `7860`
  without nginx startup.

Current status: component mode now renders the viewer iframe via the
component path and uses a dedicated component bridge for selection sync.

Optional overrides for migration testing:

- `COMPONENT_VIEWER_URL`: base URL of the viewer frontend in component mode.
  Default is `/app/static/viewer/index.html` when Streamlit static delivery is used,
  otherwise `http://localhost:3000/`.
- `COMPONENT_STATIC_ORIGIN`: absolute origin for IFC static files in component
  mode (e.g. `http://127.0.0.1:8080`). If unset, defaults are used.
- `COMPONENT_SERVE_MODE`: force delivery mode (`streamlit-static` or
  `viewer-dev-server`). If unset, mode is auto-detected.

Local development tip (component mode with Streamlit static delivery):

- Build and sync viewer assets into `Dashboard/static/viewer`:
  `cd Dashboard/ifc-lite && npm run build:streamlit-static`
- Run end-to-end startup smoke test (build + temporary Streamlit run + endpoint checks):
  `python scripts/smoke_component_mode.py`

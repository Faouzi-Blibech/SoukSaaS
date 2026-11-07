# SoukSaaS owner console: design notes

## Run it without the real backend
```
uv run uvicorn tests.fixtures.mock_owner_api:app --port 8001
$env:API_URL="http://127.0.0.1:8001"; uv run streamlit run dashboard/app.py --server.port 8599
```
(bash: `API_URL=http://127.0.0.1:8001 uv run streamlit run dashboard/app.py --server.port 8599`)

## Direction: night-shift instrument panel
The owner is a merchant leaving autonomous agents running overnight, so the console reads like
an instrument cluster, not a SaaS admin. Near-black, hairline grid, tabular numerals, and a single
object that earns attention: a slowly turning 3D map of the agent team with traffic flowing along
its links. Everything else stays quiet so that red means something.

## Research notes
- Collect UI (analytics-chart, dashboard) is client-rendered, so the fetch returned no gallery
  content; patterns below come from the secondary dashboard sources found by search and the
  three.js r160 `webgl_postprocessing_unreal_bloom` source (EffectComposer, RenderPass,
  UnrealBloomPass, OutputPass; bloom is applied last and tuned low: strength well under 1).
- Dense-dashboard conventions kept: monospace tabular numerals for metrics, IDs, timestamps;
  sans for labels and prose; thin 1px borders instead of shadows; inline sparklines; sans weight
  raised one step on dark backgrounds.

## Tokens
| token | hex | use |
|---|---|---|
| void | `#06080B` | app background |
| panel | `#0B0F14` | cards, sidebar |
| panel-hi | `#111820` | hover, inputs |
| line | `#1B242E` | 1px borders, grid |
| line-hi | `#2A3744` | focused/active borders |
| text | `#DCE3EA` | primary text |
| dim | `#7F8E9D` | labels, axes |
| faint | `#4B5866` | disabled, ticks |
| signal (accent) | `#46B4FF` | the one accent: data, active nav, OK state |
| alarm (alert) | `#FF5A36` | block, escalate, tampered, errors only |

Chart series use signal at stepped opacity plus neutral greys; alarm is reserved for flagged data.

## Type
Instrument Sans (UI, 400/500/600) and JetBrains Mono (numerals, ids, timestamps, 400/500).
Labels are sentence case, 12px, dim; numerals 30px mono with tabular figures.

## Motion
One orchestrated moment: the network scene (auto-rotate 0.04 rad/s, particles, pulses on flagged
actors). Everything else is static; hover only changes border colour. `prefers-reduced-motion`
stops the rotation and particles.

## Deliberately avoided
Purple/pink gradients, glassmorphism, emoji, glow on every element (bloom only in the scene),
all-caps tracked eyebrows, identical rounded card walls (radius 2px on cards, 999px only on
status pills), numbered markers on non-sequences, default Plotly colours.

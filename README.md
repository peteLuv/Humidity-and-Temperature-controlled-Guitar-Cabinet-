# Humidity- and Temperature-Controlled Guitar Cabinet

A climate-controlled "vault" for instruments: a **sealed, cedar-lined upper vault**
(holding a floor guitar rack + guitars) over an **open, vented amp zone** below,
with a tempered-glass cherry door and an active humidity-control system. The
**carcass is built by a woodworker** to the measurements below; this repo is the
final build plan.

## The plan

- **[`cabinet-final-measurements.md`](cabinet-final-measurements.md)** — the
  **carcass measurements** (outer + inner, both compartments) handed to the
  woodworker. Outer 100.8 × 47.3 × 195 cm; vault 97 × 46 × 129.3 cm interior;
  amp zone 97 × 46 × 60 cm.
- **[`cabinet-final-plan.md`](cabinet-final-plan.md)** — the **final build plan**
  for everything after the box: **Spanish cedar lining**, the **cherry frame +
  glass door**, the **glass**, assembly order, and material notes.
  Door detail: [`cherry-door-detail.png`](cherry-door-detail.png).
- **[`guitar-cabinet-plan.html`](guitar-cabinet-plan.html)** — the
  **climate & electrical** master plan (humidity/temperature control, AC Infinity
  Controller 79, humidifier/dehumidifier, fans, sensor, power, sealing, finishing).

## Room visualizer

- **[`apartment-3d.html`](apartment-3d.html)** — interactive 3D planner for the
  apartment: drag furniture, type custom measurements, camera presets, low-walls
  dollhouse mode, auto-saved layouts. Living Room to scale; other rooms approximate.
  Covered by `tests/apartment-3d.test.js`.

### Rebuilding the 3D viewer

`apartment-3d.html` is generated from `apartment-3d.template.html`:

```
python3 build-3d.py
```

This inlines the `vendor/` Three.js modules so the output is a single self-contained
file that opens over `file://` with no install.

## Loadout
8 instruments (held in a floor guitar rack; the oud gets its own spot) + two Orange
combo amps + a pedalboard. Target vault climate: **45–50% RH, ~15–25 °C**.

> Earlier design iterations (V1/V2/V3 cabinets, hanging-rail and 3D-printed hanger
> experiments, the old cut diagrams and PRD) are preserved in the git history.

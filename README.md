# Humidity- and Temperature-Controlled Guitar Cabinet

A climate-controlled "vault" for instruments: a **sealed, cedar-lined upper vault**
(floor guitar rack on a slatted plenum deck) over an **open, vented amp zone** below,
with a cherry face frame, **two tempered-glass doors on a center stile**, warm LED
display lighting, and monitored (passive + manual) humidity control. The **carcass is
built**; this repo is the final build plan.

## The plan (final spec — Rev E)

- **[`cabinet-final-measurements.md`](cabinet-final-measurements.md)** — the
  **as-built measurements**. Outer 101.5 × 47.5 × 195 cm; vault ~97.5 × 46 ×
  ~126.5 cm above the slatted deck; 2.5 in cable/fan plenum; amp zone ~55.6 cm.
- **[`cabinet-final-plan.md`](cabinet-final-plan.md)** — the **final build plan**:
  **Spanish cedar lining**, the **cherry face frame (wide plenum-covering middle
  rail, center stile) + two glass doors**, the **glass**, assembly order, finishes.
  Details: [`cherry-door-detail.png`](cherry-door-detail.png),
  [`center-stile-and-hinge-detail.png`](center-stile-and-hinge-detail.png),
  [`divider-stiffener-detail.png`](divider-stiffener-detail.png).
- **[`cedar-install-guide.md`](cedar-install-guide.md)** — step-by-step cedar
  lining install (seal-first, fitting an out-of-square box, brad + spot-glue).
- **[`structural-review.md`](structural-review.md)** — structural risk review
  (anchor to wall first; divider stiffener).
- **[`cabinet-3d-final.html`](cabinet-3d-final.html)** — interactive **3D model**
  at the Rev E measurements: cedar-lined vault, slatted plenum deck + fans, floor
  rack, amps, cherry frame + two glass doors, warm LED wash, RH display, cedar
  plank-style switcher. Double-click to open (Three.js embedded).
- **[`guitar-cabinet-plan.html`](guitar-cabinet-plan.html)** — the
  **climate & electrical** master plan (monitor + Boveda + manual humidify
  approach, fans, warm LED lighting spec, power, sealing).

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

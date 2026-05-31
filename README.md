# Humidity- and Temperature-Controlled Guitar Cabinet

A DIY plan to convert the tallest IKEA PAX frame into a climate-controlled "vault"
for 8 instruments, with an open amp section below.

- **[`guitar-cabinet-plan.html`](guitar-cabinet-plan.html)** — the full measurement
  and climate plan (open it in a browser).
- **[`cabinet-3d.html`](cabinet-3d.html)** — interactive 3D walkthrough of the
  **full PAX build**: all 8 instruments hung (edge-out), the two Orange amps,
  divider shelf, humidifier/dehumidifier, circulation fans, controllers, sensor,
  the full **power &amp; cabling** layer (GFCI strip, sealed grommet, back raceway,
  drip-looped cable runs, wall outlet), optional Spanish-cedar lining, and glass
  vault door.
- **[`cabinet-3d-metod.html`](cabinet-3d-metod.html)** — alternate **IKEA METOD
  60×60×220 cm** build: a narrower, pure sealed vault for just the 3
  humidity-sensitive acoustics (Oud, Taylor GS Mini Bass, slim Martin), with a
  vented lower equipment bay (controllers + power) and no amp zone. The 4 electrics
  + Backpacker are assumed stored in hard cases (with Boveda) and aren't shown.

Both viewers: **orbit / zoom / pan**, toggle layers, and **hover any part** to see
its name and measurements (the cabinet frame reports the full
external/internal/zone dimensions). **Just double-click** — Three.js is embedded,
so they work offline with no install.

### Rebuilding the 3D viewers

The `*.html` viewers are generated from `*.template.html`. Edit a template, then
run the build (it rebuilds every template):

```
python3 build-3d.py
```

This inlines the `vendor/` Three.js modules as data-URL imports so the output
stays a single self-contained file that opens over `file://` without CORS errors.

## What changed in Revision 2

The original plan was a solid starting point. This revision adds the engineering
that makes the climate goals actually hold:

- **Reality-check section up front** covering the four hardest parts of the build.
- **Structure & safety** — hang instruments from a plywood backer (not raw
  particleboard) and anchor the cabinet to wall studs (anti-tip).
- **Thermal isolation** between the hot (tube) amp below and the vault above.
- **Honest temperature control** — a sealed wooden box tracks room temperature;
  the ITC-308 is framed as a warming switch / alarm, not an air conditioner.
- **Controller deadband logic** so the humidifier and dehumidifier never fight.
- **Layout fix** — the original 8-across row is over-packed (~36.5" of slots vs.
  ~37" usable, before headstocks); the revision adds height-staggering, two depth
  ranks, or reducing the row.
- **Sealing, off-gassing, monitoring/alerts, sensor calibration, GFCI safety, and
  a power-loss failover plan.**
- **A step-by-step build sequence** ending with an empty burn-in before any
  instruments go in.

> All instrument dimensions in the plan are estimates — measure your own
> instruments (especially headstock width) before cutting wood.

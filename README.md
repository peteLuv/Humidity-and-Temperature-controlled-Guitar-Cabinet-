# Humidity- and Temperature-Controlled Guitar Cabinet

A DIY plan to convert the tallest IKEA PAX frame into a climate-controlled "vault"
for 8 instruments, with an open amp section below.

- **[`guitar-cabinet-plan.html`](guitar-cabinet-plan.html)** — the full measurement
  and climate plan (open it in a browser).
- **[`cabinet-3d.html`](cabinet-3d.html)** — an interactive 3D walkthrough you can
  orbit, zoom, and pan. Shows where each of the 8 instruments hangs (edge-out) plus
  the amp, divider shelf, humidifier/dehumidifier, circulation fans, external
  controllers, sensor, optional Spanish-cedar lining, and glass vault door. **Just
  double-click it** — Three.js is embedded, so it works offline with no install.

### Rebuilding the 3D viewer

`cabinet-3d.html` is generated. Edit the scene in `cabinet-3d.template.html`, then:

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

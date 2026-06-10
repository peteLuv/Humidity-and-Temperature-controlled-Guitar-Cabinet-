# Humidity- and Temperature-Controlled Guitar Cabinet

A DIY plan for a climate-controlled "vault" that holds 8 instruments in a sealed
upper compartment over an open amp section below — built from scratch in Baltic
birch with a cherry frame and a tempered-glass door (40 × 23 × 85 in / 216 cm,
fits under an 86.3 in / 220 cm ceiling).

- **[`guitar-cabinet-PRD.pdf`](guitar-cabinet-PRD.pdf)** — the **full Product
  Requirements Document** (also `guitar-cabinet-PRD.html`): finalized "ultimate"
  setup with pros/cons, specifications, system architecture, a complete
  **bill of materials** (frame, glass, hinges, latches, hangers, cedar, climate
  gear, cabling) with cost estimates, cut list, build sequence, control logic,
  and acceptance criteria — with rendered build and parts images.

- **[`guitar-cabinet-plan.html`](guitar-cabinet-plan.html)** — the full measurement
  and climate plan (open it in a browser).
- **[`diy-build-guide.html`](diy-build-guide.html)** — build the **wide cabinet from
  scratch with Home Depot plywood** instead of an IKEA frame: target dimensions, a
  full cut list, shopping list, tools, and step-by-step assembly (including the
  all-important door seal). Pairs with the climate plan above.
- **[`prebuilt-vault-plan.html`](prebuilt-vault-plan.html)** — the **buy-and-retrofit**
  path: skip building the box, buy a solid-wood hinged-door cabinet (or a purpose-built
  humidified guitar cabinet) and master just the **seal** and **electronics**. Sized for
  all 8 instruments hung, no amps (~72″ tall). Includes a shortlist of real products and
  a buyer's checklist.
- **[`cabinet-3d.html`](cabinet-3d.html)** — interactive 3D walkthrough of the
  **from-scratch Baltic-birch build** (40 × 23 × 85 in / 216 cm — fits under
  86.3 in / 220 cm): all 8 instruments hung (edge-out) in a sealed vault over an
  open, vented **24-in amp zone** with the two Orange combos, divider shelf,
  humidifier/dehumidifier, circulation fans, controllers, sensor, the full
  **power &amp; cabling** layer (GFCI strip, sealed grommet, back raceway,
  drip-looped cable runs, wall outlet), optional Spanish-cedar lining, and glass
  vault door. Pairs with the cut diagram (`cabinet-cut-diagram.svg`).
- **[`cabinet-3d-metod.html`](cabinet-3d-metod.html)** — alternate **IKEA METOD
  60×60×220 cm** build: a narrower, pure sealed vault for just the 3
  humidity-sensitive acoustics (Oud, Taylor GS Mini Bass, slim Martin), with a
  vented lower equipment bay (controllers + power) and no amp zone. The 4 electrics
  + Backpacker are assumed stored in hard cases (with Boveda) and aren't shown.

Both viewers: **orbit / zoom / pan**, toggle layers, and **hover any part** to see
its name and measurements (the cabinet frame reports the full
external/internal/zone dimensions). **Just double-click** — Three.js is embedded,
so they work offline with no install.

- **[`apartment-3d.html`](apartment-3d.html)** — a **dollhouse 3D of the whole
  apartment** (L-Line layout) with the climate cabinet placed on the Living
  Room's solid east wall and a person for scale. The Living Room is to scale
  (13'-3" × 21'-4"); other rooms are an approximate reconstruction of the floor
  plan. Toggle walls / labels / furniture / windows.

### Rebuilding the 3D viewers

The `*.html` viewers are generated from `*.template.html`. Edit a template, then
run the build (it rebuilds every template):

```
python3 build-3d.py
```

This inlines the `vendor/` Three.js modules as data-URL imports so the output
stays a single self-contained file that opens over `file://` without CORS errors.

## Current build decisions (latest)

The from-scratch Baltic-birch build is the chosen path. Locked-in choices:

- **Size:** 40 × 23 × **85 in** (216 cm) external — clears an 86.3 in / 220 cm
  ceiling by ~1.3 in. ¾ in Baltic-birch carcass, ½ in back.
- **Layout:** sealed vault (~58.75 in clear) on top over an **open, vented 24 in
  amp zone** holding the two Orange combos + pedalboard.
- **Frame:** solid **cherry** — 1×2 face frame, 1×3 vault door frame.
- **Glazing:** ~37 × 52 in **clear tempered glass, pencil-polished edges**
  (~$384), set on foam glazing tape. UV-filtering only if it sits in direct sun.
- **Controls:** one **AC Infinity Controller 79** (the outlet model) runs the
  circulation fans *and* switches the humidifier + dehumidifier from a single
  unit — it replaces the two Inkbird boxes. (The 69 Pro can't: no AC outlets.)
- **Lumber order:** Baltic birch + cherry are cut to the `diy-build-guide.html`
  §3 list by a hardwood dealer, including the Ø2 in divider grommet hole.
- **Thermal break** under the divider is **optional** (amps only run briefly).

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

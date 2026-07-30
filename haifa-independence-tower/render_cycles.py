#!/usr/bin/env python3
"""Hero renders with Blender Cycles (headless bpy).

Reads out/mesh.json, assigns glass/metal/landscape materials per group, lights
each shot with the real Haifa sun (declination formula for 32.816 N on 21
June) under a Nishita sky, and renders the hero set + two cameras matched to
the client's hand-sketch viewpoints.

    python3 render_cycles.py [--fast]
"""

import json
import math
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FAST = "--fast" in sys.argv

LAT = 32.816


def sun_angles(hour_solar, decl_deg=23.44):
    """Solar altitude/azimuth for Haifa at a given solar hour (21 June)."""
    H = math.radians(15.0 * (hour_solar - 12.0))
    phi, d = math.radians(LAT), math.radians(decl_deg)
    alt = math.asin(math.sin(phi) * math.sin(d) +
                    math.cos(phi) * math.cos(d) * math.cos(H))
    az = math.atan2(math.sin(H),
                    math.cos(H) * math.sin(phi) - math.tan(d) * math.cos(phi))
    return math.degrees(alt), (math.degrees(az) + 180.0) % 360.0


MATS = {
    "new_glass":     dict(base=(0.030, 0.055, 0.060), metallic=0.9, rough=0.08),
    "new_bands":     dict(base=(0.380, 0.275, 0.130), metallic=0.5, rough=0.42),
    "new_roof":      dict(base=(0.330, 0.325, 0.310), rough=0.9),
    "new_basement":  dict(base=(0.400, 0.380, 0.350), rough=0.9),
    "sail_glass":    dict(base=(0.070, 0.095, 0.115), metallic=0.85, rough=0.12),
    "sail_bands":    dict(base=(0.480, 0.490, 0.510), metallic=0.7, rough=0.4),
    "sail_sails":    dict(base=(0.620, 0.630, 0.645), rough=0.5),
    "sail_mast":     dict(base=(0.300, 0.310, 0.330), metallic=0.9, rough=0.4),
    "deck_structure": dict(base=(0.300, 0.280, 0.255), rough=0.95),
    "deck_top":      dict(base=(0.370, 0.355, 0.330), rough=0.9),
    "landscape_terraces": dict(base=(0.115, 0.195, 0.070), rough=1.0),
    "trees":         dict(base=(0.070, 0.130, 0.042), rough=1.0),
    "plot_plate":    dict(base=(0.300, 0.285, 0.260), rough=0.95),
    "city_buildings": dict(base=(0.360, 0.350, 0.330), rough=0.95),
    "city_roads":    dict(base=(0.080, 0.080, 0.085), rough=0.9),
    "terrain":       dict(base=(0.190, 0.175, 0.135), rough=1.0),
    "sea":           dict(base=(0.012, 0.070, 0.085), rough=0.05),
}
SMOOTH = {"new_glass", "sail_glass", "sail_sails", "trees"}

# shot: (name, cam loc, target, focal mm, solar hour, resolution)
SHOTS = [
    ("hero_bay",    (420, 30, 38),    (12, -148, 46), 40, 9.2,  (1920, 1200)),
    ("hero_street", (215, -430, 6),   (32, -212, 52), 40, 9.8,  (1920, 1200)),
    ("hero_aerial", (330, -520, 310), (15, -150, 15), 45, 15.5, (1920, 1200)),
    ("hero_dusk",   (250, -70, 20),   (38, -215, 42), 45, 18.85, (1920, 1200)),
    ("sketch_view_se",     (200, -450, 130), (20, -165, 42), 42, 10.0, (1700, 1300)),
    ("sketch_view_aerial", (90, -640, 340),  (30, -160, 25), 42, 14.5, (1700, 1300)),
]


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_group(name, verts, tris):
    idx = sorted({i for t in tris for i in t})
    remap = {g: k for k, g in enumerate(idx)}
    vs = [tuple(verts[i]) for i in idx]
    fs = [tuple(remap[i] for i in t) for t in tris]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)

    spec = MATS.get(name, dict(base=(0.6, 0.6, 0.6), rough=0.8))
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*spec["base"], 1.0)
    bsdf.inputs["Roughness"].default_value = spec.get("rough", 0.8)
    bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0.0)
    me.materials.append(mat)
    if name in SMOOTH:
        me.shade_smooth()
    return ob


def build_scene():
    with open(os.path.join(OUT, "mesh.json")) as fh:
        data = json.load(fh)
    V = np.array(data["vertices"]).reshape(-1, 3)
    for name, flat in data["groups"].items():
        tris = [tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)]
        if tris:
            add_group(name, V, tris)

    # horizon fill: a sea-coloured disc far beyond the terrain tile
    site_asl = data["meta"].get("site_asl", 9.0)
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=30000,
                                      fill_type="NGON",
                                      location=(0, 0, -site_asl - 0.4))
    disc = bpy.context.active_object
    mat = bpy.data.materials.new("horizon_sea")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.012, 0.07, 0.085, 1)
    b.inputs["Roughness"].default_value = 0.05
    disc.data.materials.append(mat)
    return data["meta"]


def set_sun(hour):
    alt, az = sun_angles(hour)
    scn = bpy.context.scene
    w = bpy.data.worlds.new("world")
    scn.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"   # Blender 5.0 name for the Nishita sky
    try:
        sky.sun_elevation = math.radians(alt)
        sky.sun_rotation = math.radians(180.0 - az)
        sky.sun_intensity = 1.0
        sky.altitude = 20
    except AttributeError:
        pass
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg.inputs["Strength"].default_value = 0.45
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    sun = bpy.data.lights.new("sun", type="SUN")
    sun.energy = 3.0 if alt > 12 else 2.2
    sun.angle = math.radians(0.53)
    if alt <= 12:  # warm low sun
        sun.color = (1.0, 0.55, 0.28)
    ob = bpy.data.objects.new("sun", sun)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90 - alt), 0, math.radians(180 - az))
    return alt, az


def set_camera(loc, target, focal):
    cam = bpy.data.cameras.new("cam")
    cam.lens = focal
    cam.clip_end = 60000
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = np.array(target, float) - np.array(loc, float)
    ob.rotation_euler = (
        math.atan2(math.hypot(d[0], d[1]), -d[2]),
        0.0,
        math.atan2(-d[0], d[1]),
    )
    bpy.context.scene.camera = ob
    return ob


def render_shot(name, loc, target, focal, hour, res):
    scn = bpy.context.scene
    for ob in [o for o in scn.collection.objects if o.type in ("CAMERA", "LIGHT")]:
        bpy.data.objects.remove(ob, do_unlink=True)
    alt, az = set_sun(hour)
    set_camera(loc, target, focal)
    scn.render.engine = "CYCLES"
    scn.cycles.device = "CPU"
    scn.cycles.samples = 48 if FAST else 160
    scn.cycles.use_adaptive_sampling = True
    scn.cycles.use_denoising = True
    scn.render.use_persistent_data = True
    scn.render.resolution_x = res[0] // (2 if FAST else 1)
    scn.render.resolution_y = res[1] // (2 if FAST else 1)
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Punchy"
    scn.view_settings.exposure = -0.2
    scn.render.filepath = os.path.join(OUT, f"{name}.png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"  {name}: sun alt {alt:.0f} az {az:.0f}, "
          f"{time.time()-t0:,.0f}s -> {name}.png", flush=True)


def main():
    clear_scene()
    meta = build_scene()
    print(f"scene built: roof +{meta['roof_m']} m, deck +{meta['deck_h']} m")
    only = sys.argv[sys.argv.index("--only") + 1].split(",") \
        if "--only" in sys.argv else None
    for name, loc, tgt, focal, hour, res in SHOTS:
        if only and name not in only:
            continue
        render_shot(name, loc, tgt, focal, hour, res)


if __name__ == "__main__":
    main()

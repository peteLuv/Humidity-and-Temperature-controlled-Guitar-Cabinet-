#!/usr/bin/env python3
"""Inline out/mesh.json into viewer_template.html -> out/viewer.html.

The published page has to be self-contained (no external fetches), so the
geometry travels inside the document rather than beside it.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

with open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8") as fh:
    tpl = fh.read()
with open(os.path.join(OUT, "mesh_lite.json"), encoding="utf-8") as fh:
    mesh = fh.read()

assert "__MESH_JSON__" in tpl, "template lost its geometry placeholder"
html = tpl.replace("__MESH_JSON__", mesh)

dst = os.path.join(OUT, "viewer.html")
with open(dst, "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"viewer.html ............ {os.path.getsize(dst)/1024:,.0f} kB -> {dst}")

#!/usr/bin/env python3
"""Bundle every *.template.html into a self-contained sibling *.html.

The three.js modules are embedded as base64 data-URL modules inside the import
map, so the resulting files open by double-click (file://) with no external
fetches and no CORS errors. Re-run after editing any template:

    python3 build-3d.py
"""
import base64, glob, pathlib, re, sys

ROOT = pathlib.Path(__file__).parent
VENDOR = ROOT / "vendor"

MODULES = {
    "three": "three.module.js",
    "three/addons/controls/OrbitControls.js": "OrbitControls.js",
    "three/addons/renderers/CSS2DRenderer.js": "CSS2DRenderer.js",
}

def data_url(path: pathlib.Path) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:text/javascript;base64,{b64}"

def main() -> int:
    for f in MODULES.values():
        if not (VENDOR / f).exists():
            print(f"ERROR: missing vendor/{f}", file=sys.stderr)
            return 1
    imports = {spec: data_url(VENDOR / fn) for spec, fn in MODULES.items()}
    entries = ",\n".join(f'    "{spec}": "{url}"' for spec, url in imports.items())
    importmap = '<script type="importmap">\n{ "imports": {\n' + entries + "\n}}\n</script>"

    templates = sorted(ROOT.glob("*.template.html"))
    if not templates:
        print("no *.template.html files found", file=sys.stderr)
        return 1
    for tpl in templates:
        out = ROOT / tpl.name.replace(".template.html", ".html")
        html = re.sub(
            r'<script type="importmap">.*?</script>',
            lambda _m: importmap,
            tpl.read_text(), count=1, flags=re.DOTALL,
        )
        out.write_text(html)
        print(f"wrote {out.name} ({out.stat().st_size/1024:.0f} KB, self-contained)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

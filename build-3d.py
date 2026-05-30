#!/usr/bin/env python3
"""Bundle cabinet-3d.template.html into a self-contained cabinet-3d.html.

The three.js modules are embedded as base64 data-URL modules inside the import
map, so the resulting file opens by double-click (file://) with no external
fetches and no CORS errors. Re-run after editing the template:

    python3 build-3d.py
"""
import base64, pathlib, re, sys

ROOT = pathlib.Path(__file__).parent
VENDOR = ROOT / "vendor"
TEMPLATE = ROOT / "cabinet-3d.template.html"
OUT = ROOT / "cabinet-3d.html"

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
    # build the importmap JSON by hand to keep the big strings readable in diff-free form
    entries = ",\n".join(f'    {spec!r}: "{url}"'.replace("'", '"')
                         for spec, url in imports.items())
    importmap = '<script type="importmap">\n{ "imports": {\n' + entries + "\n}}\n</script>"

    html = TEMPLATE.read_text()
    html = re.sub(
        r'<script type="importmap">.*?</script>',
        lambda _m: importmap,
        html, count=1, flags=re.DOTALL,
    )
    OUT.write_text(html)
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.name} ({kb:.0f} KB, self-contained)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

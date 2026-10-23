#!/usr/bin/env python3
"""Renders an app's adaptive launcher icon to a 512x512 PNG for the F-Droid metadata.

fdroidserver 2.x no longer extracts icons from APKs, so each app needs
metadata/<applicationId>/en-US/icon.png. This composes the adaptive icon's background and
foreground vector drawables into one SVG, keeps the visible centre (72 of 108 dp), rounds the
corners and rasterises it with Inkscape.

Usage: render-icon.py <android-project-dir> <output.png> [color_name=#RRGGBB ...]

Extra arguments define colours the build generates (resValue) instead of declaring in res/values.
"""
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

A = "{http://schemas.android.com/apk/res/android}"
AAPT = "{http://schemas.android.com/aapt}"
SIZE = 512


def colors(res: Path) -> dict:
    out = {}
    for f in res.glob("values*/*.xml"):
        for c in ET.parse(f).getroot().iter("color"):
            out.setdefault(c.get("name"), c.text.strip())
    return out


def color(value, named):
    """Android colour (#RGB, #ARGB, #RRGGBB, #AARRGGBB or @color/x) -> (svg colour, opacity)."""
    if value is None:
        return None, 1.0
    if value.startswith("@color/"):
        value = named[value[7:]]
    if value.startswith("@android:color/"):
        value = {"transparent": "#00000000", "white": "#FFFFFFFF", "black": "#FF000000"}[value[15:]]
    h = value.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    alpha = 1.0
    if len(h) == 8:
        alpha, h = int(h[:2], 16) / 255, h[2:]
    return "#" + h, alpha


class Converter:
    def __init__(self, named):
        self.named = named
        self.defs = []
        self.n = 0

    def gradient(self, el):
        g = el.find("gradient")
        self.n += 1
        gid = f"g{self.n}"
        kind = g.get(A + "type", "linear")
        stops = []
        items = g.findall("item")
        if items:
            for it in items:
                c, a = color(it.get(A + "color"), self.named)
                stops.append((float(it.get(A + "offset")), c, a))
        else:
            for off, key in ((0, "startColor"), (0.5, "centerColor"), (1, "endColor")):
                if g.get(A + key):
                    c, a = color(g.get(A + key), self.named)
                    stops.append((off, c, a))
        stop_xml = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
        if kind == "radial":
            attrs = (f'cx="{g.get(A + "centerX", 0)}" cy="{g.get(A + "centerY", 0)}" '
                     f'r="{g.get(A + "gradientRadius", 0)}"')
            self.defs.append(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" {attrs}>{stop_xml}</radialGradient>')
        else:
            attrs = (f'x1="{g.get(A + "startX", 0)}" y1="{g.get(A + "startY", 0)}" '
                     f'x2="{g.get(A + "endX", 0)}" y2="{g.get(A + "endY", 0)}"')
            self.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" {attrs}>{stop_xml}</linearGradient>')
        return f"url(#{gid})"

    def paint(self, path, name):
        for attr in path.findall(AAPT + "attr"):
            if attr.get("name") == "android:" + name:
                return self.gradient(attr), 1.0
        return color(path.get(A + name), self.named)

    def node(self, el):
        tag = el.tag
        if tag == "group":
            g = lambda k, d: float(el.get(A + k, d))
            px, py = g("pivotX", 0), g("pivotY", 0)
            t = (f'translate({g("translateX", 0) + px} {g("translateY", 0) + py}) '
                 f'rotate({g("rotation", 0)}) scale({g("scaleX", 1)} {g("scaleY", 1)}) translate({-px} {-py})')
            return f'<g transform="{t}">' + "".join(self.node(c) for c in el) + "</g>"
        if tag == "clip-path":
            self.n += 1
            self.defs.append(f'<clipPath id="c{self.n}"><path d="{el.get(A + "pathData")}"/></clipPath>')
            return f'<g clip-path="url(#c{self.n})">'  # closed after siblings, see vector()
        if tag != "path":
            return ""
        fill, fa = self.paint(el, "fillColor")
        stroke, sa = self.paint(el, "strokeColor")
        attrs = [f'd="{el.get(A + "pathData")}"', f'fill="{fill or "none"}"']
        attrs.append(f'fill-opacity="{fa * float(el.get(A + "fillAlpha", 1))}"')
        if el.get(A + "fillType", "").lower() == "evenodd":
            attrs.append('fill-rule="evenodd"')
        if stroke:
            attrs += [f'stroke="{stroke}"', f'stroke-width="{el.get(A + "strokeWidth", 0)}"',
                      f'stroke-opacity="{sa * float(el.get(A + "strokeAlpha", 1))}"',
                      f'stroke-linecap="{el.get(A + "strokeLineCap", "butt")}"',
                      f'stroke-linejoin="{el.get(A + "strokeLineJoin", "miter")}"']
        return "<path " + " ".join(attrs) + "/>"

    def vector(self, file: Path):
        """Returns SVG content scaled to the 108x108 adaptive icon canvas."""
        root = ET.parse(file).getroot()
        vw, vh = float(root.get(A + "viewportWidth")), float(root.get(A + "viewportHeight"))
        body, opened = "", 0
        for c in root:
            part = self.node(c)
            opened += part.endswith('">') and part.startswith("<g clip-path")
            body += part
        body += "</g>" * opened
        return f'<g transform="scale({108 / vw} {108 / vh})">{body}</g>'


def layer(res: Path, ref: str, conv: Converter):
    kind, name = ref[1:].split("/")
    if kind == "color":
        c, a = color(ref, conv.named)
        return f'<rect width="108" height="108" fill="{c}" fill-opacity="{a}"/>'
    for f in sorted(res.glob(f"{kind}*/{name}.xml")):
        return conv.vector(f)
    png = sorted(res.glob(f"{kind}*/{name}.png")) + sorted(res.glob(f"{kind}*/{name}.webp"))
    if png:
        return f'<image width="108" height="108" href="{png[-1].resolve()}"/>'
    raise SystemExit(f"no drawable for {ref}")


def main(project: str, out: str, extra_colors: list):
    res = Path(project) / "app/src/main/res"
    icon = sorted(res.glob("mipmap-anydpi*/ic_launcher.xml"))[0]
    root = ET.parse(icon).getroot()
    conv = Converter(colors(res) | dict(c.split("=", 1) for c in extra_colors))
    layers = [layer(res, root.find(t).get(A + "drawable"), conv) for t in ("background", "foreground")]
    # Visible part of an adaptive icon: the centre 72x72 dp of the 108x108 canvas.
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="18 18 72 72">'
           f'<defs>{"".join(conv.defs)}<clipPath id="shape"><rect x="18" y="18" width="72" height="72" rx="16"/></clipPath></defs>'
           f'<g clip-path="url(#shape)">{"".join(layers)}</g></svg>')
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg)
    subprocess.run(["inkscape", f.name, "--export-type=png", f"--export-filename={out}",
                    f"--export-width={SIZE}", f"--export-height={SIZE}"], check=True, capture_output=True)
    Path(f.name).unlink()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])

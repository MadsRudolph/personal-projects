#!/usr/bin/env python3
"""Laser test coupon for SMD PCB trials on the xTool F1 Ultra.

Outputs (all in mm, origin top-left, Y down):
  esp32_coupon_negative.svg  - filled areas = copper to ABLATE (isolation around ESP32-WROOM-32
                               pads, clearance ladder, trace-width ladder). Import into XCS as
                               'engrave'/fill.
  esp32_coupon_outlines.svg  - same geometry as unfilled outlines (pads + windows), for a
                               vector/isolation-line pass or for checking alignment.
Geometry of the ESP32 pads comes from KiCad's RF_Module:ESP32-WROOM-32 footprint
(38 castellated pads 1.5 x 0.9 mm on 1.27 mm pitch -> 0.37 mm copper gap between pads).
"""
import re, sys

FP = "/usr/share/kicad/footprints/RF_Module.pretty/ESP32-WROOM-32.kicad_mod"

def kicad_pads(path):
    txt = open(path, encoding="utf-8").read()
    pads = []
    for m in re.finditer(r'\(pad "(\d+)" smd rect\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\s*\(size ([\d.]+) ([\d.]+)\)', txt):
        n, x, y, rot, w, h = m.groups()
        w, h = float(w), float(h)
        if rot and float(rot) % 180 == 90:
            w, h = h, w
        pads.append((n, float(x), float(y), w, h))
    return pads

def rect(x, y, w, h):          # centre-based -> corner path
    x0, y0 = x - w/2, y - h/2
    return f"M{x0:.3f},{y0:.3f}h{w:.3f}v{h:.3f}h{-w:.3f}z"

neg, out = [], []   # negative (evenodd fill) paths, outline paths

# ---------------------------------------------------------------- 1. ESP32 footprint
pads = kicad_pads(FP)
exp = [p for p in pads if p[0] != "39"]          # 38 edge pads (skip thermal pad)
cx, cy = 14.0, 16.0                              # place footprint centre on coupon
ISO = 0.45                                       # isolation ring width outside each pad row
# one window per row so the ablated area is small (fast), pads left as islands
rows = {"L": [p for p in exp if p[1] < -8], "R": [p for p in exp if p[1] > 8],
        "B": [p for p in exp if abs(p[1]) < 8]}
for k, ps in rows.items():
    xs = [p[1]-p[3]/2 for p in ps] + [p[1]+p[3]/2 for p in ps]
    ys = [p[2]-p[4]/2 for p in ps] + [p[2]+p[4]/2 for p in ps]
    x0, x1, y0, y1 = min(xs)-ISO, max(xs)+ISO, min(ys)-ISO, max(ys)+ISO
    win = rect(cx+(x0+x1)/2, cy+(y0+y1)/2, x1-x0, y1-y0)
    holes = "".join(rect(cx+p[1], cy+p[2], p[3], p[4]) for p in ps)
    neg.append(win + holes)
    out.append(win); out.extend(rect(cx+p[1], cy+p[2], p[3], p[4]) for p in ps)
# module body outline (18 x 25.5) as reference only
out.append(rect(cx, cy, 18.0, 25.5))

# ---------------------------------------------------------------- 2. clearance ladder
# pairs of 1.5 x 3 mm pads with gap g; the ablated area is just the gap slot + a frame
GAPS = [0.15, 0.20, 0.25, 0.30, 0.37, 0.50]
x = 32.0; y = 6.0; PW, PH = 1.5, 3.0; F = 0.4
for g in GAPS:
    w = 2*PW + g
    win = rect(x + w/2, y, w + 2*F, PH + 2*F)
    pa = rect(x + PW/2, y, PW, PH); pb = rect(x + PW + g + PW/2, y, PW, PH)
    neg.append(win + pa + pb); out.extend([win, pa, pb])
    x += w + 2*F + 1.0

# ---------------------------------------------------------------- 3. trace-width ladder
# a trace of width t, 8 mm long, between two 1.5 mm pads; isolation slot 0.4 mm each side
TRACES = [0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
x0 = 32.0; y = 12.0; L = 8.0; S = 0.4
for t in TRACES:
    total = PW + L + PW
    win = rect(x0 + total/2, y, total + 2*S, PW + 2*S)
    pa = rect(x0 + PW/2, y, PW, PW); pb = rect(x0 + PW + L + PW/2, y, PW, PW)
    tr = rect(x0 + PW + L/2, y, L, t)
    neg.append(win + pa + pb + tr); out.extend([win, pa, pb, tr])
    y += PW + 2*S + 0.8

W, H = 66.0, 34.0
def svg(paths, fill):
    style = 'fill="#000" fill-rule="evenodd" stroke="none"' if fill else 'fill="none" stroke="#000" stroke-width="0.05"'
    body = "\n".join(f'<path d="{d}" {style}/>' for d in paths)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" '
            f'viewBox="0 0 {W} {H}">\n<rect x="0" y="0" width="{W}" height="{H}" fill="none" stroke="#f00" stroke-width="0.05"/>\n{body}\n</svg>\n')

open("esp32_coupon_negative.svg", "w").write(svg(neg, True))
open("esp32_coupon_outlines.svg", "w").write(svg(out, False))
print(f"pads parsed: {len(pads)} (edge: {len(exp)})")
ex = [p for p in exp if p[0] in ("1","2")]
print("pad1->pad2 pitch %.2f, pad width %.2f, copper gap %.2f mm" % (ex[1][2]-ex[0][2], ex[0][4], ex[1][2]-ex[0][2]-ex[0][4]))
print("clearance ladder gaps:", GAPS); print("trace ladder widths:", TRACES)

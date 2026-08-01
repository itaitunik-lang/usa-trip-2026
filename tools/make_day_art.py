#!/usr/bin/env python3
"""Draw a landscape banner for each day of the trip.

The repo is public, so stock photography is a licensing problem. These are
generated instead: a few kilobytes each, no attribution to get wrong, and they
work with no network — which matters in the parks where there is no reception.

To swap in a real photo later, drop `images/day-<iso>.jpg` next to the SVG.
The page prefers the photo when one exists (see hero() in index.html).

    python3 tools/make_day_art.py
"""
from pathlib import Path
import json
import math
import random

W, H = 1200, 420
OUT = Path(__file__).resolve().parent.parent / "images"

# sky_top, sky_bottom, far, mid, near, accent (sun/lights)
PALETTES = {
    "coast":   ("#2b3a4a", "#6d7f88", "#3f4f5c", "#2b3742", "#1a222a", "#f0d9b5"),
    "sequoia": ("#3a2a18", "#8a5a2b", "#4a3a20", "#33281a", "#1e1811", "#f2c26b"),
    "granite": ("#243447", "#7d90a3", "#4a5a6b", "#33404d", "#1f2831", "#ffe6c2"),
    "desert":  ("#40201a", "#c9683a", "#8a3f24", "#5c2a19", "#331710", "#ffd08a"),
    "narrow":  ("#3b1f16", "#9c4a28", "#7a3620", "#4e2214", "#2a120c", "#ffcf94"),
    "hoodoo":  ("#33202c", "#c96a41", "#a24d2c", "#6d3220", "#3a1a12", "#ffd9a0"),
    "slot":    ("#2a1a2e", "#b4562f", "#8c3f24", "#5a2718", "#30150e", "#ffc987"),
    "buttes":  ("#3d1f1c", "#d1703f", "#93402356", "#6b2f1c", "#38160f", "#ffd6a0"),
    "layers":  ("#2c2333", "#b06a45", "#8a5236", "#5f3a26", "#332015", "#ffdcae"),
    "redrock": ("#3a1d1a", "#cf6a3c", "#a4472555", "#733120", "#3d1810", "#ffd3a1"),
    "cactus":  ("#4a2416", "#e08a49", "#a8542a", "#70351c", "#3a1a0f", "#ffe0ab"),
    "city":    ("#141d2e", "#3d4d68", "#243248", "#18212f", "#0e141d", "#ffd98a"),
    "sky":     ("#1b2740", "#5b7fa6", "#33445c", "#222d3d", "#151c26", "#ffe3b0"),
}

# iso -> (archetype, seed)
DAYS = {
    "2026-08-05": ("coast", 11),
    "2026-08-06": ("sequoia", 22),
    "2026-08-07": ("granite", 33),
    "2026-08-08": ("desert", 44),
    "2026-08-09": ("narrow", 55),
    "2026-08-10": ("hoodoo", 66),
    "2026-08-11": ("slot", 77),
    "2026-08-12": ("buttes", 88),
    "2026-08-13": ("layers", 99),
    "2026-08-14": ("redrock", 110),
    "2026-08-15": ("cactus", 121),
    "2026-08-16": ("city", 132),
    "2026-08-17": ("city", 143),
    "2026-08-18": ("city", 154),
    "2026-08-19": ("city", 165),
    "2026-08-20": ("sky", 176),
}


def ridge(rnd, base, amp, steps=14, rough=0.5):
    """A jagged horizon line as SVG path points."""
    pts, step = [], W / steps
    y = base
    for i in range(steps + 1):
        y += rnd.uniform(-amp, amp)
        y = max(base - amp * 2.2, min(base + amp * 1.2, y))
        pts.append((i * step, y))
        amp *= 1 - (1 - rough) * 0.06
    return pts


def poly(pts, fill, opacity=1.0):
    d = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    o = f' opacity="{opacity}"' if opacity < 1 else ""
    return f'<polygon points="0,{H} {d} {W},{H}" fill="{fill}"{o}/>'


def butte(x, w, top, fill):
    """A flat-topped mesa with slightly battered sides."""
    inset = w * 0.14
    return (f'<path d="M{x:.0f},{H} L{x + inset:.0f},{top:.0f} '
            f'L{x + w - inset:.0f},{top:.0f} L{x + w:.0f},{H} Z" fill="{fill}"/>')


def hoodoo(x, w, top, fill):
    """A spire that tapers in steps — the shape Bryce erodes into."""
    h = H - top
    return (f'<path d="M{x:.0f},{H} '
            f'L{x + w * 0.16:.0f},{top + h * 0.42:.0f} '
            f'L{x + w * 0.10:.0f},{top + h * 0.30:.0f} '
            f'L{x + w * 0.28:.0f},{top + h * 0.16:.0f} '
            f'L{x + w * 0.22:.0f},{top + h * 0.06:.0f} '
            f'L{x + w * 0.50:.0f},{top:.0f} '
            f'L{x + w * 0.78:.0f},{top + h * 0.06:.0f} '
            f'L{x + w * 0.72:.0f},{top + h * 0.16:.0f} '
            f'L{x + w * 0.90:.0f},{top + h * 0.30:.0f} '
            f'L{x + w * 0.84:.0f},{top + h * 0.42:.0f} '
            f'L{x + w:.0f},{H} Z" fill="{fill}"/>')


def conifer(x, base, h, fill):
    parts, tiers = [], 4
    for i in range(tiers):
        ty = base - h * (0.30 + 0.175 * i)
        half = h * (0.30 - 0.055 * i)
        parts.append(f'<path d="M{x - half:.0f},{ty + h * 0.16:.0f} '
                     f'L{x:.0f},{ty - h * 0.08:.0f} L{x + half:.0f},{ty + h * 0.16:.0f} Z" fill="{fill}"/>')
    parts.append(f'<rect x="{x - h * 0.035:.0f}" y="{base - h * 0.34:.0f}" '
                 f'width="{h * 0.07:.0f}" height="{h * 0.34:.0f}" fill="{fill}"/>')
    return "".join(parts)


def saguaro(x, base, h, fill):
    t = h * 0.11
    return (f'<g fill="{fill}">'
            f'<rect x="{x:.0f}" y="{base - h:.0f}" width="{t:.0f}" height="{h:.0f}" rx="{t/2:.0f}"/>'
            f'<rect x="{x - h*0.26:.0f}" y="{base - h*0.62:.0f}" width="{t*0.8:.0f}" height="{h*0.34:.0f}" rx="{t*0.4:.0f}"/>'
            f'<rect x="{x - h*0.26:.0f}" y="{base - h*0.62:.0f}" width="{h*0.28:.0f}" height="{t*0.8:.0f}" rx="{t*0.4:.0f}"/>'
            f'<rect x="{x + h*0.20:.0f}" y="{base - h*0.75:.0f}" width="{t*0.8:.0f}" height="{h*0.42:.0f}" rx="{t*0.4:.0f}"/>'
            f'<rect x="{x + t*0.6:.0f}" y="{base - h*0.75:.0f}" width="{h*0.24:.0f}" height="{t*0.8:.0f}" rx="{t*0.4:.0f}"/>'
            f'</g>')


def skyline(rnd, base, fill, lights=None):
    out, x = [], -20
    while x < W + 20:
        w = rnd.uniform(38, 96)
        h = rnd.uniform(70, 250)
        top = base - h
        out.append(f'<rect x="{x:.0f}" y="{top:.0f}" width="{w:.0f}" height="{h + 40:.0f}" fill="{fill}"/>')
        if rnd.random() < 0.25:  # spire
            out.append(f'<rect x="{x + w/2 - 3:.0f}" y="{top - 34:.0f}" width="6" height="34" fill="{fill}"/>')
        if lights:
            for _ in range(int(w * h / 2600)):
                lx = x + rnd.uniform(5, max(6, w - 9))
                ly = rnd.uniform(top + 8, base - 12)
                out.append(f'<rect x="{lx:.0f}" y="{ly:.0f}" width="3" height="4" fill="{lights}" opacity="{rnd.uniform(.35,.9):.2f}"/>')
        x += w + rnd.uniform(3, 12)
    return "".join(out)


def build(kind, seed):
    rnd = random.Random(seed)
    sky_t, sky_b, far, mid, near, accent = PALETTES[kind]
    g = [f'<defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{sky_t}"/><stop offset="1" stop-color="{sky_b}"/>'
         f'</linearGradient></defs>',
         f'<rect width="{W}" height="{H}" fill="url(#s)"/>']

    # sun, kept off-centre so it does not sit behind the day title
    sx, sy = rnd.uniform(W * 0.12, W * 0.34), rnd.uniform(H * 0.16, H * 0.34)
    g.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="{rnd.uniform(26,40):.0f}" fill="{accent}" opacity=".55"/>')

    if kind == "coast":
        g.append(poly(ridge(rnd, H * 0.62, 26), far))
        g.append(f'<rect y="{H*0.72:.0f}" width="{W}" height="{H*0.28:.0f}" fill="{mid}"/>')
        for i in range(3):  # fog bands
            g.append(f'<rect y="{H*(0.50+0.07*i):.0f}" width="{W}" height="16" fill="#ffffff" opacity=".07"/>')
        g.append(poly(ridge(rnd, H * 0.86, 12), near))
    elif kind == "sequoia":
        g.append(poly(ridge(rnd, H * 0.66, 22), far))
        g.append(poly(ridge(rnd, H * 0.80, 16), mid))
        for i in range(9):
            conifer_x = 40 + i * (W / 8.4) + rnd.uniform(-22, 22)
            g.append(conifer(conifer_x, H + 10, rnd.uniform(190, 330), near))
    elif kind == "granite":
        g.append(poly(ridge(rnd, H * 0.55, 40, steps=8, rough=0.85), far))
        g.append(poly(ridge(rnd, H * 0.72, 30, steps=6, rough=0.9), mid))
        g.append(poly(ridge(rnd, H * 0.88, 14), near))
    elif kind in ("desert", "redrock", "buttes", "layers"):
        g.append(poly(ridge(rnd, H * 0.60, 20), far))
        n = {"desert": 3, "redrock": 4, "buttes": 3, "layers": 5}[kind]
        for i in range(n):
            bw = rnd.uniform(120, 230)
            bx = (W / n) * i + rnd.uniform(-30, 60)
            g.append(butte(bx, bw, rnd.uniform(H * 0.36, H * 0.58), mid))
        g.append(poly(ridge(rnd, H * 0.86, 12), near))
    elif kind == "narrow":
        g.append(f'<path d="M0,0 L{W*0.30:.0f},0 L{W*0.40:.0f},{H} L0,{H} Z" fill="{mid}"/>')
        g.append(f'<path d="M{W:.0f},0 L{W*0.70:.0f},0 L{W*0.60:.0f},{H} L{W},{H} Z" fill="{far}"/>')
        g.append(f'<rect x="{W*0.40:.0f}" y="{H*0.80:.0f}" width="{W*0.20:.0f}" height="{H*0.20:.0f}" fill="{accent}" opacity=".25"/>')
        g.append(poly(ridge(rnd, H * 0.94, 6), near))
    elif kind == "hoodoo":
        g.append(poly(ridge(rnd, H * 0.52, 22), far))
        for i in range(11):
            hw = rnd.uniform(46, 88)
            g.append(hoodoo(i * (W / 10.5) - 20, hw, rnd.uniform(H * 0.34, H * 0.62), mid))
        g.append(poly(ridge(rnd, H * 0.90, 10), near))
    elif kind == "slot":
        for i, op in enumerate((0.9, 0.75, 0.6)):
            x0 = W * (0.06 + 0.13 * i)
            g.append(f'<path d="M{x0:.0f},0 C{x0+120:.0f},{H*0.35:.0f} {x0-70:.0f},{H*0.65:.0f} {x0+90:.0f},{H} '
                     f'L0,{H} L0,0 Z" fill="{mid}" opacity="{op}"/>')
            x1 = W * (0.94 - 0.13 * i)
            g.append(f'<path d="M{x1:.0f},0 C{x1-120:.0f},{H*0.35:.0f} {x1+70:.0f},{H*0.65:.0f} {x1-90:.0f},{H} '
                     f'L{W},{H} L{W},0 Z" fill="{far}" opacity="{op}"/>')
        g.append(poly(ridge(rnd, H * 0.95, 5), near))
    elif kind == "cactus":
        g.append(poly(ridge(rnd, H * 0.62, 24), far))
        g.append(poly(ridge(rnd, H * 0.80, 14), mid))
        for i in range(6):
            saguaro(0, 0, 1, near)  # keep signature stable
            g.append(saguaro(70 + i * (W / 5.6) + rnd.uniform(-30, 30), H + 6, rnd.uniform(120, 210), near))
    elif kind == "city":
        g.append(skyline(rnd, H * 0.74, far))
        g.append(skyline(rnd, H * 0.86, mid, lights=accent))
        g.append(skyline(rnd, H + 6, near, lights=accent))
    elif kind == "sky":
        for i in range(5):
            cy = rnd.uniform(H * 0.30, H * 0.72)
            cw = rnd.uniform(180, 340)
            cx = rnd.uniform(-40, W)
            g.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{cw/2:.0f}" ry="{cw/9:.0f}" fill="#ffffff" opacity="{rnd.uniform(.07,.16):.2f}"/>')
        g.append(poly(ridge(rnd, H * 0.90, 10), near))

    # scrim so overlaid text stays readable
    g.append(f'<defs><linearGradient id="v" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="#000" stop-opacity="0"/>'
             f'<stop offset="1" stop-color="#000" stop-opacity=".55"/></linearGradient></defs>')
    g.append(f'<rect width="{W}" height="{H}" fill="url(#v)"/>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice">'
            + "".join(g) + "</svg>")


def main():
    OUT.mkdir(exist_ok=True)
    total = 0
    for iso, (kind, seed) in DAYS.items():
        svg = build(kind, seed)
        p = OUT / f"day-{iso}.svg"
        p.write_text(svg, encoding="utf-8")
        total += len(svg)
        print(f"  {p.name:24} {kind:8} {len(svg)/1024:5.1f} KB")
    print(f"{len(DAYS)} banners, {total/1024:.0f} KB total")


if __name__ == "__main__":
    main()

"""Generate Kleinia bento card art for the installer (light + dark).

Only brand-kit inputs: mark path (100-unit grid), palette, ring/glow motifs.
usage (needs cairosvg + pillow):
  python3 distro/kleinia/art/gen_bento.py <branding>/brand-kit/kleinia-brand-kit <out dir>
then copy the *.webp into data/.
"""
import io, math, random, re, sys
from pathlib import Path

import cairosvg
from PIL import Image

KIT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

KLEIN, PORCELAIN, SKY, ICE = "#002FA7", "#F5F3EE", "#8FA8FF", "#D9E2FF"
GRAPHITE, NIGHT, KLEIN_L, WHITE = "#5B6075", "#030821", "#3D63FF", "#FFFFFF"

# mark geometry in the 100-unit grid: bbox x 26.7..73.3, y 9.8..90.6, axis x=50
MARK_D = re.search(r' d="([^"]+)"', (KIT / "logo/svg/kleinia-mark-blue.svg").read_text()).group(1)
MARK_TOP, MARK_H, BODY_CY = 9.8, 80.8, 67.3


def mark(cx, cy_body, h, fill, opacity=1.0):
    """Place the mark so its body-circle centre sits at (cx, cy_body), height h px."""
    s = h / MARK_H
    return (f'<path fill="{fill}" fill-opacity="{opacity}" fill-rule="evenodd" d="{MARK_D}" '
            f'transform="translate({cx - 50 * s:.2f} {cy_body - BODY_CY * s:.2f}) scale({s:.4f})"/>')


def svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f"<defs>{defs}</defs>{body}</svg>")


def save(name, s, w, h):
    png = cairosvg.svg2png(bytestring=s.encode(), output_width=w, output_height=h)
    Image.open(io.BytesIO(png)).convert("RGB").save(OUT / f"{name}.webp", "WEBP", quality=88, method=6)
    (OUT / f"{name}.svg").write_text(s)


def rings(cx, cy, color, r0, r1, step, op0, op1, sw=2):
    out = []
    n = int((r1 - r0) / step)
    for i in range(n + 1):
        t = i / max(n, 1)
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r0 + i * step:.1f}" fill="none" stroke="{color}" '
                   f'stroke-width="{sw}" stroke-opacity="{op0 + (op1 - op0) * t:.3f}"/>')
    return "".join(out)


def glow(gid, color, op):
    return (f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="{op}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')


# ---------------------------------------------------------------- 1 welcome
# square; composition centred, body circle slightly above centre (content bar sits at the bottom)
def welcome(dark):
    W = H = 1600
    cx, cy, mh = W / 2, H * 0.46, 430
    if dark:
        defs = (f'<radialGradient id="bg" cx="0.5" cy="0.45" r="0.75"><stop offset="0" stop-color="#0A1A5C"/>'
                f'<stop offset="1" stop-color="{NIGHT}"/></radialGradient>' + glow("g", KLEIN_L, 0.55))
        body = (f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
                + rings(cx, cy, KLEIN_L, 200, 1150, 26, 0.38, 0.0)
                + f'<circle cx="{cx}" cy="{cy}" r="430" fill="url(#g)"/>'
                + mark(cx, cy, mh, WHITE))
    else:
        defs = (f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PORCELAIN}"/>'
                f'<stop offset="1" stop-color="{ICE}"/></linearGradient>' + glow("g", ICE, 0.9))
        body = (f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
                + rings(cx, cy, KLEIN, 200, 1150, 26, 0.22, 0.0)
                + f'<circle cx="{cx}" cy="{cy}" r="380" fill="url(#g)"/>'
                + mark(cx, cy, mh, KLEIN))
    save(f"kleinia-welcome-{'dark' if dark else 'light'}", svg(W, H, body, defs), W, H)


# ---------------------------------------------------------------- 2 docs
# a calm stack of rounded "pages"; front page carries heading + text lines + the mark
def docs(dark):
    W, H = 1920, 1080
    pw, ph, r = 620, 760, 36          # page size, radius (brand radius 18 @ 2x)
    x0, y0 = W / 2 - pw / 2 + 40, 150  # front page origin (top clipped below content bar)
    if dark:
        bg = (f'<radialGradient id="bg" cx="0.5" cy="0.25" r="0.9"><stop offset="0" stop-color="#0B1E6B"/>'
              f'<stop offset="1" stop-color="{NIGHT}"/></radialGradient>')
        back = [("#0E1A4D", 0.55), ("#13246A", 0.8)]
        page, head, line, edge = "#0B1440", KLEIN_L, "#2A3A7A", KLEIN_L
    else:
        bg = (f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{ICE}"/>'
              f'<stop offset="1" stop-color="{PORCELAIN}"/></linearGradient>')
        back = [("#B9C8FF", 0.55), ("#C9D5FF", 0.9)]
        page, head, line, edge = WHITE, KLEIN, ICE, "#C3CFF5"
    body = [f'<rect width="{W}" height="{H}" fill="url(#bg)"/>']
    body.append(rings(W / 2, H * 0.42, edge, 380, 1300, 30, 0.18 if dark else 0.30, 0.0, 1.5))
    for i, (c, op) in enumerate(back):          # back pages, offset up-left
        d = (2 - i) * 70
        body.append(f'<rect x="{x0 - d}" y="{y0 - d * 0.55}" width="{pw}" height="{ph}" rx="{r}" '
                    f'fill="{c}" fill-opacity="{op}"/>')
    body.append(f'<rect x="{x0}" y="{y0}" width="{pw}" height="{ph}" rx="{r}" fill="{page}" '
                f'stroke="{edge}" stroke-opacity="0.6" stroke-width="2"/>')
    px, py = x0 + 64, y0 + 70
    body.append(mark(px + 22, py + 30, 72, head))
    body.append(f'<rect x="{px + 80}" y="{py + 6}" width="300" height="34" rx="17" fill="{head}"/>')
    rnd = random.Random(7)
    y = py + 120
    for k in range(9):
        if k == 4:
            y += 26
        wl = pw - 128 - (rnd.randint(0, 3) * 60 if k % 4 != 3 else 220)
        body.append(f'<rect x="{px}" y="{y}" width="{wl}" height="18" rx="9" fill="{line}"/>')
        y += 46
    # the agent's voice: one Sky highlight in the text
    body.append(f'<rect x="{px}" y="{py + 120 + 46 * 5 + 26}" width="180" height="18" rx="9" fill="{SKY}"/>')
    save(f"kleinia-docs-{'dark' if dark else 'light'}", svg(W, H, "".join(body), bg), W, H)


# ---------------------------------------------------------------- 3 community
# Klein-blue field; the mark at the hub, people (rings) and agents (Sky dots) around it
def community(dark):
    W, H = 1920, 1080
    cx, cy = W / 2, H * 0.40
    if dark:
        bg = (f'<radialGradient id="bg" cx="0.5" cy="0.4" r="0.8"><stop offset="0" stop-color="#0A1A5C"/>'
              f'<stop offset="1" stop-color="{NIGHT}"/></radialGradient>' + glow("g", KLEIN_L, 0.5))
        hub, ln, ring = WHITE, KLEIN_L, "#8FA8FF"
    else:
        bg = (f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1A47C4"/>'
              f'<stop offset="1" stop-color="{KLEIN}"/></linearGradient>' + glow("g", "#3D63FF", 0.7))
        hub, ln, ring = WHITE, ICE, ICE
    rnd = random.Random(42)
    nodes = []
    # hand-placed around the hub: inside the area every crop keeps, clear of the bottom content bar
    for i, (dx, dy) in enumerate([(-520, -40), (-330, -230), (-90, -310), (250, -260), (500, -110),
                                  (560, 150), (300, 230), (-260, 220), (-470, 150), (40, 290)]):
        nodes.append((cx + dx, cy + dy, i))
    body = [f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
            rings(cx, cy, ring, 150, 1200, 34, 0.20, 0.0, 1.5),
            f'<circle cx="{cx}" cy="{cy}" r="300" fill="url(#g)"/>']
    for x, y, i in nodes:                                       # spokes
        body.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{ln}" '
                    f'stroke-opacity="0.28" stroke-width="2"/>')
    for (x1, y1, _), (x2, y2, _) in zip(nodes, nodes[1:] + nodes[:1]):   # outer ring of links
        body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{ln}" '
                    f'stroke-opacity="0.14" stroke-width="2"/>')
    for x, y, i in nodes:
        if i % 3 == 1:   # agents: small Sky dots (used sparingly)
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="16" fill="{SKY}"/>')
        else:            # people: the mark's two-circle motif (body r 23.3 / neck r 15.5)
            s = rnd.uniform(0.9, 1.3)
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{23.3 * s:.1f}" fill="none" stroke="{WHITE}" '
                        f'stroke-opacity="0.85" stroke-width="5"/>')
            body.append(f'<circle cx="{x:.1f}" cy="{y - 38 * s:.1f}" r="{15.5 * s * 0.6:.1f}" fill="{WHITE}" '
                        f'fill-opacity="0.85"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="120" fill="{KLEIN if not dark else "#0B1440"}" '
                f'stroke="{WHITE}" stroke-opacity="0.9" stroke-width="4"/>')
    body.append(mark(cx, cy + 22, 150, hub))
    save(f"kleinia-community-{'dark' if dark else 'light'}", svg(W, H, "".join(body), bg), W, H)


for d in (False, True):
    welcome(d); docs(d); community(d)
print("ok")

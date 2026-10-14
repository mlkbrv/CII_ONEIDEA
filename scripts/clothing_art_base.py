"""Palette and drawing helpers shared by the clothing art modules."""

R, RD = "#E4002B", "#A5001F"
W = "#FFFFFF"
FUR, FURD = "#F4EFE6", "#DCD3C4"
INK = "#1A1A1A"
G, GD = "#F2C230", "#E0A81E"
DEN, DEND = "#4A6FA5", "#33527E"
SL, SLD = "#3C4652", "#2A323C"
ICE, ICED = "#BFE3F2", "#8CC4DC"
MINT, MINTD = "#37C2A6", "#28A48C"
OL, OLD = "#6E7A4F", "#57603D"
ORG, ORGD = "#F28C28", "#D9731A"
BRN, BRND = "#8B5A2B", "#6B4220"

HEADER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768" fill="none">'
TORSO = "M150 300 Q150 264 188 264 L226 264 Q256 296 286 264 L324 264 Q362 264 362 300 L362 470 A22 22 0 0 1 340 492 L172 492 A22 22 0 0 1 150 470 Z"
LEGS = "M174 452 L338 452 L334 652 L272 652 L256 520 L240 652 L178 652 Z"


def svg(*parts: str) -> str:
    return HEADER + "\n  " + "\n  ".join(parts) + "\n</svg>\n"


def rect(x, y, w, h, fill, rx=0, extra=""):
    r = f' rx="{rx}"' if rx else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{r} fill="{fill}"{extra}/>'


def circ(cx, cy, r, fill, extra=""):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{extra}/>'


def ell(cx, cy, rx, ry, fill, extra=""):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"{extra}/>'


def path(d, fill, extra=""):
    return f'<path d="{d}" fill="{fill}"{extra}/>'


def line(d, stroke, width, extra=""):
    return f'<path d="{d}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" fill="none"{extra}/>'


def ring(cx, cy, r, stroke, width, extra=""):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{stroke}" stroke-width="{width}" fill="none"{extra}/>'


def frame(x, y, w, h, rx, stroke, width):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" stroke="{stroke}" stroke-width="{width}" fill="none"/>'


def star(cx, cy, k, fill):
    pts = [(0, -k), (k * .3, -k * .3), (k, -k * .2), (k * .5, k * .25), (k * .62, k), (0, k * .55),
           (-k * .62, k), (-k * .5, k * .25), (-k, -k * .2), (-k * .3, -k * .3)]
    d = "M" + " L".join(f"{cx + x:.0f} {cy + y:.0f}" for x, y in pts) + " Z"
    return path(d, fill)

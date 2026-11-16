"""Fig. 1, simplified: the whole study at a glance."""
import sys

W, H = 1500, 560
FONT = "DejaVu Sans, Liberation Sans, sans-serif"
NAVY, ORANGE, GREY, INK = "#1f3a6e", "#c77d14", "#8a8a8a", "#1d1d1d"
out = []
add = out.append


def box(x, y, w, h, fill, stroke, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="2.5"{d}/>')


def text(x, y, s, size=24, weight="normal", fill=INK, anchor="middle", style="normal"):
    add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'font-style="{style}" fill="{fill}" text-anchor="{anchor}">{s}</text>')


def badge(x, y, n):
    add(f'<circle cx="{x}" cy="{y}" r="17" fill="{NAVY}"/>')
    text(x, y + 7, str(n), 20, "bold", "white")


def arrow(x1, y1, x2, y2, color=INK, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="3"{d} '
        f'marker-end="url(#a{color[1:]})"/>')


def card(x, y, w, h, title, sub, fill, stroke, n=None):
    box(x, y, w, h, fill, stroke)
    subs = sub if isinstance(sub, tuple) else (sub,)
    top = y + h / 2 - 4 - 13 * (len(subs) - 1)
    text(x + w / 2, top, title, 27, "bold")
    for i, t in enumerate(subs):
        text(x + w / 2, top + 32 + 25 * i, t, 20, fill="#444")
    if n:
        badge(x + 4, y + 4, n)


add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add("<defs>")
for c in (INK, ORANGE):
    add(f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
        f'markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
add("</defs>")
add(f'<rect width="{W}" height="{H}" fill="white"/>')

BLUE, SAND, PALE = "#eaf0f8", "#fbf2e6", "#f3f3f3"
Y1, H1 = 40, 140
card(20, Y1, 250, H1, "Noisy speech", ("MarVEN,", "DEMAND, FSD50K"), PALE, GREY, 1)
card(320, Y1, 270, H1, "Model", "B1, B3, CM, DFN3, SB", BLUE, NAVY, 2)
card(640, Y1, 270, H1, "Energy split", "against clean speech", SAND, ORANGE, 3)

# direction scale
DX, DW = 960, 280
box(DX, Y1, DW, H1, "white", NAVY)
text(DX + DW / 2, Y1 + 42, "Direction <tspan font-style='italic'>d</tspan>", 27, "bold")
add(f'<line x1="{DX+35}" y1="{Y1+78}" x2="{DX+DW-35}" y2="{Y1+78}" stroke="{INK}" stroke-width="3"/>')
for xx, lab in ((DX + 35, "−1"), (DX + DW / 2, "0"), (DX + DW - 35, "+1")):
    add(f'<line x1="{xx}" y1="{Y1+70}" x2="{xx}" y2="{Y1+86}" stroke="{INK}" stroke-width="3"/>')
    text(xx, Y1 + 110, lab, 20, "bold")
text(DX + 18, Y1 + 132, "noise left", 18, fill="#444", anchor="start")
text(DX + DW - 18, Y1 + 132, "speech lost", 18, fill="#444", anchor="end")

card(1290, Y1, 190, H1, "Claims 1, 2", ("novelty,", "diversity"), BLUE, NAVY)

Y2, H2 = 270, 130
card(320, Y2, 590, H2, "Predictor", "noisy-input features only, LightGBM", BLUE, NAVY, 4)
card(960, Y2, 280, H2, "Speech-loss rank", "per utterance", "white", NAVY)
card(1290, Y2, 190, H2, "Claim 3", "prediction", BLUE, NAVY)

# arrows, top row
mid1 = Y1 + H1 / 2
arrow(270, mid1, 316, mid1)
arrow(590, mid1, 636, mid1)
arrow(910, mid1, 956, mid1)
arrow(1240, mid1, 1286, mid1)
# noisy input to predictor
add(f'<path d="M145,{Y1+H1} L145,{Y2+H2/2} L314,{Y2+H2/2}" fill="none" stroke="{INK}" '
    f'stroke-width="3" marker-end="url(#a{INK[1:]})"/>')
# label path, training only
arrow(775, Y1 + H1, 775, Y2 - 4, ORANGE, "9 7")
text(790, Y1 + H1 + 52, "label, training only", 20, fill=ORANGE, anchor="start", style="italic")
mid2 = Y2 + H2 / 2
arrow(910, mid2, 956, mid2)
arrow(1240, mid2, 1286, mid2)

# gate bar
GY = 450
box(20, GY, 1460, 70, PALE, GREY)
badge(24, GY + 4, 5)
text(750, GY + 45, "Every test: threshold committed to a public repository before the run that decided it",
     22, fill=INK)

add("</svg>")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out))
print("ok")

"""Generate a synthetic ballooned test drawing (samples/drawings/plate_synthetic.png)."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

W, H = 2200, 1500
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default(size=size)


F, FS, FB = font(30), font(24), font(34)
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
BAL_R = 26
chars = []  # (balloon_id, text_bbox_px, balloon_center)


def norm(box):
    x0, y0, x1, y1 = box
    return {"x": round(x0 * 1000 / W), "y": round(y0 * 1000 / H),
            "width": max(1, round((x1 - x0) * 1000 / W)), "height": max(1, round((y1 - y0) * 1000 / H))}


def balloon(n, target_box, center):
    cx, cy = center
    tx = min(max(cx, target_box[0]), target_box[2])
    ty = min(max(cy, target_box[1]), target_box[3])
    d.line([cx, cy, tx, ty], fill="black", width=2)
    d.ellipse([cx - BAL_R, cy - BAL_R, cx + BAL_R, cy + BAL_R], fill="white", outline="black", width=3)
    d.text((cx, cy), str(n), font=FB if n < 10 else F, fill="black", anchor="mm")
    chars.append((n, target_box, center))


def text(xy, s, f=F, anchor="la"):
    d.text(xy, s, font=f, fill="black", anchor=anchor)
    return d.textbbox(xy, s, font=f, anchor=anchor)


def hdim(x0, x1, y, label, ext_from):
    d.line([x0, ext_from, x0, y + 10], fill="black", width=1)
    d.line([x1, ext_from, x1, y + 10], fill="black", width=1)
    d.line([x0, y, x1, y], fill="black", width=2)
    for x, s in ((x0, 1), (x1, -1)):
        d.polygon([(x, y), (x + 18 * s, y - 6), (x + 18 * s, y + 6)], fill="black")
    return text(((x0 + x1) // 2, y - 8), label, anchor="mb")


def vdim(y0, y1, x, label, ext_from):
    d.line([ext_from, y0, x - 10, y0], fill="black", width=1)
    d.line([ext_from, y1, x - 10, y1], fill="black", width=1)
    d.line([x, y0, x, y1], fill="black", width=2)
    for y, s in ((y0, 1), (y1, -1)):
        d.polygon([(x, y), (x - 6, y + 18 * s), (x + 6, y + 18 * s)], fill="black")
    return text((x + 12, (y0 + y1) // 2), label, anchor="lm")


# Border + title
d.rectangle([20, 20, W - 20, H - 20], outline="black", width=4)
text((60, 50), "FRONT VIEW", FS)
text((1500, 50), "SIDE VIEW", FS)

# Front view plate 120x80 mm @ 8 px/mm
S = 8
PX, PY = 350, 350
PW, PH = 120 * S, 80 * S
d.rounded_rectangle([PX, PY, PX + PW, PY + PH], radius=5 * S, outline="black", width=4)
cx, cy = PX + PW // 2, PY + PH // 2
d.ellipse([cx - 12.5 * S, cy - 12.5 * S, cx + 12.5 * S, cy + 12.5 * S], outline="black", width=4)
d.line([cx - 150, cy, cx + 150, cy], fill="gray", width=1)
d.line([cx, cy - 150, cx, cy + 150], fill="gray", width=1)
holes = [(PX + 12 * S, PY + 12 * S), (PX + PW - 12 * S, PY + 12 * S),
         (PX + 12 * S, PY + PH - 12 * S), (PX + PW - 12 * S, PY + PH - 12 * S)]
for hx, hy in holes:
    d.ellipse([hx - 3.3 * S, hy - 3.3 * S, hx + 3.3 * S, hy + 3.3 * S], outline="black", width=3)

# 1: overall length
b = hdim(PX, PX + PW, PY - 110, "120 ±0.1", PY - 5)
balloon(1, b, (b[2] + 60, b[1] - 20))
# 2: overall height
b = vdim(PY, PY + PH, PX + PW + 120, "80 ±0.1", PX + PW + 5)
balloon(2, b, (b[2] + 60, b[1] - 40))
# 3: centre bore diameter
d.line([cx + 12.5 * S * 0.7, cy - 12.5 * S * 0.7, cx + 230, cy - 230], fill="black", width=2)
b = text((cx + 235, cy - 250), "Ø25 ±0.05")
balloon(3, b, (b[2] + 50, b[1] + 10))
# 4: hole pattern callout 4X Ø6.6 THRU
hx, hy = holes[2]
d.line([hx + 20, hy + 20, hx + 120, hy + 150], fill="black", width=2)
b = text((hx + 125, hy + 135), "4X Ø6.6 +0.1/-0")
balloon(4, b, (b[0] - 50, b[3] + 30))
# 5: position FCF under hole callout
fx, fy = b[0], b[3] + 15
cells = [70, 170, 50, 50, 50]
x = fx
for w in cells:
    d.rectangle([x, fy, x + w, fy + 50], outline="black", width=2)
    x += w
pc = (fx + 35, fy + 25)
d.ellipse([pc[0] - 15, pc[1] - 15, pc[0] + 15, pc[1] + 15], outline="black", width=2)
d.line([pc[0] - 22, pc[1], pc[0] + 22, pc[1]], fill="black", width=2)
d.line([pc[0], pc[1] - 22, pc[0], pc[1] + 22], fill="black", width=2)
text((fx + 80, fy + 25), "Ø0.2", anchor="lm")
mc = (fx + 205, fy + 25)
d.ellipse([mc[0] - 17, mc[1] - 17, mc[0] + 17, mc[1] + 17], outline="black", width=2)
text(mc, "M", FS, anchor="mm")
for i, lab in enumerate("ABC"):
    text((fx + 240 + 25 + 50 * i, fy + 25), lab, anchor="mm")
fcf = (fx, fy, x, fy + 50)
balloon(5, fcf, (x + 50, fy + 25))
# 6: hole pitch 96 (basic)
b = hdim(holes[0][0], holes[1][0], PY - 45, "96", PY + 12 * S)
bb = (b[0] - 8, b[1] - 4, b[2] + 8, b[3] + 4)
d.rectangle(bb, outline="black", width=2)
balloon(6, bb, (bb[0] - 60, bb[1] - 25))
# 7: corner radius
d.line([PX + PW - 12, PY + 12, PX + PW + 60, PY - 40], fill="black", width=2)
b = text((PX + PW + 65, PY - 60), "R5 TYP")
balloon(7, b, (b[2] + 45, b[1]))

# Side view: thickness 10 ±0.1 and flatness
SX, SY = 1600, 350
d.rectangle([SX, SY, SX + 10 * S, SY + PH], outline="black", width=4)
b = hdim(SX, SX + 10 * S, SY - 110, "10 ±0.1", SY - 5)
balloon(8, b, (b[2] + 60, b[1] - 20))
# 9: flatness FCF
fx, fy = SX + 10 * S + 60, SY + 200
d.rectangle([fx, fy, fx + 70, fy + 50], outline="black", width=2)
d.rectangle([fx + 70, fy, fx + 170, fy + 50], outline="black", width=2)
d.polygon([(fx + 18, fy + 35), (fx + 30, fy + 15), (fx + 55, fy + 15), (fx + 43, fy + 35)], outline="black", width=2)
text((fx + 120, fy + 25), "0.05", anchor="mm")
d.line([fx, fy + 25, SX + 10 * S, fy + 25], fill="black", width=2)
flat = (fx, fy, fx + 170, fy + 50)
balloon(9, flat, (fx + 220, fy + 25))
# 10: surface finish
sx, sy = SX + 10 * S + 60, SY + 420
d.line([sx, sy, sx + 15, sy + 30, sx + 50, sy - 30, sx + 110, sy - 30], fill="black", width=2)
b = text((sx + 55, sy - 62), "Ra 1.6", FS)
sf = (sx, b[1], sx + 110, sy + 30)
balloon(10, sf, (sx + 160, sy))
# datum labels
for lab, (x0, y0) in {"A": (SX - 90, SY + PH - 60), "B": (PX - 110, PY + PH // 2), "C": (PX + PW // 2 + 150, PY + PH + 30)}.items():
    d.rectangle([x0, y0, x0 + 44, y0 + 44], outline="black", width=2)
    text((x0 + 22, y0 + 22), lab, anchor="mm")

# Notes + title block
ny = 1150
text((60, ny), "NOTES:", FS)
text((60, ny + 40), "1. ALL DIMENSIONS IN MILLIMETRES.", FS)
b = text((60, ny + 75), "2. BREAK ALL SHARP EDGES 0.2 MAX.", FS)
balloon(11, b, (b[2] + 50, b[1] + 12))
text((60, ny + 110), "3. UNLESS OTHERWISE SPECIFIED: X.X ±0.2  X.XX ±0.05  ANGLES ±0.5°", FS)
text((60, ny + 145), "4. MATERIAL: AL 6061-T6 PER AMS 4027.", FS)
tb = (1400, 1130, W - 40, H - 40)
d.rectangle(tb, outline="black", width=3)
for i, (k, v) in enumerate([("PART NO.", "CF-1001"), ("TITLE", "MOUNTING PLATE"), ("DWG NO.", "CF-1001-D"),
                            ("REV", "B"), ("SCALE", "1:1  UNITS: mm")]):
    y = tb[1] + 15 + i * 60
    text((tb[0] + 20, y), k, FS)
    text((tb[0] + 220, y), v, F)
    if i:
        d.line([tb[0], y - 10, tb[2], y - 10], fill="black", width=1)

out = ROOT / "samples" / "drawings"
out.mkdir(parents=True, exist_ok=True)
img.save(out / "plate_synthetic.png")
print("Generated samples/drawings/plate_synthetic.png")

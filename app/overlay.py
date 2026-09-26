"""Balloon placement and rendering. Always draws on a copy - the original drawing stays intact."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

STATUS_COLORS = {"Accepted": (22, 163, 74), "Corrected": (37, 99, 235), "Rejected": (220, 38, 38),
                 "review": (217, 119, 6), "Pending": (75, 85, 99)}
CLEAN = (29, 78, 216)  # final deliverable colour


def _font(size: int):
    for name in ("Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def row_color(row: dict):
    if row["status"] == "Pending" and row["flagged"]:
        return STATUS_COLORS["review"]
    return STATUS_COLORS.get(row["status"], STATUS_COLORS["Pending"])


def balloon_radius(img: Image.Image) -> int:
    return max(13, int(max(img.size) * 0.011))


def place_balloons(img: Image.Image, rows: list[dict]) -> None:
    """Assign balloon_xy to rows without a drawing balloon: nearest free white space, no overlaps."""
    gray = np.array(img.convert("L"))
    ink = (gray < 160).astype(np.float32)
    integral = ink.cumsum(0).cumsum(1)
    H, W = gray.shape
    r = balloon_radius(img)

    def ink_in(cx, cy, rad):
        x0, y0, x1, y1 = int(cx - rad), int(cy - rad), int(cx + rad), int(cy + rad)
        if x0 < 2 or y0 < 2 or x1 >= W - 2 or y1 >= H - 2:
            return 1e9
        s = integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0]
        return s / ((x1 - x0) * (y1 - y0))

    occupied = [(row["balloon_xy"][0], row["balloon_xy"][1], row["balloon_xy"][2])
                for row in rows if row.get("balloon_xy")]
    boxes = [row["loc"] for row in rows if row.get("loc")]
    for row in rows:
        if row.get("balloon_xy") or not row.get("loc"):
            continue
        x0, y0, x1, y1 = row["loc"]
        cx0, cy0 = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = (x1 - x0) / 2, (y1 - y0) / 2
        best, best_score = None, 1e18
        for dist in (r * 1.6, r * 2.6, r * 3.8, r * 5.5):
            for k in range(16):
                a = k * math.pi / 8
                dx, dy = math.cos(a), math.sin(a)
                # step out from the box edge along direction a
                t = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
                cx, cy = cx0 + dx * (t + dist), cy0 + dy * (t + dist)
                if any(math.dist((cx, cy), (ox, oy)) < r + orr + 6 for ox, oy, orr in occupied):
                    continue
                overlap_box = any(b[0] - r < cx < b[2] + r and b[1] - r < cy < b[3] + r for b in boxes)
                score = ink_in(cx, cy, r * 1.15) * 100 + dist / r + (8 if overlap_box else 0) + (0.3 if dy > 0.5 else 0)
                if score < best_score:
                    best, best_score = (int(cx), int(cy), r), score
            if best and best_score < 3 + dist / r:
                break
        if best is None:
            best = (int(max(r, x0 - r * 2)), int(max(r, y0 - r * 2)), r)
        row["balloon_xy"] = best
        occupied.append(best)


def _leader_end(cx, cy, box):
    x0, y0, x1, y1 = box
    return min(max(cx, x0), x1), min(max(cy, y0), y1)


def draw(img: Image.Image, rows: list[dict], selected: str | None = None, clean: bool = False) -> Image.Image:
    """clean=False: review view (status colours, target boxes). clean=True: final ballooned drawing."""
    out = img.copy().convert("RGB")
    d = ImageDraw.Draw(out, "RGBA")
    lw = max(2, int(max(out.size) / 900))
    for row in rows:
        if clean and row["status"] == "Rejected":
            continue
        color = CLEAN if clean else row_color(row)
        sel = row["id"] == selected
        w = lw * (3 if sel else 1)
        if row.get("loc") and not clean:
            x0, y0, x1, y1 = row["loc"]
            pad = 3
            d.rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], outline=color + (255,),
                        fill=color + (70 if sel else 28,), width=w)
        if not row.get("balloon_xy"):
            continue
        cx, cy, r = row["balloon_xy"]
        if row.get("loc"):
            ex, ey = _leader_end(cx, cy, row["loc"])
            ang = math.atan2(ey - cy, ex - cx)
            sx, sy = cx + r * math.cos(ang), cy + r * math.sin(ang)
            if row["generated"] and math.dist((sx, sy), (ex, ey)) > 2:
                d.line([sx, sy, ex, ey], fill=color + (255,), width=lw)
                if clean:
                    d.ellipse([ex - lw * 2, ey - lw * 2, ex + lw * 2, ey + lw * 2], fill=color + (255,))
            elif not clean:
                d.line([sx, sy, ex, ey], fill=color + (120,), width=lw)
        if row["generated"]:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255), outline=color + (255,), width=w + 1)
            label = row["id"]
            f = _font(int(r * (1.0 if len(label) <= 2 else 0.75)))
            d.text((cx, cy), label, fill=color + (255,), font=f, anchor="mm")
        else:  # existing balloon on the drawing: ring it, never cover it
            rr = r + lw * 2 + 2
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=color + (255,), width=w + 1)
            if row["id"] != str(row["balloon"]):  # duplicate number -> show our unique id
                f = _font(int(r * 0.7))
                d.text((cx + rr, cy - rr), row["id"], fill=color + (255,), font=f, anchor="lb")
    return out


def crop(img: Image.Image, row: dict, pad: float = 1.2) -> Image.Image:
    boxes = [row["loc"]] if row.get("loc") else []
    if row.get("balloon_xy"):
        cx, cy, r = row["balloon_xy"]
        boxes.append((cx - r, cy - r, cx + r, cy + r))
    if not boxes:
        return img.copy()
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    pw = max(img.width * 0.07, (x1 - x0) * pad * 0.5)
    ph = max(img.height * 0.08, (y1 - y0) * pad * 0.5)
    return img.crop((max(0, x0 - pw), max(0, y0 - ph), min(img.width, x1 + pw), min(img.height, y1 + ph)))

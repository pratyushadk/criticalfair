"""Balloon placement and rendering. Always draws on a copy - the original drawing stays intact."""
import math

import cv2
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


def place_balloons(img: Image.Image, rows: list[dict], perception=None) -> None:
    """Assign balloon_xy to rows without a drawing balloon.
    Hard rules: never overlap any text on the drawing, another balloon, or the image edge.
    Soft rules: prefer white space and short leaders."""
    gray = np.array(img.convert("L"))
    ink = (gray < 160).astype(np.float32)
    integral = np.pad(ink.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    H, W = gray.shape
    r = balloon_radius(img)
    margin = max(4, r // 3)

    def ink_in(cx, cy, rad):
        x0, y0, x1, y1 = int(cx - rad), int(cy - rad), int(cx + rad), int(cy + rad)
        if x0 < 3 or y0 < 3 or x1 >= W - 3 or y1 >= H - 3:
            return None
        s = integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0]
        return s / ((x1 - x0) * (y1 - y0))

    text_boxes = [t.box for t in perception.tokens] if perception is not None else []
    text_boxes += [row["loc"] for row in rows if row.get("loc")]
    if perception is not None:
        text_boxes += [c.box for c in perception.circles]
    # character-sized ink blobs = text the OCR may have missed (stacked tolerances, small digits, symbols)
    n, _, stats, _ = cv2.connectedComponentsWithStats((gray < 160).astype(np.uint8), connectivity=8)
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if 0.2 * r <= h <= 2.4 * r and w <= 2.6 * r and area >= 4:
            text_boxes.append((x, y, x + w, y + h))

    def hits_text(cx, cy):
        rr = r + margin
        return any(b[0] - rr < cx < b[2] + rr and b[1] - rr < cy < b[3] + rr for b in text_boxes)

    occupied = [row["balloon_xy"] for row in rows if row.get("balloon_xy")]
    for row in rows:
        if row.get("balloon_xy") or not row.get("loc"):
            continue
        x0, y0, x1, y1 = row["loc"]
        cx0, cy0 = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = (x1 - x0) / 2, (y1 - y0) / 2
        best, best_score = None, 1e18
        for dist in (r * 1.5, r * 2.3, r * 3.2, r * 4.4, r * 6.0, r * 8.0):
            for k in range(24):
                a = k * math.pi / 12
                dx, dy = math.cos(a), math.sin(a)
                t = min(hw / abs(dx) if abs(dx) > 1e-6 else 1e9, hh / abs(dy) if abs(dy) > 1e-6 else 1e9)
                cx, cy = cx0 + dx * (t + dist), cy0 + dy * (t + dist)
                if any(math.dist((cx, cy), (ox, oy)) < r + orr + margin * 2 for ox, oy, orr in occupied):
                    continue
                if hits_text(cx, cy):
                    continue
                density = ink_in(cx, cy, r + margin)
                if density is None or density > 0.035:  # must sit in (nearly) clean white space
                    continue
                score = density * 60 + dist / r * 0.8 + (0.4 if abs(dy) > 0.9 else 0)
                if score < best_score:
                    best, best_score = (int(cx), int(cy), r), score
            if best is not None and best_score < 1.5 + dist / r * 0.8:
                break  # found clean white space at this distance - do not go further out
        if best is None:  # everything crowded: fall back to least-bad spot ignoring text
            for dist in (r * 2.5, r * 4, r * 6):
                for k in range(24):
                    a = k * math.pi / 12
                    cx, cy = cx0 + math.cos(a) * (hw + dist), cy0 + math.sin(a) * (hh + dist)
                    density = ink_in(cx, cy, r)
                    if density is not None and not any(math.dist((cx, cy), (o[0], o[1])) < r + o[2] + 4 for o in occupied):
                        score = density * 60 + dist / r
                        if score < best_score:
                            best, best_score = (int(cx), int(cy), r), score
            row["flags"] = row.get("flags", []) + ["Crowded area - check balloon placement"]
        row["balloon_xy"] = best or (int(max(r, x0 - r * 2)), int(max(r, y0 - r * 2)), r)
        occupied.append(row["balloon_xy"])


def _leader_end(cx, cy, box, gap=5):
    """Nearest point on the box expanded by `gap`, so the leader stops just short of the text."""
    x0, y0, x1, y1 = box[0] - gap, box[1] - gap, box[2] + gap, box[3] + gap
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
                    d.ellipse([ex - lw * 1.5, ey - lw * 1.5, ex + lw * 1.5, ey + lw * 1.5], fill=color + (255,))
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
            if row["id"] != str(row["balloon"]):  # duplicate number -> show our unique id on a white tag
                f = _font(int(r * 0.7))
                tb = d.textbbox((cx + rr, cy - rr), row["id"], font=f, anchor="lb")
                d.rounded_rectangle([tb[0] - 3, tb[1] - 2, tb[2] + 3, tb[3] + 2], radius=4,
                                    fill=(255, 255, 255, 255), outline=color + (255,), width=1)
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


def live_view(img: Image.Image, p, stage: int, items: list, width: int = 1100) -> Image.Image:
    """Analysis-screen canvas. stage 1: text found, 2: balloons found, 3: characteristics streaming in."""
    scale = min(1.0, width / img.width)
    out = img.convert("RGB").resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(out, "RGBA")
    S = lambda b: [v * scale for v in b]
    used = {t for toks, _, _ in items for t in toks}
    if stage >= 1:
        for t in p.tokens:
            if t.id not in used:
                d.rectangle(S(t.box), outline=(14, 165, 233, 200), fill=(14, 165, 233, 35), width=1)
    if stage >= 2:
        for c in p.circles:
            b = S(c.box)
            d.ellipse([b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3], outline=(147, 51, 234, 255), width=3)
    if stage >= 3:
        f = _font(max(11, int(15 * scale / 0.6)) if scale < 1 else 15)
        for n, (toks, _, _) in enumerate(items, 1):
            boxes = [p.token(t).box for t in toks if p.token(t)]
            if not boxes:
                continue
            b = S((min(x[0] for x in boxes), min(x[1] for x in boxes), max(x[2] for x in boxes), max(x[3] for x in boxes)))
            d.rectangle([b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3], outline=(22, 163, 74, 255), fill=(22, 163, 74, 60), width=2)
            tag = str(n)
            tb = d.textbbox((b[0] - 3, b[1] - 5), tag, font=f, anchor="lb")
            d.rounded_rectangle([tb[0] - 4, tb[1] - 2, tb[2] + 4, tb[3] + 2], radius=5, fill=(22, 163, 74, 255))
            d.text((b[0] - 3, b[1] - 5), tag, font=f, fill=(255, 255, 255, 255), anchor="lb")
    return out


def a3_pdf(img: Image.Image, title: str = "", dpi: int = 200) -> bytes:
    """Ballooned drawing on an A3 landscape page (420 x 297 mm) with a thin footer."""
    import io
    W, H = int(420 / 25.4 * dpi), int(297 / 25.4 * dpi)
    page = Image.new("RGB", (W, H), "white")
    m, footer = int(10 / 25.4 * dpi), int(9 / 25.4 * dpi)
    box_w, box_h = W - 2 * m, H - 2 * m - footer
    sc = min(box_w / img.width, box_h / img.height)
    im = img.convert("RGB").resize((int(img.width * sc), int(img.height * sc)), Image.LANCZOS)
    page.paste(im, (m + (box_w - im.width) // 2, m + (box_h - im.height) // 2))
    d = ImageDraw.Draw(page)
    d.line([m, H - m - footer + 8, W - m, H - m - footer + 8], fill=(180, 180, 180), width=2)
    f = _font(int(dpi * 0.12))
    d.text((m, H - m - footer // 2 + 6), title, fill=(60, 60, 60), font=f, anchor="lm")
    d.text((W - m, H - m - footer // 2 + 6), "Ballooned by Project Critical Fair · A3", fill=(120, 120, 120),
           font=f, anchor="rm")
    buf = io.BytesIO()
    page.save(buf, format="PDF", resolution=dpi)
    return buf.getvalue()

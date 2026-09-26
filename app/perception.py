"""Deterministic, local perception: exact text boxes, balloon circles and drawing zones.

Claude never has to guess pixel coordinates - it references the IDs produced here.
"""
import re
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image

try:
    from ocrmac import ocrmac  # Apple Vision OCR (macOS)
except ImportError:  # pragma: no cover
    ocrmac = None


@dataclass
class Token:
    id: str
    text: str
    box: tuple  # x0, y0, x1, y1 in pixels of the full-res image
    conf: float = 1.0


@dataclass
class Circle:
    id: str
    cx: int
    cy: int
    r: int
    digits: str = ""  # number read inside the circle ("" if unreadable)

    @property
    def box(self):
        return (self.cx - self.r, self.cy - self.r, self.cx + self.r, self.cy + self.r)


@dataclass
class Perception:
    width: int
    height: int
    tokens: list[Token] = field(default_factory=list)
    circles: list[Circle] = field(default_factory=list)
    col_labels: list[tuple[str, float]] = field(default_factory=list)  # (label, x centre)
    row_labels: list[tuple[str, float]] = field(default_factory=list)  # (label, y centre)
    text_source: str = "ocr"

    def token(self, tid):
        return next((t for t in self.tokens if t.id == tid), None)

    def circle(self, cid):
        return next((c for c in self.circles if c.id == cid), None)

    @property
    def has_balloons(self) -> bool:
        return sum(1 for c in self.circles if c.digits) >= 2

    def zone(self, x: float, y: float) -> str:
        """Drawing zone like 'B4' from the border grid (virtual 8x4 grid when the border has none)."""
        if len({c[0] for c in self.col_labels}) >= 2 and len({r[0] for r in self.row_labels}) >= 2:
            col = min(self.col_labels, key=lambda c: abs(c[1] - x))[0]
            row = min(self.row_labels, key=lambda r: abs(r[1] - y))[0]
        else:
            col = str(min(8, int(x / self.width * 8)) + 1)
            row = "ABCD"[min(3, int(y / self.height * 4))]
        return f"{row}{col}"


# ---------------- OCR ----------------
def _ocr(img: Image.Image, level: str) -> list[tuple[str, float, tuple]]:
    """Returns (text, conf, (x0,y0,x1,y1) px) with top-left origin."""
    W, H = img.size
    out = []
    for text, conf, (x, y, w, h) in ocrmac.OCR(img, recognition_level=level,
                                                language_preference=["en-US"]).recognize():
        out.append((text.strip(), float(conf), (x * W, (1 - y - h) * H, (x + w) * W, (1 - y) * H)))
    return out


def _iou(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _merge(found: list, new: list):
    for text, conf, box in new:
        if not text:
            continue
        dup = next((i for i, f in enumerate(found) if _iou(f[2], box) > 0.3), None)
        if dup is None:
            found.append((text, conf, box))
        elif conf > found[dup][1] or (conf == found[dup][1] and len(text) > len(found[dup][0])):
            found[dup] = (text, conf, box)


def ocr_tokens(img: Image.Image) -> list[tuple]:
    if ocrmac is None:
        return []
    W, H = img.size
    found: list = []
    _merge(found, _ocr(img, "accurate"))
    if max(W, H) < 2600:  # small raster: an upscaled pass catches stacked tolerances
        s = 2
        big = img.resize((W * s, H * s), Image.LANCZOS)
        _merge(found, [(t, c, tuple(v / s for v in b)) for t, c, b in _ocr(big, "accurate")])
    _merge(found, _ocr(img, "fast"))
    # vertical text: rotate clockwise, OCR, map boxes back
    rot = img.rotate(-90, expand=True)
    back = []
    for t, c, (x0, y0, x1, y1) in _ocr(rot, "accurate"):
        box = (y0, H - x1, y1, H - x0)
        if (box[3] - box[1]) > (box[2] - box[0]) * 1.5:  # keep only genuinely vertical text
            back.append((t, c, box))
    _merge(found, back)
    return found


def pdf_tokens(page, scale: float) -> list[tuple]:
    """Exact text spans from a vector PDF page, scaled to rendered pixels."""
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = " ".join(s["text"] for s in line["spans"]).strip()
            if text:
                x0, y0, x1, y1 = line["bbox"]
                out.append((text, 1.0, (x0 * scale, y0 * scale, x1 * scale, y1 * scale)))
    return out


# ---------------- balloons ----------------
def _ring_score(ink, cx, cy, r) -> float:
    """Fraction of the circumference that is inked (balloons are complete outlines)."""
    H, W = ink.shape
    hits = 0
    angles = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for a in angles:
        ok = False
        for dr in (-2, -1, 0, 1, 2):
            x, y = int(cx + (r + dr) * np.cos(a)), int(cy + (r + dr) * np.sin(a))
            if 0 <= x < W and 0 <= y < H and ink[y, x]:
                ok = True
                break
        hits += ok
    return hits / len(angles)


def _read_number(img: Image.Image, cx, cy, r) -> str:
    """OCR the number inside a circle with everything outside 0.78r masked white."""
    if ocrmac is None:
        return ""
    k = int(r * 0.8)
    crop = img.crop((cx - k, cy - k, cx + k, cy + k)).convert("L")
    mask = Image.new("L", crop.size, 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).ellipse([k - r * 0.78, k - r * 0.78, k + r * 0.78, k + r * 0.78], fill=255)
    white = Image.new("L", crop.size, 255)
    crop = Image.composite(crop, white, mask)
    pad = Image.new("L", (crop.width * 3, crop.height * 3), 255)
    pad.paste(crop, (crop.width, crop.height))
    pad = pad.resize((pad.width * 3, pad.height * 3), Image.LANCZOS).convert("RGB")
    best = ""
    for level in ("accurate", "fast"):
        for t, conf, _ in _ocr(pad, level):
            t = t.replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1").replace("S", "5")
            if re.fullmatch(r"\d{1,3}", t.strip()) and conf >= 0.3:
                best = t.strip()
                break
        if best:
            break
    return best


def detect_circles(img: Image.Image) -> list[Circle]:
    gray = np.array(img.convert("L"))
    H, W = gray.shape
    ink = gray < 140
    raw = cv2.HoughCircles(cv2.medianBlur(gray, 3), cv2.HOUGH_GRADIENT, dp=1.2, minDist=W * 0.015,
                           param1=120, param2=38, minRadius=max(8, int(W * 0.008)), maxRadius=int(W * 0.024))
    circles = []
    for cx, cy, r in ([] if raw is None else np.round(raw[0]).astype(int)):
        k = max(2, int(r * 0.6))
        inner = ink[max(0, cy - k):cy + k, max(0, cx - k):cx + k]
        fill = float(inner.mean()) if inner.size else 0
        if not 0.02 < fill < 0.40 or _ring_score(ink, cx, cy, r) < 0.8:
            continue  # empty hole, hatching or partial arc -> not a balloon
        circles.append(Circle("", int(cx), int(cy), int(r), _read_number(img, cx, cy, r)))
    circles.sort(key=lambda c: (c.cy, c.cx))
    for i, c in enumerate(circles, 1):
        c.id = f"C{i}"
    return circles


# ---------------- zones ----------------
def zone_labels(img: Image.Image, tokens: list) -> tuple[list, list]:
    W, H = img.size
    cols, rows = [], []
    strips = {"top": (0, 0, W, int(H * 0.05)), "bottom": (0, int(H * 0.95), W, H),
              "left": (0, 0, int(W * 0.035), H), "right": (int(W * 0.965), 0, W, H)}
    cand = [(t, b) for t, _, b in tokens]
    if ocrmac is not None:
        for name, (x0, y0, x1, y1) in strips.items():
            crop = img.crop((x0, y0, x1, y1))
            s = 3
            crop = crop.resize((crop.width * s, crop.height * s), Image.LANCZOS)
            for t, _, b in _ocr(crop, "accurate"):
                cand.append((t, (x0 + b[0] / s, y0 + b[1] / s, x0 + b[2] / s, y0 + b[3] / s)))
    for t, (x0, y0, x1, y1) in cand:
        t = t.strip()
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if re.fullmatch(r"\d{1,2}", t) and (cy < H * 0.05 or cy > H * 0.95):
            cols.append((t, cx))
        elif re.fullmatch(r"[A-HJ-N]", t) and (cx < W * 0.035 or cx > W * 0.965):
            rows.append((t, cy))

    def dedupe(labels):
        out = []
        for lab, pos in sorted(labels, key=lambda l: l[1]):
            if not out or abs(out[-1][1] - pos) > 15:
                out.append((lab, pos))
        return out
    return dedupe(cols), dedupe(rows)


def read_text(img: Image.Image, pdf_text: list | None = None) -> tuple[list, str]:
    raw = list(pdf_text or [])
    if len(raw) >= 5:
        return raw, "pdf"
    return ocr_tokens(img), "ocr"


def assemble(img: Image.Image, raw: list, source: str, circles: list[Circle]) -> Perception:
    W, H = img.size
    cols, rows = zone_labels(img, raw)
    tokens = []
    for text, conf, box in raw:  # drop balloon numbers and border zone labels
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        if any(c.digits and (cx - c.cx) ** 2 + (cy - c.cy) ** 2 < c.r ** 2 for c in circles):
            continue
        if (cy < H * 0.05 or cy > H * 0.95 or cx < W * 0.035 or cx > W * 0.965) and len(text) <= 2:
            continue
        tokens.append((text, conf, box))
    tokens.sort(key=lambda t: (round(t[2][1] / (H * 0.03)), t[2][0]))
    toks = [Token(f"T{i}", t, tuple(int(v) for v in b), c) for i, (t, c, b) in enumerate(tokens, 1)]
    return Perception(W, H, toks, circles, cols, rows, source)


def perceive(img: Image.Image, pdf_text: list | None = None) -> Perception:
    raw, source = read_text(img, pdf_text)
    return assemble(img, raw, source, detect_circles(img))

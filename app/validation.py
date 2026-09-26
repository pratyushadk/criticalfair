"""Deterministic checks and row building on top of perception + Claude output."""
import math
import re
from collections import Counter, defaultdict

from .perception import Perception
from .schemas import Characteristic, Extraction

CONFIDENCE_THRESHOLD = 0.8
DIM_PATTERN = re.compile(r"(±|\+/-|Ø|ø|⌀|\bR\d|\bM\d+x|\d+\.\d+|\d+°|\bRa\s?\d)")

NOTE_WORDS = re.compile(r"UNLESS|TOLERANCE|ANGLES|DIMENSIONS|MATERIAL|SCALE|DATE|DRAWN|CHECKED|X\.X", re.I)

TOOL_RULES = [  # fallback when Claude gives no tool
    (lambda c: "thread" in c.type.lower(), "Thread Gauge (Go/No-Go)"),
    (lambda c: "finish" in c.type.lower(), "Profilometer"),
    (lambda c: c.type.lower() in ("gd&t", "basic"), "CMM"),
    (lambda c: c.type.lower() == "note", "Visual"),
    (lambda c: "angle" in c.type.lower(), "Protractor / CMM"),
    (lambda c: c.upper is not None and c.lower is not None and (c.upper - c.lower) <= 0.04, "Micrometer"),
    (lambda c: True, "Caliper"),
]


def _union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def _center(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0


def requirement_text(name: str, notation: str, unit: str) -> str:
    unit = unit if unit and unit not in notation and unit.lower() not in ("deg", "°") else ""
    return f"{name}: {notation}{' ' + unit if unit else ''}"


def _value_flags(c: Characteristic, general_tol: str) -> list[str]:
    flags = []
    t = c.type.lower()
    if t in ("linear", "diameter", "radius", "angle", "chamfer"):
        if c.nominal is None:
            flags.append("Nominal value missing")
        if (c.upper is None or c.lower is None) and not general_tol:
            flags.append("No tolerance and no general tolerance found")
    if c.upper is not None and c.lower is not None and c.upper < c.lower:
        flags.append("Upper tolerance below lower tolerance")
    if t == "gd&t" and not re.search(r"\d", c.gdt or c.notation):
        flags.append("GD&T tolerance value missing")
    return flags


def build(ext: Extraction, p: Perception) -> tuple[list[dict], list[dict]]:
    """Returns (rows, issues). issues = drawing-level problems [{kind, text, token?}]."""
    ballooned = p.has_balloons
    general_tol = ext.drawing.general_tolerance
    rows, issues = [], []

    # --- per characteristic: location, zone, flags ---
    for i, c in enumerate(ext.characteristics):
        flags = []
        valid = [p.token(t) for t in c.tokens if p.token(t)]
        if len(valid) < len(c.tokens):
            flags.append("Some referenced text tokens do not exist")
        if valid:
            loc, exact = _union([t.box for t in valid]), True
        elif len(c.box) == 4:
            x0, y0, x1, y1 = c.box
            loc = (x0 * p.width / 1000, y0 * p.height / 1000, x1 * p.width / 1000, y1 * p.height / 1000)
            exact = False
            flags.append("Approximate location (no readable text) - confirm on drawing")
        else:
            loc, exact = None, False
            flags.append("Location unknown")
        circle = p.circle(c.circle) if c.circle else None
        if c.circle and not circle:
            flags.append(f"Referenced balloon {c.circle} does not exist")
        if ballooned and not circle:
            flags.append("No balloon on drawing - new balloon added")
        if circle and loc:
            d = math.dist((circle.cx, circle.cy), _center(loc))
            if d > 0.35 * max(p.width, p.height):
                flags.append("Balloon is far from its requirement - verify leader association")
        if c.confidence < CONFIDENCE_THRESHOLD:
            flags.append(f"Low confidence ({c.confidence:.0%})")
        if c.issue:
            flags.append(c.issue)
        flags += _value_flags(c, general_tol)
        tool = c.tool or next(t for rule, t in TOOL_RULES if rule(c))
        rows.append({
            "key": i, "balloon": c.balloon if circle else 0, "circle": circle.id if circle else "",
            "status": "Pending", "name": c.name, "notation": c.notation, "unit": c.unit, "type": c.type,
            "nominal": c.nominal, "upper": c.upper, "lower": c.lower, "qty": c.qty, "gdt": c.gdt,
            "designator": c.designator, "tool": tool, "confidence": c.confidence,
            "loc": tuple(int(v) for v in loc) if loc else None, "exact": exact,
            "balloon_xy": (circle.cx, circle.cy, circle.r) if circle else None, "generated": circle is None,
            "zone": p.zone(*_center(loc)) if loc else "", "flags": flags, "tokens": [t.id for t in valid],
            "_ai": c.model_dump(),
        })

    # --- duplicates: same circle used twice / same text used twice ---
    by_circle = defaultdict(list)
    for r in rows:
        if r["circle"]:
            by_circle[r["circle"]].append(r)
    for cid, rs in by_circle.items():
        if len(rs) > 1:
            for r in rs:
                r["flags"].append(f"One balloon ({cid}) linked to {len(rs)} characteristics")
    for a in rows:
        for b in rows:
            if a["key"] < b["key"] and a["loc"] and b["loc"] and (
                    set(a["tokens"]) & set(b["tokens"]) or _iou(a["loc"], b["loc"]) > 0.6):
                b["flags"].append(f"Possible duplicate of '{a['name']}'")

    # --- unique numbering ---
    if ballooned:
        counts = Counter(r["balloon"] for r in rows if r["balloon"])
        seen = Counter()
        for r in rows:
            n = r["balloon"]
            if n and counts[n] > 1:
                seen[n] += 1
                r["id"] = f"{n}.{seen[n]}"
                r["flags"].append(f"Balloon number {n} appears {counts[n]} times on the drawing")
            elif n:
                r["id"] = str(n)
        nxt = max([r["balloon"] for r in rows if r["balloon"]] or [0]) + 1
        for r in rows:
            if "id" not in r:
                r["id"] = str(nxt)
                nxt += 1
        nums = sorted(counts)
        if nums:
            gaps = sorted(set(range(1, nums[-1] + 1)) - set(nums))
            if gaps:
                issues.append({"kind": "missing", "text": f"Balloon numbers not found on drawing: {', '.join(map(str, gaps))}"})
    else:
        for n, r in enumerate(rows, 1):
            r["id"] = str(n)

    # --- balloons detected but never associated ---
    used = {r["circle"] for r in rows} | set(ext.ignored_circles)
    for c in p.circles:
        if c.id not in used and c.digits:
            issues.append({"kind": "missing", "text": f"Balloon {c.digits} ({p.zone(c.cx, c.cy)}) detected but not linked to any requirement"})

    # --- dimension-like text that no characteristic uses ---
    used_tokens = {t for r in rows for t in r["tokens"]}
    tb_y = p.height * 0.78
    for t in p.tokens:
        if t.id in used_tokens or not DIM_PATTERN.search(t.text) or NOTE_WORDS.search(t.text):
            continue
        if t.box[1] > tb_y and t.box[0] > p.width * 0.6:  # title-block area
            continue
        issues.append({"kind": "unused", "text": f"'{t.text}' ({p.zone(*_center(t.box))}) is not in the list - missed characteristic?",
                       "token": t.id})

    for w in ext.warnings:
        issues.append({"kind": "ai", "text": w})
    for r in rows:
        r["flagged"] = bool(r["flags"])
    return rows, issues


def row_from_token(p: Perception, token_id: str, rows: list[dict]) -> dict:
    """Manual 'add as characteristic' from an unused token."""
    t = p.token(token_id)
    nxt = max([int(float(r["id"])) for r in rows] or [0]) + 1
    return {"key": 10_000 + nxt, "id": str(nxt), "balloon": 0, "circle": "", "status": "Pending",
            "name": "Added characteristic", "notation": t.text, "unit": "", "type": "Linear", "nominal": None,
            "upper": None, "lower": None, "qty": 1, "gdt": "", "designator": "", "tool": "Caliper",
            "confidence": 0.0, "loc": t.box, "exact": True, "balloon_xy": None, "generated": True,
            "zone": p.zone(*_center(t.box)), "flags": ["Added manually - complete the details"], "tokens": [t.id],
            "flagged": True, "_ai": {}}

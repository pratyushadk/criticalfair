"""Fill templates/AS9102_template.xlsx (the team's "Final Template") - values only, layout/formulas/formatting kept."""
import io
import json
import re
from copy import copy
from datetime import date, datetime, timezone
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "templates" / "AS9102_template.xlsx"

PART_SHEET, CHAR_SHEET, SUMMARY_SHEET = "Part Info, Drawing & GDT Ref", "Characteristics", "Summary"
PART_CELLS = {"part_number": "B4", "part_name": "D4", "revision": "B5", "drawing_number": "D5",
              "drawing_revision": "B6", "additional_changes": "D6", "fai_report_number": "B7", "serial_number": "D7",
              "quantity": "B8", "process_ref": "D8", "organization": "B9", "supplier_code": "D9", "customer": "B10",
              "po_number": "D10", "material": "B11", "material_cert": "D11", "fai_type": "B12", "baseline_part": "D12",
              "partial_reason": "B13", "inspector": "D13", "inspection_date": "B14", "equipment": "D14",
              "calibration_due": "B15", "drawing_file": "B19"}
FIRST_ROW, TEMPLATE_LAST_ROW = 2, 31
REF_FIRST, REF_LAST = 48, 92          # GD&T reference list that feeds the Characteristics dropdown
IMAGE_AREA = ("A21", 21, 44, "ABCDEFGH")  # merged placeholder for the ballooned drawing

# Dimension types the template's reference list lacks - appended (marked) so every value stays valid in the dropdown.
ADDED_TYPES = [
    ("Linear Dimension", "Dimension Type (added by Critical Fair)", "No", "Toleranced straight-line size or distance."),
    ("Basic Dimension", "Dimension Type (added by Critical Fair)", "No", "Theoretically exact value (boxed); verified through the related geometric tolerance."),
    ("Angular Dimension", "Dimension Type (added by Critical Fair)", "No", "Toleranced angle between features."),
    ("Chamfer", "Dimension Type (added by Critical Fair)", "No", "Edge chamfer size / angle."),
    ("Thread", "Dimension Type (added by Critical Fair)", "No", "Thread callout; verified with Go/No-Go gauges."),
    ("Surface Finish", "Dimension Type (added by Critical Fair)", "No", "Surface roughness requirement (e.g. Ra max)."),
    ("Note / Visual Requirement", "Dimension Type (added by Critical Fair)", "No", "Drawing note verified by visual or attribute inspection."),
]

GDT_MAP = [  # keyword in GD&T text / type -> template reference name
    ("position", "True Position (Position Tolerance)"), ("⌖", "True Position (Position Tolerance)"),
    ("flatness", "Flatness"), ("⏥", "Flatness"), ("perpendicular", "Perpendicularity"), ("⟂", "Perpendicularity"),
    ("parallel", "Parallelism"), ("∥", "Parallelism"), ("angularity", "Angularity"), ("concentric", "Concentricity"),
    ("◎", "Concentricity"), ("cylindricity", "Cylindricity"), ("⌭", "Cylindricity"), ("circularity", "Circularity (Roundness)"),
    ("roundness", "Circularity (Roundness)"), ("profile of a surface", "Profile of a Surface"), ("⌓", "Profile of a Surface"),
    ("profile of a line", "Profile of a Line"), ("⌒", "Profile of a Line"), ("total runout", "Total Runout"),
    ("runout", "Runout (Circular Runout)"), ("straightness", "Straightness"), ("symmetry", "Symmetry"),
]


def dimension_type(r: dict) -> str:
    t = (r.get("type") or "").lower()
    text = f"{r.get('gdt', '')} {r.get('name', '')} {r.get('notation', '')}".lower()
    if t == "gd&t" or r.get("gdt"):
        for key, name in GDT_MAP:
            if key in text:
                return name
        return "Feature Control Frame"
    notation = r.get("notation", "")
    if t == "basic":
        return "Basic Dimension"
    if "thread" in t or re.search(r"\bM\d+(\.\d+)?\s*[xX×]", notation):
        return "Thread"
    if "finish" in t or "ra " in notation.lower():
        return "Surface Finish"
    if t == "note":
        return "Note / Visual Requirement"
    if t == "diameter" or "Ø" in notation or "ø" in notation:
        return "Spherical Diameter" if "SØ" in notation else "Diameter"
    if t == "radius" or re.match(r"\s*(\d+X\s*)?S?R\s?\d", notation):
        return "Spherical Radius" if "SR" in notation else "Radius"
    if t == "chamfer":
        return "Chamfer"
    if t == "angle" or "°" in notation:
        return "Angular Dimension"
    return "Linear Dimension"


def _first_number(text: str):
    text = re.sub(r"\b[A-Z]\b", " ", text)  # drop datum letters
    m = re.search(r"(\d*\.\d+|\d+)", text)
    return float(m.group(1)) if m else None


def limits(r: dict) -> tuple:
    """(nominal, upper(+), lower(-) as positive magnitude, comment) matching the template's PASS/FAIL formula."""
    dtype = dimension_type(r)
    if dtype in ("Thread", "Note / Visual Requirement"):
        return None, None, None, "Attribute check - record PASS/FAIL here"
    if dtype == "Basic Dimension":
        return r.get("nominal"), None, None, "Basic dimension - verified through the related GD&T"
    if r.get("type", "").lower() == "gd&t" or r.get("gdt"):
        tol = _first_number(re.sub(r"^[^\d]*", "", r.get("gdt") or r.get("notation", ""))) \
            if (r.get("gdt") or r.get("notation")) else None
        return 0.0, tol, 0.0, "Enter measured deviation (0 = perfect)"
    if dtype == "Surface Finish":
        v = r.get("nominal") or _first_number(r.get("notation", ""))
        return 0.0, v, 0.0, "Enter measured Ra"
    up, lo = r.get("upper"), r.get("lower")
    note = "" if up is not None and lo is not None else "No tolerance on drawing - apply general tolerance"
    return r.get("nominal"), up, abs(lo) if lo is not None else None, note


def _set(ws, ref, value):
    for rng in ws.merged_cells.ranges:
        if ref in rng:
            ref = rng.start_cell.coordinate
            break
    ws[ref] = value


def _copy_style(ws, src_row, dst_row, cols):
    for col in cols:
        s, d = ws[f"{col}{src_row}"], ws[f"{col}{dst_row}"]
        if s.has_style:
            d.font, d.border, d.fill = copy(s.font), copy(s.border), copy(s.fill)
            d.alignment, d.number_format, d.protection = copy(s.alignment), s.number_format, copy(s.protection)


def _num(r):
    try:
        return float(r["id"])
    except ValueError:
        return 1e9


def exported_rows(rows):
    return sorted((r for r in rows if r["status"] in ("Accepted", "Corrected")), key=_num)


def requirement(r: dict) -> str:
    notation, name = r["notation"].strip(), r["name"].strip()
    if (r.get("type") or "").lower() == "note" and len(notation) > 25:  # long note: the text itself is the requirement
        return notation[0].upper() + notation[1:].lower() if notation.isupper() else notation
    qty = f" ({r['qty']}X)" if (r.get("qty") or 1) > 1 and f"{r['qty']}X" not in r["notation"].upper() else ""
    return f"{r['name']}: {r['notation']}{qty}"


def build_workbook(rows: list[dict], drawing, info: dict, balloon_png: bytes | None,
                   template: bytes | None = None, model: str = "") -> bytes:
    wb = load_workbook(io.BytesIO(template) if template else DEFAULT_TEMPLATE)
    part, chars, summ = wb[PART_SHEET], wb[CHAR_SHEET], wb[SUMMARY_SHEET]
    out_rows = exported_rows(rows)

    # ---- Part Info (Form 1 style) ----
    tools = sorted({r["tool"] for r in out_rows if r.get("tool")})
    values = dict(info)
    values.setdefault("inspection_date", date.today().strftime("%d-%b-%Y"))
    values.setdefault("fai_type", "Full")
    values["equipment"] = values.get("equipment") or ", ".join(tools)
    values["drawing_file"] = values.get("drawing_file") or f"{Path(drawing.filename).stem}_ballooned.pdf"
    if info.get("material"):
        values["material"] = info["material"] + (f" / {info['material_spec']}" if info.get("material_spec")
                                                 and info["material_spec"] not in info["material"] else "")
    for key, ref in PART_CELLS.items():
        if values.get(key):
            _set(part, ref, values[key])
    if str(part["A16"].value or "").startswith("Example"):
        part["A16"] = None

    # ---- extra dimension types for the dropdown ----
    ref_last = REF_LAST
    existing = {part.cell(r, 1).value for r in range(REF_FIRST, REF_LAST + 1)}
    for name, cat, datum, meaning in ADDED_TYPES:
        if name in existing:
            continue
        ref_last += 1
        for col in "ABCDE":
            _copy_style(part, REF_LAST, ref_last, [col])
        part.cell(ref_last, 1, name), part.cell(ref_last, 2, cat), part.cell(ref_last, 3, datum)
        part.cell(ref_last, 4, meaning)

    # ---- ballooned drawing image in the placeholder ----
    if balloon_png:
        anchor, r0, r1, cols = IMAGE_AREA
        area_w = sum((part.column_dimensions[c].width or 8.43) * 7 + 5 for c in cols)
        area_h = sum((part.row_dimensions[r].height or 15) * 96 / 72 for r in range(r0, r1 + 1))
        img = XLImage(io.BytesIO(balloon_png))
        scale = min((area_w - 10) / img.width, (area_h - 10) / img.height)
        img.width, img.height = int(img.width * scale), int(img.height * scale)
        _set(part, anchor, None)
        part.add_image(img, anchor)

    # ---- Characteristics (Form 3 style) ----
    last = max(TEMPLATE_LAST_ROW, FIRST_ROW + len(out_rows) - 1)
    for n in range(FIRST_ROW, last + 1):  # clear example row + extend formula rows if needed
        if n > TEMPLATE_LAST_ROW:
            _copy_style(chars, TEMPLATE_LAST_ROW, n, "ABCDEFGHIJK")
            chars[f"I{n}"] = f'=IF(OR(E{n}="",H{n}=""),"INCOMPLETE",IF(AND(H{n}>=(E{n}-G{n}),H{n}<=(E{n}+F{n})),"PASS","FAIL"))'
        for col in "ABCDEFGHJK":
            chars[f"{col}{n}"] = None
    for i, r in enumerate(out_rows):
        n = FIRST_ROW + i
        nom, up, lo, note = limits(r)
        ref = f"Zone {r['zone']} / Balloon {r['id']}" if r.get("zone") else f"Balloon {r['id']}"
        comment = "; ".join(x for x in (note, f"Qty {r['qty']}X" if (r.get("qty") or 1) > 1 else "",
                                        f"Designator: {r['designator']}" if r.get("designator") else "",
                                        "Corrected by reviewer" if r["status"] == "Corrected" else "",
                                        "AI result accepted without individual review" if r.get("_skipped") else "") if x)
        chars[f"A{n}"] = int(float(r["id"])) if float(r["id"]).is_integer() else r["id"]
        chars[f"B{n}"] = ref
        chars[f"C{n}"] = requirement(r)
        chars[f"D{n}"] = dimension_type(r)
        chars[f"E{n}"], chars[f"F{n}"], chars[f"G{n}"] = nom, up, lo
        chars[f"J{n}"] = r.get("tool") or ""
        chars[f"K{n}"] = comment
        chars[f"C{n}"].alignment = Alignment(wrap_text=True, vertical="top")

    # dropdown (openpyxl drops the template's x14 validation -> re-create it as a standard list validation)
    dv = DataValidation(type="list", formula1=f"='{PART_SHEET}'!$A${REF_FIRST}:$A${ref_last}", allow_blank=True,
                        errorTitle="Invalid entry", error="Please choose a value from the GD&T Reference list.")
    dv.add(f"D{FIRST_ROW}:D{last}")
    chars.add_data_validation(dv)
    if last > TEMPLATE_LAST_ROW:  # extend conditional formatting + summary ranges
        new = ConditionalFormattingList()
        for cf in chars.conditional_formatting:
            rng = str(cf.sqref).replace(f"I{FIRST_ROW}:I{TEMPLATE_LAST_ROW}", f"I{FIRST_ROW}:I{last}")
            for rule in cf.rules:
                new.add(rng, rule)
        chars.conditional_formatting = new
        for row in summ.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    c.value = c.value.replace(f"A{FIRST_ROW}:A{TEMPLATE_LAST_ROW}", f"A{FIRST_ROW}:A{last}") \
                                     .replace(f"I{FIRST_ROW}:I{TEMPLATE_LAST_ROW}", f"I{FIRST_ROW}:I{last}")

    # ---- Traceability (appended sheet) ----
    ts = wb.create_sheet("Traceability")
    thin = Side(style="thin", color="BFBFBF")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta = [("Drawing file", drawing.filename), ("Drawing SHA-256", drawing.sha256), ("Sheet / page", drawing.page + 1),
            ("Image size (px)", f"{drawing.image.width} x {drawing.image.height}"), ("AI model", model),
            ("Exported (UTC)", now),
            ("Statement", "AI-assisted extraction. Every exported characteristic was accepted or corrected by a reviewer.")]
    for i, (k, v) in enumerate(meta, 1):
        ts.cell(i, 1, k).font = Font(bold=True)
        ts.cell(i, 2, str(v))
    hdr = len(meta) + 2
    heads = ["Char #", "Balloon on drawing", "Zone", "Review status", "In report", "Characteristic (final)",
             "Notation (AI)", "Feature (AI)", "Confidence", "Flags", "Edited fields", "Location px (x0,y0,x1,y1)",
             "Location exact?", "Balloon px (cx,cy,r)", "Text tokens", "AI raw"]
    fill = PatternFill("solid", fgColor="1F3864")
    for j, h in enumerate(heads, 1):
        c = ts.cell(hdr, j, h)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), fill
        c.alignment = Alignment(wrap_text=True, vertical="center")
    exp = {r["key"] for r in out_rows}
    for i, r in enumerate(sorted(rows, key=_num), hdr + 1):
        ai = r.get("_ai") or {}
        vals = [r["id"], r["balloon"] or "generated", r.get("zone", ""),
                r["status"] + (" (not individually reviewed)" if r.get("_skipped") else ""), "yes" if r["key"] in exp else "no",
                requirement(r), ai.get("notation", ""), ai.get("name", ""), r.get("confidence"),
                "; ".join(r["flags"]), ", ".join(r.get("_edited", [])), str(r.get("loc") or ""),
                "yes" if r.get("exact") else "approx", str(r.get("balloon_xy") or ""), " ".join(r.get("tokens", [])),
                json.dumps(ai, ensure_ascii=False)]
        for j, v in enumerate(vals, 1):
            c = ts.cell(i, j, v)
            c.border = Border(bottom=thin)
            c.alignment = Alignment(wrap_text=j in (6, 10), vertical="top")
    for col, w in zip("ABCDEFGHIJKLMNOP", [8, 10, 7, 12, 8, 44, 24, 24, 10, 50, 16, 22, 10, 16, 14, 40]):
        ts.column_dimensions[col].width = w
    ts.freeze_panes = ts.cell(hdr + 1, 1)

    for ws in wb.worksheets:  # print everything on A3 landscape, one page wide
        ws.page_setup.paperSize = ws.PAPERSIZE_A3
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def preview(rows: list[dict]) -> list[dict]:
    """Rows as they will appear on the Characteristics sheet (for the UI)."""
    out = []
    for r in exported_rows(rows):
        nom, up, lo, _ = limits(r)
        out.append({"Char #": r["id"], "Reference Location": f"Zone {r['zone']} / Balloon {r['id']}",
                    "Characteristic Description": requirement(r), "GD&T / Dimension Type": dimension_type(r),
                    "Nominal": nom, "Upper Tol (+)": up, "Lower Tol (−)": lo, "Measurement Equipment": r.get("tool")})
    return out

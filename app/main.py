"""Critical Fair - Streamlit UI.  Run:  streamlit run app/main.py"""
import html
import io
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app import as9102, extractor, overlay, validation  # noqa: E402
from app.drawing import load_drawing  # noqa: E402
from app.perception import assemble, detect_circles, read_text  # noqa: E402

SAMPLES = sorted((ROOT / "samples" / "drawings").glob("*.*"))
STEPS = ["Upload", "Analyse", "Review", "Export"]
ICON = {"Accepted": "✓", "Corrected": "✎", "Rejected": "✕"}
PILL = {"Accepted": ("#DCFCE7", "#166534"), "Corrected": ("#DBEAFE", "#1E40AF"), "Rejected": ("#FEE2E2", "#991B1B"),
        "Needs review": ("#FEF3C7", "#92400E"), "Pending": ("#F3F4F6", "#374151")}
TOOLS = ["Caliper", "Micrometer", "Bore Gauge", "Height Gauge", "CMM", "Profilometer", "Thread Gauge (Go/No-Go)",
         "Pin Gauge", "Radius Gauge", "Protractor / CMM", "Dial Indicator", "Optical Comparator", "Visual"]
DESIGNATORS = ["", "Key", "Critical", "Major", "Minor"]

st.set_page_config(page_title="Critical Fair", page_icon="◎", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
#MainMenu, footer, [data-testid="stSidebarCollapsedControl"] {display:none;}
.block-container {max-width: 1240px; padding-top: 2rem;}
.cf-brand {font-size:1.35rem; font-weight:700; letter-spacing:-.01em;}
.cf-sub {color:#6B7280; font-size:.9rem; margin-top:-.2rem;}
.cf-steps {display:flex; gap:2rem; justify-content:center; margin:1rem 0 1.4rem;}
.cf-step {display:flex; align-items:center; gap:.5rem; color:#9CA3AF; font-weight:500; font-size:.95rem;}
.cf-step b {width:1.7rem; height:1.7rem; border-radius:50%; display:inline-flex; align-items:center; justify-content:center;
  background:#F3F4F6; font-size:.8rem;}
.cf-step.on {color:#111827;} .cf-step.on b {background:#2563EB; color:#fff;}
.cf-step.done {color:#111827;} .cf-step.done b {background:#DCFCE7; color:#166534;}
.cf-h {font-size:1.45rem; font-weight:650; text-align:center; margin-bottom:.15rem;}
.cf-c {text-align:center; color:#6B7280;}
.cf-name {font-size:1.45rem; font-weight:650; letter-spacing:-.01em; margin:.15rem 0 0;}
.cf-notation {font-family: ui-monospace, Menlo, monospace; font-size:1.15rem; background:#F3F4F6; border-radius:8px;
  padding:.35rem .6rem; display:inline-block; margin:.35rem 0;}
.cf-meta {color:#6B7280; font-size:.88rem;}
.cf-pill {display:inline-block; padding:.12rem .6rem; border-radius:999px; font-size:.76rem; font-weight:600;}
.cf-stage {display:flex; align-items:center; gap:.75rem; padding:.55rem .2rem; border-bottom:1px solid #F3F4F6;}
.cf-stage:last-child {border-bottom:none;}
.cf-dot {width:1.5rem; height:1.5rem; border-radius:50%; display:inline-flex; align-items:center; justify-content:center;
  font-size:.75rem; font-weight:700; flex-shrink:0;}
.cf-dot.done {background:#DCFCE7; color:#166534;} .cf-dot.run {background:#2563EB; color:#fff; animation: cfp 1s infinite alternate;}
.cf-dot.wait {background:#F3F4F6; color:#9CA3AF;}
@keyframes cfp {from {opacity:1} to {opacity:.45}}
.cf-stage .t {flex:1; font-weight:500;} .cf-stage .d {color:#6B7280; font-size:.85rem;}
.cf-stage.wait .t {color:#9CA3AF;}
</style>""", unsafe_allow_html=True)

ss = st.session_state
for k, v in {"step": 0, "idx": 0, "nav": 0}.items():
    ss.setdefault(k, v)


# ---------------- helpers ----------------
def go(step: int):
    ss.step = step
    st.rerun()


def restart():
    for k in ("rows", "source", "drawing", "perception", "extraction", "issues"):
        ss.pop(k, None)
    go(0)


def label(r):
    return "Needs review" if r["status"] == "Pending" and r["flagged"] else r["status"]


def pill(r):
    bg, fg = PILL[label(r)]
    return f'<span class="cf-pill" style="background:{bg};color:{fg}">{label(r)}</span>'


def png(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def pdf(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=200)
    return buf.getvalue()


def order(rows):
    """Review order: flagged first, then by characteristic number."""
    return sorted(range(len(rows)), key=lambda i: (not rows[i]["flagged"], float(rows[i]["id"])))


def advance():
    rows = ss.rows
    seq = order(rows)
    pos = seq.index(ss.idx) if ss.idx in seq else -1
    for k in range(1, len(seq) + 1):
        j = seq[(pos + k) % len(seq)]
        if rows[j]["status"] == "Pending":
            ss.idx = j
            break
    ss.nav += 1


def set_status(r, status):
    r["status"] = status
    advance()
    st.rerun()


def stage_html(stages, cur, notes):
    out = []
    for i, name in enumerate(stages):
        cls = "done" if i < cur else "run" if i == cur else "wait"
        dot = "✓" if i < cur else str(i + 1)
        out.append(f'<div class="cf-stage {cls}"><span class="cf-dot {cls}">{dot}</span>'
                   f'<span class="t">{name}</span><span class="d">{html.escape(notes.get(i, ""))}</span></div>')
    return "".join(out)


# ---------------- header ----------------
h1, h2 = st.columns([6, 1], vertical_alignment="center")
h1.markdown('<div class="cf-brand">◎ Critical Fair</div>'
            '<div class="cf-sub">Engineering drawing → ballooned drawing → AS9102 report</div>', unsafe_allow_html=True)
with h2.popover("Settings", icon=":material/tune:"):
    st.caption(f"Model · `{extractor.MODEL}` · effort `{extractor.EFFORT}`" if extractor.has_api_key()
               else "No API key · only previously analysed drawings work")
    validation.CONFIDENCE_THRESHOLD = st.slider("Flag below confidence", 0.5, 1.0, 0.8, 0.05)
    ss.force = st.toggle("Re-analyse (ignore saved result)", value=ss.get("force", False))

st.markdown('<div class="cf-steps">' + "".join(
    f'<div class="cf-step {"on" if i == ss.step else "done" if i < ss.step else ""}">'
    f'<b>{"✓" if i < ss.step else i + 1}</b>{s}</div>' for i, s in enumerate(STEPS)) + '</div>', unsafe_allow_html=True)


# ================= 1. UPLOAD =================
if ss.step == 0:
    _, mid, _ = st.columns([1, 2, 1])
    with mid, st.container(border=True):
        st.markdown('<div class="cf-h">Upload an engineering drawing</div>'
                    '<div class="cf-c">PDF, PNG or JPG · with or without balloons. The original is never modified.</div>',
                    unsafe_allow_html=True)
        up = st.file_uploader("Drawing", type=["pdf", "png", "jpg", "jpeg"], label_visibility="collapsed")
        if up is not None:
            ss.source = (up.name, up.getvalue())
        elif SAMPLES:
            pick = st.pills("Or try a sample", [s.name for s in SAMPLES], selection_mode="single")
            if pick:
                ss.source = (pick, (ROOT / "samples" / "drawings" / pick).read_bytes())
        if "source" in ss:
            name, data = ss.source
            drawing = load_drawing(name, data)
            st.image(drawing.image, caption=f"{name} · {drawing.image.width}×{drawing.image.height}px", width="stretch")
            ready = extractor.has_api_key() or extractor.cached(drawing.sha256)
            if not ready:
                st.error("Set ANTHROPIC_API_KEY in .env to analyse new drawings.")
            elif st.button("Analyse drawing  →", type="primary", width="stretch"):
                ss.drawing = drawing
                go(1)
            st.caption("Next: Critical Fair finds every characteristic, balloons it, and asks you to confirm anything uncertain.")


# ================= 2. ANALYSE (staged progress) =================
elif ss.step == 1:
    drawing = ss.drawing
    stages = ["Uploading drawing", "Analysing drawing", "Detecting balloons", "Reading characteristics",
              "Validating", "Generating ballooned drawing & Excel"]
    notes = {}
    _, mid, _ = st.columns([1, 2, 1])
    with mid, st.container(border=True):
        st.markdown(f'<div class="cf-h">Analysing {html.escape(drawing.filename)}</div>'
                    '<div class="cf-c">This usually takes 20–60 seconds. You will review everything before export.</div>',
                    unsafe_allow_html=True)
        st.write("")
        bar = st.progress(0.0)
        box = st.empty()
        eta_line = st.empty()
        t0 = time.time()

        def show(cur, frac, eta=None):
            box.markdown(stage_html(stages, cur, notes), unsafe_allow_html=True)
            bar.progress(min(1.0, frac))
            elapsed = time.time() - t0
            eta_line.caption(f"Elapsed {elapsed:.0f}s" + (f" · about {max(1, eta):.0f}s remaining" if eta else ""))

        notes[0] = f"{len(ss.source[1]) / 1024:.0f} KB"
        show(1, 0.05)
        raw, src = read_text(drawing.image, drawing.pdf_text)
        notes[1] = f"{len(raw)} text items ({'vector PDF text' if src == 'pdf' else 'OCR'})"
        show(2, 0.12)
        circles = detect_circles(drawing.image)
        p = assemble(drawing.image, raw, src, circles)
        n_b = sum(1 for c in circles if c.digits)
        notes[2] = f"{len(circles)} balloon candidates" if p.has_balloons else "No balloons - they will be generated"
        est = extractor.estimate_seconds(p)
        exp_n = extractor.expected_count(p)
        cached_hit = None if ss.get("force") else extractor.cached(drawing.sha256)
        show(3, 0.18, est)
        try:
            if cached_hit:
                ext = cached_hit
                notes[3] = f"{len(ext.characteristics)} found · loaded saved analysis"
            else:
                def progress(found, elapsed):
                    notes[3] = f"{found} found so far"
                    frac = 0.18 + 0.7 * min(0.97, max(elapsed / est, found / max(exp_n, 1)))
                    show(3, frac, max(3, est - elapsed))
                sha = drawing.sha256 if not ss.get("force") else drawing.sha256
                if ss.get("force"):
                    for d in extractor.CACHE_DIRS:
                        (d / f"{sha}.json").unlink(missing_ok=True)
                ext = extractor.extract(drawing.image, p, sha, on_progress=progress)
                notes[3] = f"{len(ext.characteristics)} characteristics in {time.time() - t0:.0f}s"
        except extractor.ExtractionError as e:
            st.error(str(e))
            if st.button("← Back"):
                go(0)
            st.stop()
        show(4, 0.9)
        rows, issues = validation.build(ext, p)
        overlay.place_balloons(drawing.image, rows)
        flagged = sum(r["flagged"] for r in rows)
        notes[4] = f"{flagged} to review · {len(issues)} drawing checks"
        show(5, 0.95)
        info = ext.drawing
        ss.draft_xlsx = as9102.build_workbook(rows, drawing, info.model_dump(), None, model=extractor.MODEL)
        notes[5] = "Ready"
        show(6, 1.0)
        ss.perception, ss.extraction, ss.rows, ss.issues = p, ext, rows, issues
        ss.analysed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        ss.idx = order(rows)[0] if rows else 0
        ss.nav += 1
        time.sleep(0.6)
        go(2)


# ================= 3. REVIEW =================
elif ss.step == 2:
    rows, drawing, p = ss.rows, ss.drawing, ss.perception
    if not rows:
        st.warning("No characteristics were found on this drawing.")
        if st.button("← Start over"):
            restart()
        st.stop()
    r = rows[ss.idx]
    done = sum(x["status"] != "Pending" for x in rows)
    flagged_left = sum(1 for x in rows if x["status"] == "Pending" and x["flagged"])

    t1, t2 = st.columns([4, 1], vertical_alignment="center")
    t1.progress(done / len(rows), text=f"{done} of {len(rows)} confirmed · {flagged_left} need your attention")
    if t2.button("Accept all unflagged", type="tertiary", width="stretch",
                 help="Accept every pending characteristic that has no warnings"):
        for x in rows:
            if x["status"] == "Pending" and not x["flagged"]:
                x["status"] = "Accepted"
        if r["status"] != "Pending":
            advance()
        ss.nav += 1
        st.rerun()

    left, right = st.columns([1.55, 1], gap="large")
    view = overlay.draw(drawing.image, rows, selected=r["id"])
    with left:
        with st.container(border=True):
            st.image(view, width="stretch")
        seq = order(rows)
        marks = {rows[i]["id"]: ICON.get(rows[i]["status"], "!" if rows[i]["flagged"] else "") for i in seq}
        picked = st.pills("Characteristics", [rows[i]["id"] for i in seq], key=f"pills_{ss.nav}", default=r["id"],
                          format_func=lambda b: f"{b} {marks[b]}".strip(), label_visibility="collapsed")
        if picked and picked != r["id"]:
            ss.idx = next(i for i, x in enumerate(rows) if x["id"] == picked)
            st.rerun()
        issues = ss.issues
        if issues:
            with st.expander(f"Drawing checks · {len(issues)}", expanded=any(i["kind"] != "ai" for i in issues)):
                for n, i in enumerate(issues):
                    c1, c2 = st.columns([5, 1], vertical_alignment="center")
                    c1.markdown(f"{'⚠️' if i['kind'] != 'ai' else 'ℹ️'} {i['text']}")
                    if i.get("token") and c2.button("Add", key=f"add_{n}"):
                        new = validation.row_from_token(p, i["token"], rows)
                        rows.append(new)
                        overlay.place_balloons(drawing.image, rows)
                        ss.issues = [x for x in issues if x is not i]
                        ss.idx = len(rows) - 1
                        ss.nav += 1
                        st.rerun()

    with right, st.container(border=True):
        bal = f"balloon {r['balloon']} on drawing" if not r["generated"] else "balloon generated"
        st.markdown(f'<span class="cf-meta">#{r["id"]} · {bal} · zone {r["zone"] or "?"}</span> &nbsp;{pill(r)}',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="cf-name">{html.escape(r["name"])}</div>'
                    f'<div class="cf-notation">{html.escape(r["notation"])}</div>'
                    f'<div class="cf-meta">{html.escape(r["type"])} · {r["tool"]} · {r["confidence"]:.0%} confidence'
                    f'{" · qty " + str(r["qty"]) if (r["qty"] or 1) > 1 else ""}</div>', unsafe_allow_html=True)
        st.image(overlay.crop(view, r), width="stretch")
        if r["flags"]:
            st.warning("\n".join(f"- {f}" for f in dict.fromkeys(r["flags"])))
        b1, b2, b3 = st.columns(3)
        if b1.button("Reject", width="stretch", help="Not a characteristic / wrong - exclude from AS9102"):
            set_status(r, "Rejected")
        with b2.popover("Edit", width="stretch"):
            with st.form(f"edit_{r['key']}", border=False):
                name = st.text_input("Feature name", r["name"])
                notation = st.text_input("Notation", r["notation"])
                c1, c2, c3 = st.columns(3)
                nom = c1.number_input("Nominal", value=r["nominal"], format="%g")
                up_ = c2.number_input("+Tol", value=r["upper"], format="%g")
                lo_ = c3.number_input("−Tol", value=r["lower"], format="%g")
                c4, c5 = st.columns(2)
                tool = c4.selectbox("Inspection tool", TOOLS + ([r["tool"]] if r["tool"] not in TOOLS else []),
                                    index=(TOOLS + [r["tool"]]).index(r["tool"]))
                desig = c5.selectbox("Designator", DESIGNATORS + ([r["designator"]] if r["designator"] not in DESIGNATORS else []),
                                     index=(DESIGNATORS + [r["designator"]]).index(r["designator"]))
                if st.form_submit_button("Save & accept", type="primary", width="stretch"):
                    new = {"name": name, "notation": notation, "nominal": nom, "upper": up_, "lower": lo_,
                           "tool": tool, "designator": desig}
                    changed = [k for k, v in new.items() if v != r[k]]
                    r.update(new)
                    r["_edited"] = sorted(set(r.get("_edited", [])) | set(changed))
                    set_status(r, "Corrected" if r["_edited"] else "Accepted")
        if b3.button("Accept", type="primary", width="stretch"):
            set_status(r, "Corrected" if r.get("_edited") else "Accepted")

    st.write("")
    n1, _, n2 = st.columns([1, 3, 1.2])
    if n1.button("← Start over", type="tertiary"):
        restart()
    left_to_do = len(rows) - done
    if n2.button("Continue to export →" if not left_to_do else f"{left_to_do} left to confirm", type="primary",
                 disabled=bool(left_to_do), width="stretch"):
        go(3)


# ================= 4. EXPORT =================
elif ss.step == 3:
    rows, drawing, ext = ss.rows, ss.drawing, ss.extraction
    cnt = {s: sum(r["status"] == s for r in rows) for s in ("Accepted", "Corrected", "Rejected")}
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.container(border=True):
            st.markdown('<div class="cf-h">Your AS9102 package is ready</div>'
                        f'<div class="cf-c">{cnt["Accepted"] + cnt["Corrected"]} characteristics · '
                        f'{html.escape(ext.drawing.part_number or drawing.filename)}</div>', unsafe_allow_html=True)
            st.write("")
            for col, (k, v) in zip(st.columns(3), cnt.items()):
                col.metric(k, v)
            with st.expander("Report details (Form 1)"):
                c1, c2 = st.columns(2)
                d = ext.drawing
                info = {"part_number": c1.text_input("Part number", d.part_number),
                        "part_name": c2.text_input("Part name", d.part_name),
                        "drawing_number": c1.text_input("Drawing number", d.drawing_number),
                        "revision": c2.text_input("Revision", d.revision),
                        "drawing_revision": d.revision,
                        "serial_number": c1.text_input("Serial number"),
                        "fai_report_number": c2.text_input("FAI report number"),
                        "prepared_by": c1.text_input("Prepared by"),
                        "date": date.today().strftime("%d-%b-%Y"),
                        "material": d.material, "material_spec": d.material_spec}
                tpl = st.file_uploader("Different AS9102 template (optional)", type=["xlsx"])
            clean = overlay.draw(drawing.image, rows, clean=True)
            clean_png = png(clean)
            xlsx = as9102.build_workbook(rows, drawing, info, clean_png, template=tpl.getvalue() if tpl else None,
                                         model=extractor.MODEL)
            ss.xlsx = xlsx
            stem = Path(drawing.filename).stem
            st.download_button("Download AS9102 Excel", xlsx, f"{stem}_AS9102.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               type="primary", width="stretch")
            st.download_button("Download ballooned drawing (PDF)", pdf(clean), f"{stem}_ballooned.pdf",
                               "application/pdf", width="stretch")
            trace = {"drawing": {"filename": drawing.filename, "sha256": drawing.sha256, "page": drawing.page + 1},
                     "model": extractor.MODEL, "analysed_at": ss.get("analysed_at"),
                     "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "drawing_info": ext.drawing.model_dump(), "characteristics": rows}
            d1, d2 = st.columns(2)
            d1.download_button("Traceability JSON", json.dumps(trace, indent=2, default=str, ensure_ascii=False),
                               f"{stem}_traceability.json", "application/json", type="tertiary", width="stretch")
            d2.download_button("Ballooned drawing (PNG)", clean_png, f"{stem}_ballooned.png", "image/png",
                               type="tertiary", width="stretch")
        with st.expander("Preview ballooned drawing"):
            st.image(clean, width="stretch")
        c1, c2 = st.columns(2)
        if c1.button("← Back to review", type="tertiary"):
            go(2)
        if c2.button("New drawing →", type="tertiary", width="stretch"):
            restart()

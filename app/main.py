"""Critical Fair - Streamlit UI.  Run:  streamlit run app/main.py"""
import html
import io
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app import as9102, extractor, hero, overlay, validation  # noqa: E402
from app.drawing import load_drawing  # noqa: E402
from app.perception import assemble, detect_circles, read_text  # noqa: E402

SAMPLES = sorted((ROOT / "samples" / "drawings").glob("*.*"))
STEPS = ["Upload", "Analyse", "Review", "Export"]
SAMPLE_LABELS = {"flange.jpeg": "Flange · GD&T", "cylinder.png": "Hydraulic cylinder",
                 "cylinder_ballooned.png": "Cylinder · pre-ballooned", "plate_synthetic.png": "Mounting plate"}
ICON = {"Accepted": "✓", "Corrected": "✎", "Rejected": "✕"}
PILL = {"Accepted": ("#DCFCE7", "#166534"), "Corrected": ("#DBEAFE", "#1E40AF"), "Rejected": ("#FEE2E2", "#991B1B"),
        "Needs review": ("#FEF3C7", "#92400E"), "Pending": ("#F3F4F6", "#374151")}
TOOLS = ["Caliper", "Micrometer", "Bore Gauge", "Height Gauge", "CMM", "Profilometer", "Thread Gauge (Go/No-Go)",
         "Pin Gauge", "Radius Gauge", "Protractor / CMM", "Dial Indicator", "Optical Comparator", "Visual"]
DESIGNATORS = ["", "Key", "Critical", "Major", "Minor"]
MANUAL_MIN_PER_CHAR, MANUAL_SETUP_MIN = 4, 20  # stated assumption for the time-saved estimate

st.set_page_config(page_title="Critical Fair", page_icon="◎", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
#MainMenu, footer, header[data-testid="stHeader"], [data-testid="stSidebarCollapsedControl"] {display:none;}
html, body, [data-testid="stApp"] {font-family: -apple-system, "SF Pro Text", Inter, "Segoe UI", sans-serif;}
[data-testid="stApp"] {background: #F6F6F3;}
.block-container {max-width: 1320px; padding-top: 1.1rem; padding-bottom: 2rem;}
/* top bar */
.st-key-topbar {background:#fff; border:1px solid #E4E4E0; border-radius:8px; padding:.6rem 1.1rem; margin-bottom:1rem;}
.cf-brand {line-height:1.05;}
.cf-brand {font-size:1.12rem; color:#1C1C1C;} .cf-brand .k {color:#8A8A84; font-weight:400;} .cf-brand .n {font-weight:650;}
.cf-steps {display:flex; gap:.45rem; justify-content:center; align-items:center;}
.cf-step {display:flex; align-items:center; gap:.4rem; color:#9A9A94; font-weight:500; font-size:.88rem; padding:.3rem .2rem;
  border-bottom:2px solid transparent;}
.cf-step b {width:1.25rem; height:1.25rem; border-radius:50%; display:inline-flex; align-items:center; justify-content:center;
  border:1px solid #CFCFC9; font-size:.7rem; font-weight:500;}
.cf-step.on {color:#1C1C1C; border-bottom-color:#1F4E79;} .cf-step.on b {background:#1F4E79; border-color:#1F4E79; color:#fff;}
.cf-step.done {color:#55554F;} .cf-step.done b {border-color:#8FA9C1; color:#1F4E79;}
.cf-sep {color:#D4D4CE; margin:0 .3rem;}
/* cards */
[class*="st-key-card"] {background:#fff; border-radius:8px; padding:1.1rem 1.2rem; border:1px solid #E4E4E0;}
.cf-title {font-size:1rem; font-weight:600; color:#1C1C1C; margin-bottom:.5rem;}
.cf-hero {text-align:center; margin:.8rem 0 1.2rem;}
.cf-hero h1 {font-size:1.7rem; font-weight:650; letter-spacing:-.015em; margin:0; padding:0; color:#1C1C1C;}
.cf-hero p {color:#475569; font-size:1.02rem; margin:.45rem auto 0; max-width:720px;}
.cf-flow {display:flex; justify-content:center; align-items:center; gap:.5rem; flex-wrap:wrap; margin:1rem 0 .2rem;}
.cf-chip {background:#fff; border:1px solid #E2E8F0; border-radius:999px; padding:.3rem .8rem; font-size:.82rem; font-weight:600; color:#334155;}
.cf-chip.ai {background:#EEF2FF; border-color:#C7D2FE; color:#3730A3;}
.cf-arrow {color:#94A3B8;}
.cf-name {font-size:1.3rem; font-weight:650; color:#1C1C1C; margin:.2rem 0 0;}
.cf-notation {font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size:1.08rem; background:#F6F6F3;
  border:1px solid #E4E4E0; border-radius:4px; padding:.3rem .6rem; display:inline-block; margin:.4rem 0 .3rem;}
.cf-meta {color:#64748B; font-size:.86rem;}
.cf-pill {display:inline-block; padding:.12rem .6rem; border-radius:999px; font-size:.74rem; font-weight:700;}
/* analysis */
.cf-stage {display:flex; align-items:center; gap:.7rem; padding:.5rem .1rem; border-bottom:1px solid #F1F5F9;}
.cf-stage:last-child {border-bottom:none;}
.cf-dot {width:1.45rem; height:1.45rem; border-radius:50%; display:inline-flex; align-items:center; justify-content:center;
  font-size:.72rem; font-weight:700; flex-shrink:0;}
.cf-dot.done {background:#DCFCE7; color:#166534;} .cf-dot.run {background:#1F4E79; color:#fff; animation: cfp .9s infinite alternate;}
.cf-dot.wait {background:#F1F5F9; color:#94A3B8;}
@keyframes cfp {from {opacity:1} to {opacity:.4}}
.cf-stage .t {flex:1; font-weight:600; font-size:.92rem; color:#0F172A;} .cf-stage .d {color:#64748B; font-size:.8rem;}
.cf-stage.wait .t {color:#94A3B8; font-weight:500;}
.cf-feed {max-height: 340px; overflow:hidden;}
.cf-item {display:flex; gap:.6rem; align-items:baseline; padding:.34rem 0; border-bottom:1px dashed #E2E8F0; animation: cfin .35s ease-out;}
.cf-item .n {background:#1F4E79; color:#fff; border-radius:6px; font-size:.7rem; font-weight:700; padding:.05rem .4rem; min-width:1.6rem; text-align:center;}
.cf-item .nm {font-weight:600; font-size:.88rem; color:#0F172A;}
.cf-item .nt {font-family:ui-monospace,Menlo,monospace; font-size:.8rem; color:#475569; margin-left:auto; white-space:nowrap;}
@keyframes cfin {from {opacity:0; transform: translateY(-6px)} to {opacity:1; transform:none}}
.cf-legend {display:flex; gap:1.1rem; color:#64748B; font-size:.8rem; margin-top:.5rem;}
/* KPIs */
.cf-kpis {display:grid; grid-template-columns: repeat(4, 1fr); gap:.9rem; margin:.2rem 0 1rem;}
.cf-kpi {background:#fff; border:1px solid #E4E4E0; border-radius:8px; padding:.8rem 1rem;}
.cf-kpi .v {font-size:1.5rem; font-weight:600; color:#1C1C1C;} .cf-kpi .l {color:#6B6B66; font-size:.8rem;}
.cf-kpi.win .v {color:#1F4E79;}
.cf-mini {display:flex; gap:.5rem; flex-wrap:wrap;}
.cf-mini span {background:#fff; border:1px solid #E4E4E0; border-radius:4px; padding:.2rem .6rem; font-size:.8rem; color:#55554F;}
.cf-mini b {color:#0F172A;}
.stButton button, .stDownloadButton button {border-radius:6px; font-weight:500;}
</style>""", unsafe_allow_html=True)

ss = st.session_state
for k, v in {"step": 0, "idx": 0, "nav": 0}.items():
    ss.setdefault(k, v)


# ---------------- helpers ----------------
def go(step: int):
    ss.step = step
    st.rerun()


def restart():
    for k in ("rows", "source", "drawing", "perception", "extraction", "issues", "t_start", "t_analysis"):
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


def fmt_dur(s: float) -> str:
    s = int(s)
    return f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


def manual_minutes(n: int) -> int:
    return MANUAL_SETUP_MIN + MANUAL_MIN_PER_CHAR * n


def stage_html(stages, cur, notes):
    out = []
    for i, name in enumerate(stages):
        cls = "done" if i < cur else "run" if i == cur else "wait"
        dot = "✓" if i < cur else str(i + 1)
        out.append(f'<div class="cf-stage {cls}"><span class="cf-dot {cls}">{dot}</span>'
                   f'<span class="t">{name}</span><span class="d">{html.escape(notes.get(i, ""))}</span></div>')
    return "".join(out)


def feed_html(items):
    rows = [f'<div class="cf-item"><span class="n">{n}</span><span class="nm">{html.escape(nm)}</span>'
            f'<span class="nt">{html.escape(nt[:34])}</span></div>'
            for n, (_, nm, nt) in reversed(list(enumerate(items, 1)))][:9]
    return f'<div class="cf-feed">{"".join(rows)}</div>'


# ---------------- top bar ----------------
with st.container(key="topbar"):
    h1, h2, h3 = st.columns([1.3, 3, 0.9], vertical_alignment="center")
    h1.markdown('<div class="cf-brand"><span class="k">Project</span> <span class="n">Critical Fair</span></div>',
                unsafe_allow_html=True)
    h2.markdown('<div class="cf-steps">' + '<span class="cf-sep">›</span>'.join(
        f'<div class="cf-step {"on" if i == ss.step else "done" if i < ss.step else ""}">'
        f'<b>{"✓" if i < ss.step else i + 1}</b>{s}</div>' for i, s in enumerate(STEPS)) + '</div>',
        unsafe_allow_html=True)
    with h3.popover("Settings", icon=":material/tune:", width="stretch"):
        st.caption(f"Model · `{extractor.MODEL}` · effort `{extractor.EFFORT}`" if extractor.has_api_key()
                   else "No API key · only previously analysed drawings work")
        validation.CONFIDENCE_THRESHOLD = st.slider("Flag below confidence", 0.5, 1.0, 0.8, 0.05)
        ss.force = st.toggle("Re-analyse (ignore saved result)", value=ss.get("force", False))


# ================= 1. UPLOAD =================
if ss.step == 0:
    components.html(hero.html(), height=404)
    _, mid, _ = st.columns([0.6, 2, 0.6])
    with mid, st.container(key="card_upload"):
        up = st.file_uploader("Drop an engineering drawing — PDF, PNG or JPG", type=["pdf", "png", "jpg", "jpeg"])
        if up is not None:
            ss.source = (up.name, up.getvalue())
        elif SAMPLES:
            pick = st.pills("or try a sample", [s.name for s in SAMPLES], selection_mode="single",
                            format_func=lambda n: SAMPLE_LABELS.get(n, n))
            if pick:
                ss.source = (pick, (ROOT / "samples" / "drawings" / pick).read_bytes())
        if "source" in ss:
            name, data = ss.source
            drawing = load_drawing(name, data)
            st.image(drawing.image, width="stretch")
            ready = extractor.has_api_key() or extractor.cached(drawing.sha256)
            if not ready:
                st.error("Set ANTHROPIC_API_KEY in .env to analyse new drawings.")
            elif st.button("Analyse drawing  →", type="primary", width="stretch"):
                ss.drawing = drawing
                ss.t_start = time.time()
                go(1)


    st.markdown('<div style="text-align:center;color:#9A9A94;font-size:.8rem;margin-top:1.4rem">'
                'Project Critical Fair · built by Manish, Pratyush and Nitish</div>', unsafe_allow_html=True)


# ================= 2. ANALYSE (live) =================

elif ss.step == 1:
    # hide the previous screen's elements while this long-running step renders
    st.markdown('<style>[data-stale="true"], .stale-element {display:none !important;}</style>', unsafe_allow_html=True)
    drawing = ss.drawing
    stages = ["Uploading drawing", "Reading text & symbols", "Detecting balloons", "Interpreting characteristics",
              "Validating", "Placing balloons & preparing AS9102"]
    notes = {}
    left, right = st.columns([1.6, 1], gap="medium")
    with left, st.container(key="card_canvas"):
        st.markdown('<div class="cf-title">Analysing drawing</div>', unsafe_allow_html=True)
        canvas = st.empty()
        legend = st.empty()
    with right:
        with st.container(key="card_stages"):
            bar = st.progress(0.0)
            box = st.empty()
            eta_line = st.empty()
        with st.container(key="card_feed"):
            st.markdown('<div class="cf-title">Characteristics found</div>', unsafe_allow_html=True)
            feed = st.empty()
    t0 = time.time()
    state = {"items": [], "last_draw": 0.0}

    def show(cur, frac, eta=None):
        box.markdown(stage_html(stages, cur, notes), unsafe_allow_html=True)
        bar.progress(min(1.0, frac))
        eta_line.caption(f"Elapsed {time.time() - t0:.0f}s" + (f" · about {max(1, eta):.0f}s remaining" if eta else ""))

    def paint(stage, force=False):
        if force or time.time() - state["last_draw"] > 0.8:
            canvas.image(overlay.live_view(drawing.image, p, stage, state["items"]), width="stretch")
            feed.markdown(feed_html(state["items"]), unsafe_allow_html=True)
            state["last_draw"] = time.time()

    canvas.image(drawing.image, width="stretch")
    notes[0] = f"{len(ss.source[1]) / 1024:.0f} KB"
    show(1, 0.04)
    raw, src = read_text(drawing.image, drawing.pdf_text)
    p = assemble(drawing.image, raw, src, [])
    notes[1] = f"{len(p.tokens)} text items located ({'vector PDF' if src == 'pdf' else 'OCR'})"
    paint(1, True)
    legend.markdown('<div class="cf-legend"><span><span style="color:#96968C">■</span> text located</span>'
                    '<span><span style="color:#C0392B">○</span> existing balloon</span>'
                    '<span><span style="color:#1F4E79">■</span> characteristic identified</span></div>',
                    unsafe_allow_html=True)
    show(2, 0.1)
    circles = detect_circles(drawing.image)
    p = assemble(drawing.image, raw, src, circles)
    notes[2] = f"{sum(1 for c in circles if c.digits) or len(circles)} existing balloons" if p.has_balloons \
        else "None on drawing — will generate"
    paint(2, True)
    est, exp_n = extractor.estimate_seconds(p), extractor.expected_count(p)
    show(3, 0.15, est)
    cached_hit = None if ss.get("force") else extractor.cached(drawing.sha256)
    try:
        if cached_hit:  # replay the saved analysis so the process stays visible
            ext = cached_hit
            for c in ext.characteristics:
                state["items"].append((c.tokens, c.name, c.notation))
                notes[3] = f"{len(state['items'])} found · saved analysis"
                show(3, 0.15 + 0.7 * len(state["items"]) / max(1, len(ext.characteristics)))
                paint(3, True)
                time.sleep(min(0.18, 4.0 / max(1, len(ext.characteristics))))
        else:
            if ss.get("force"):
                for d in extractor.CACHE_DIRS:
                    (d / f"{drawing.sha256}.json").unlink(missing_ok=True)

            def progress(text, elapsed):
                items = extractor.partial_items(text)
                state["items"] = items
                notes[3] = f"{len(items)} found so far"
                frac = 0.15 + 0.7 * min(0.97, max(elapsed / est, len(items) / max(exp_n, 1)))
                show(3, frac, max(2, est - elapsed))
                paint(3)
            ext = extractor.extract(drawing.image, p, drawing.sha256, on_progress=progress)
            state["items"] = [(c.tokens, c.name, c.notation) for c in ext.characteristics]
        notes[3] = f"{len(ext.characteristics)} characteristics"
        paint(3, True)
    except extractor.ExtractionError as e:
        st.error(str(e))
        if st.button("← Back"):
            go(0)
        st.stop()
    show(4, 0.9)
    rows, issues = validation.build(ext, p)
    flagged = sum(r["flagged"] for r in rows)
    notes[4] = f"{len(p.tokens) + len(circles) + len(rows) * 6} checks · {flagged} to review"
    show(5, 0.95)
    overlay.place_balloons(drawing.image, rows, p)
    generated = sum(1 for r in rows if r["generated"])
    notes[5] = f"{generated} balloons placed" if generated else "Balloons linked"
    canvas.image(overlay.draw(drawing.image, rows), width="stretch")
    show(6, 1.0)
    ss.perception, ss.extraction, ss.rows, ss.issues = p, ext, rows, issues
    ss.t_analysis = time.time() - t0
    ss.analysed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ss.idx = order(rows)[0] if rows else 0
    ss.nav += 1
    time.sleep(1.2)
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
    generated = sum(1 for x in rows if x["generated"])

    t1, t2, t3 = st.columns([3.2, 1, 1], vertical_alignment="center")
    with t1:
        st.markdown(f'<div class="cf-mini"><span><b>{len(rows)}</b> characteristics</span>'
                    f'<span><b>{generated}</b> balloons generated</span>'
                    f'<span><b>{flagged_left}</b> need a decision</span>'
                    f'<span>analysed in <b>{fmt_dur(ss.get("t_analysis", 0))}</b></span></div>', unsafe_allow_html=True)
        st.progress(done / len(rows), text=f"{done} of {len(rows)} confirmed")
    if t2.button("Accept all unflagged", width="stretch", help="Accept every pending item that passed all checks"):
        for x in rows:
            if x["status"] == "Pending" and not x["flagged"]:
                x["status"] = "Accepted"
        if r["status"] != "Pending":
            advance()
        ss.nav += 1
        st.rerun()
    with t3.popover("Skip review", icon=":material/fast_forward:", width="stretch"):
        st.markdown(f"Accept the AI's reading for all **{len(rows) - done}** remaining characteristics"
                    f"{f' (incl. {flagged_left} flagged)' if flagged_left else ''} and go straight to export.")
        st.caption("They are marked 'accepted without individual review' in the report.")
        if st.button("Accept all & export", type="primary", width="stretch"):
            for x in rows:
                if x["status"] == "Pending":
                    x["status"], x["_skipped"] = "Accepted", True
            go(3)

    left, right = st.columns([1.55, 1], gap="medium")
    view = overlay.draw(drawing.image, rows, selected=r["id"])
    with left:
        with st.container(key="card_drawing"):
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
            with st.expander(f"Drawing-level checks · {len(issues)}", expanded=any(i["kind"] != "ai" for i in issues)):
                for n, i in enumerate(issues):
                    c1, c2 = st.columns([5, 1], vertical_alignment="center")
                    c1.markdown(f"{'**Check** · ' if i['kind'] != 'ai' else 'Note · '}{i['text']}")
                    if i.get("token") and c2.button("Add", key=f"add_{n}"):
                        new = validation.row_from_token(p, i["token"], rows)
                        rows.append(new)
                        overlay.place_balloons(drawing.image, rows, p)
                        ss.issues = [x for x in issues if x is not i]
                        ss.idx = len(rows) - 1
                        ss.nav += 1
                        st.rerun()

    with right, st.container(key="card_item"):
        bal = f"balloon {r['balloon']} on drawing" if not r["generated"] else "balloon generated"
        st.markdown(f'<span class="cf-meta">#{r["id"]} · {bal} · zone {r["zone"] or "?"}</span> &nbsp;{pill(r)}',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="cf-name">{html.escape(r["name"])}</div>'
                    f'<div class="cf-notation">{html.escape(r["notation"])}</div>'
                    f'<div class="cf-meta">{html.escape(as9102.dimension_type(r))} · {r["tool"]} · '
                    f'{r["confidence"]:.0%} confidence{" · qty " + str(r["qty"]) if (r["qty"] or 1) > 1 else ""}</div>',
                    unsafe_allow_html=True)
        st.image(overlay.crop(view, r), width="stretch")
        if r["flags"]:
            st.warning("\n".join(f"- {f}" for f in dict.fromkeys(r["flags"])))
        else:
            st.success("Passed all automated checks")
        b1, b2, b3 = st.columns(3)
        if b1.button("Reject", width="stretch", help="Not a characteristic / wrong — exclude from the report"):
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
    if n2.button("Generate AS9102 →" if not left_to_do else f"{left_to_do} left to confirm", type="primary",
                 disabled=bool(left_to_do), width="stretch"):
        go(3)


# ================= 4. EXPORT =================
elif ss.step == 3:
    rows, drawing, ext = ss.rows, ss.drawing, ss.extraction
    out_rows = as9102.exported_rows(rows)
    cnt = {s: sum(r["status"] == s for r in rows) for s in ("Accepted", "Corrected", "Rejected")}
    total_s = time.time() - ss.get("t_start", time.time())
    manual = manual_minutes(len(out_rows))
    skipped = sum(1 for r in rows if r.get("_skipped"))
    kpi3 = (f'<div class="cf-kpi"><div class="v">{skipped}</div><div class="l">accepted without individual review</div></div>'
            if skipped else f'<div class="cf-kpi"><div class="v">{cnt["Corrected"] + cnt["Rejected"]}</div>'
                            f'<div class="l">AI results corrected / rejected by engineer</div></div>')
    st.markdown(f'<div class="cf-hero" style="margin-bottom:.4rem"><h1>Report ready</h1>'
                f'<p>{html.escape(" · ".join(x for x in (ext.drawing.part_name or "Engineering drawing", ext.drawing.part_number) if x))}'
                f'</p></div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="cf-kpis">
      <div class="cf-kpi"><div class="v">{len(out_rows)}</div><div class="l">characteristics in the report</div></div>
      <div class="cf-kpi"><div class="v">{sum(1 for r in rows if r['generated'])}</div><div class="l">balloons placed automatically</div></div>
      {kpi3}
      <div class="cf-kpi win"><div class="v">{fmt_dur(total_s)}</div><div class="l">total time · manual estimate ≈ {manual // 60}h {manual % 60:02d}m*</div></div>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns([1.5, 1], gap="large")
    with right, st.container(key="card_download"):
        st.markdown('<div class="cf-title">Download</div>', unsafe_allow_html=True)
        d = ext.drawing
        with st.expander("Report details (Part Info sheet)"):
            c1, c2 = st.columns(2)
            info = {"part_number": c1.text_input("Part number", d.part_number),
                    "part_name": c2.text_input("Part name", d.part_name),
                    "drawing_number": c1.text_input("Drawing number", d.drawing_number),
                    "revision": c2.text_input("Revision", d.revision),
                    "drawing_revision": d.revision,
                    "serial_number": c1.text_input("Serial / lot number"),
                    "fai_report_number": c2.text_input("FAI report number"),
                    "inspector": c1.text_input("Inspector name"),
                    "customer": c2.text_input("Customer"),
                    "material": d.material, "material_spec": d.material_spec}
            tpl = st.file_uploader("Different template (optional)", type=["xlsx"])
        clean = overlay.draw(drawing.image, rows, clean=True)
        clean_png = png(clean)
        xlsx = as9102.build_workbook(rows, drawing, info, clean_png, template=tpl.getvalue() if tpl else None,
                                     model=extractor.MODEL)
        ss.xlsx = xlsx
        names = as9102.file_names(info, drawing)
        st.download_button("Download AS9102 Excel", xlsx, names["xlsx"],
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           type="primary", width="stretch", icon=":material/table_view:")
        st.download_button("Ballooned drawing · A3 PDF", overlay.a3_pdf(clean, " · ".join(
                               x for x in (as9102.doc_id(info, drawing), d.part_name) if x)),
                           names["pdf"], "application/pdf", width="stretch",
                           icon=":material/picture_as_pdf:")
        trace = {"document": as9102.doc_id(info, drawing),
                 "drawing": {"sha256": drawing.sha256, "page": drawing.page + 1},
                 "model": extractor.MODEL, "analysed_at": ss.get("analysed_at"),
                 "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "drawing_info": ext.drawing.model_dump(), "characteristics": rows}
        st.download_button("Traceability record (JSON)", json.dumps(trace, indent=2, default=str, ensure_ascii=False),
                           names["json"], "application/json", type="tertiary", width="stretch")
        st.caption("A3 landscape · team template · traceability sheet included")
        c1, c2 = st.columns(2)
        if c1.button("← Back to review", type="tertiary"):
            go(2)
        if c2.button("New drawing →", type="tertiary", width="stretch"):
            restart()
    with left, st.container(key="card_preview"):
        tab1, tab2 = st.tabs(["Characteristics sheet", "Ballooned drawing"])
        with tab1:
            st.dataframe(pd.DataFrame(as9102.preview(rows)), hide_index=True, width="stretch", height=430)
        with tab2:
            st.image(clean, width="stretch")
    st.caption(f"*Manual estimate assumes ~{MANUAL_MIN_PER_CHAR} min per characteristic to balloon, interpret and "
               f"transcribe, plus {MANUAL_SETUP_MIN} min setup.")

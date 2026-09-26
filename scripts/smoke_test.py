"""Headless end-to-end UI test on a sample with a saved analysis (no API call)."""
import io
from pathlib import Path

from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
at = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=120).run()


def click(label, exact=False):
    next(b for b in at.button if (b.label == label if exact else b.label.startswith(label))).click().run()
    assert not at.exception, at.exception


for sample in ["flange.jpeg", "cylinder_ballooned.png"]:
    at.session_state["source"] = (sample, (ROOT / "samples" / "drawings" / sample).read_bytes())
    at.run()
    click("Analyse drawing")          # -> analyse stage runs to completion -> review
    assert at.session_state["step"] == 2, at.session_state["step"]
    rows = at.session_state["rows"]
    click("Accept all unflagged")
    while any(r["status"] == "Pending" for r in at.session_state["rows"]):
        click("Accept", exact=True)
    click("Generate AS9102")
    assert at.session_state["step"] == 3
    wb = load_workbook(io.BytesIO(at.session_state["xlsx"]))
    ch = wb["Characteristics"]
    data = [r for r in ch.iter_rows(min_row=2, max_col=11, values_only=True) if r[0] is not None]
    print(sample, "->", wb.sheetnames, f"{len(data)} characteristic rows")
    for r in data[:3]:
        print("   ", r[:7], r[9])
    pi = wb["Part Info, Drawing & GDT Ref"]
    print("    Part info:", pi["B4"].value, "|", pi["D4"].value, "| images:", len(pi._images))
    click("New drawing")
print("OK")

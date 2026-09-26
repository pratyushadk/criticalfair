# Critical Fair

Engineering drawing → ballooned drawing → AS9102 FAIR (Forms 1–3), with a human confirming every characteristic.

## Run
```bash
cd critical-fair
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env        # never commit .env
.venv/bin/streamlit run app/main.py
```
The four samples in `samples/drawings/` have saved analyses (`samples/cache/`) - they load instantly and work offline.

## Demo script (≈2 min)
1. **Upload** → pick `flange.jpeg` (no balloons) → *Analyse drawing*. Point out the live stages.
   The analysis screen shows the drawing being read live: text located → balloons found → characteristics identified.
2. **Review**: balloons generated next to each dimension (never on top of text); card shows feature name, exact notation, tool, zone.
   *Accept all unflagged*, then resolve the amber ones (Accept / Edit / Reject).
3. **Export** → impact summary + preview of the Characteristics sheet → *Download AS9102 Excel*
   (team "Final Template": Part Info with the ballooned drawing, Characteristics with PASS/FAIL formulas and
   dropdown, Summary, plus a Traceability sheet) and the ballooned drawing PDF.
4. Repeat with `cylinder_ballooned.png` to show existing-balloon detection, duplicate balloon numbers (5.1/5.2),
   missing numbers (3, 8, 9) and unballooned dimensions being caught.

## Tests
- `.venv/bin/python scripts/smoke_test.py` – headless UI end-to-end on cached samples (no API).
- `.venv/bin/python scripts/live_test.py <drawing>` – live Claude run with timings.
- `.venv/bin/python scripts/render_test.py <drawing>` – full pipeline → overlays in `output/`.

Implementation docs: `docs/ARCHITECTURE.md`, `docs/PRD.md`, `docs/SRD.md`. Team specs: `ARCHITECTURE.md`, `PRD.md`, `SRS_PART1.md`, `SRS_PART2.md`.

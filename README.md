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
2. **Review**: balloons generated right on each dimension; card shows feature name, exact notation, tool, zone.
   *Accept all unflagged*, then resolve the amber ones (Accept / Edit / Reject).
3. **Export** → *Download AS9102 Excel*: Form 1 from title block, Form 3 with zone ("Sht 1, B4"),
   "Overall Length: 150.00 ±0.10 mm", tooling, plus Traceability + Ballooned Drawing sheets.
4. Repeat with `cylinder_ballooned.png` to show existing-balloon detection, duplicate balloon numbers (5.1/5.2),
   missing numbers (3, 8, 9) and unballooned dimensions being caught.

## Tests
- `.venv/bin/python scripts/smoke_test.py` – headless UI end-to-end on cached samples (no API).
- `.venv/bin/python scripts/live_test.py <drawing>` – live Claude run with timings.
- `.venv/bin/python scripts/render_test.py <drawing>` – full pipeline → overlays in `output/`.

Implementation docs: `docs/ARCHITECTURE.md`, `docs/PRD.md`, `docs/SRD.md`. Team specs: `ARCHITECTURE.md`, `PRD.md`, `SRS_PART1.md`, `SRS_PART2.md`.

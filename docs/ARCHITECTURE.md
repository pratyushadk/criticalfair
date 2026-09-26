# Critical Fair — Architecture

```
Upload (PDF / PNG / JPG)
  │
  ├─ 1. Local perception  (app/perception.py, ~1 s, no AI)
  │     • Text with EXACT boxes: vector-PDF text (PyMuPDF) or Apple Vision OCR (multi-pass + rotated)
  │     • Balloon circles: OpenCV Hough + complete-ring test + masked digit OCR
  │     • Zone grid from border labels (fallback: virtual 8×4 grid)
  │
  ├─ 2. Claude vision, ONE streamed call  (app/extractor.py)
  │     image + numbered text tokens (T#) + circles (C#)  →  structured Extraction
  │     Claude only *associates and interprets*: balloon C# ↔ text T#, values, GD&T, name, tool.
  │     Opus 5 · effort medium · fast mode (auto-fallback) · results cached by drawing SHA-256
  │
  ├─ 3. Validation  (app/validation.py, deterministic)
  │     exact location = union of token boxes · unique IDs (duplicates → 5.1/5.2) · missing balloon numbers ·
  │     detected-but-unlinked balloons · dimension-like text not used (possible misses) · balloon far from
  │     requirement · low confidence · tolerance sanity · tool fallback rules
  │
  ├─ 4. Balloons  (app/overlay.py)
  │     existing balloons: ringed, never covered · new balloons: placed in nearest white space, no overlaps
  │
  ├─ 5. Review UI (app/main.py): flagged first, accept / edit / reject, add missed text as characteristic
  │
  └─ 6. Export (app/as9102.py): team "Final Template" (templates/AS9102_template.xlsx) - Part Info fields +
        ballooned drawing in the placeholder, Characteristics rows (dropdown type, nominal/±tol for the PASS/FAIL
        formula, equipment), Summary ranges extended if >30 rows; dropdown re-created (openpyxl drops the x14
        version); missing dimension types appended to the reference list and marked. + Traceability sheet.
```

Why this design: vision models are good at *reading* drawings but imprecise at *pixel coordinates*.
Local OCR/CV gives exact positions; Claude references their IDs. This fixed balloon misalignment
(errors of ~200 px before) and made one call enough (≈20–50 s vs 2+ min for two calls).

Config (.env): `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` (claude-opus-5), `CLAUDE_EFFORT` (medium), `CLAUDE_FAST_MODE` (1).
Template cell map: `PART_CELLS`, `FIRST_ROW`, `REF_FIRST/REF_LAST`, `IMAGE_AREA` in `app/as9102.py`.

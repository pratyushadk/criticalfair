# Critical Fair — SRD

| ID | Requirement | Where |
|----|-------------|-------|
| F1 | Accept PDF (page 1, 200 DPI render) / PNG / JPG, with or without balloons | drawing.py |
| F2 | Exact text boxes: vector-PDF text, else Apple Vision OCR (normal, 2× upscale, fast, rotated passes, merged) | perception.py |
| F3 | Balloon detection: Hough circles + ≥80 % ring completeness + fill filter + masked digit OCR | perception.py |
| F4 | One streamed Claude call; structured output referencing T#/C# IDs; symbols read visually; unknowns = null + issue | extractor.py |
| F5 | Each characteristic: feature name (human-readable), exact notation, type, nominal/tolerances, qty, GD&T, designator (only if marked), inspection tool, confidence | schemas.py |
| F6 | Unique IDs: duplicates on drawing → n.1/n.2; unballooned requirements get new numbers; flags on all | validation.py |
| F7 | Pre-export checks: missing balloon numbers, detected-but-unlinked balloons, unused dimension text, far balloon↔requirement, duplicates, low confidence, tolerance sanity | validation.py |
| F8 | Generated balloons placed in free white space next to the requirement, no overlaps; existing balloons ringed, never covered | overlay.py |
| F9 | Review: flagged first; accept / edit / reject; add missed text; export unlocked when all confirmed | main.py |
| F10 | AS9102: team template Forms 1–3, values only (formatting preserved, row style copied), Form 3 = char no, "Sht n, zone", designator, "Name: notation", tooling | as9102.py |
| F11 | Traceability: sheet + JSON with char no ↔ balloon, zone, pixel box, exact/approx, tokens, AI raw output, review status, edited fields, drawing SHA-256 | as9102.py |
| F12 | Staged progress UI with live count, elapsed and ETA; results cached by SHA-256 | main.py, extractor.py |

Non-functional: key only from `.env` (git-ignored); single Streamlit process; no DB.

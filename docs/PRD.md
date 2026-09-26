# Critical Fair — PRD

## Problem
Quality engineers manually read ballooned engineering drawings, interpret each characteristic
(dimension, tolerance, GD&T, datums, notes) and retype it into AS9102 Form 3. Slow, repetitive, error-prone.

## Goal (hackathon PoC)
Drawing in → reviewable, traceable AS9102 Excel out. An engineering-documentation **copilot**, not an
autonomous certification system: a human verifies every characteristic before export.

## Users
Quality / manufacturing engineers preparing First Article Inspection Reports (FAIR).

## MVP scope
1. Upload PDF (first page) or PNG/JPG drawing, with or without balloons.
2. Local perception finds text (exact boxes) and existing balloon circles; Claude associates and interprets.
3. Balloons: existing ones detected (duplicates/missing flagged); missing ones generated next to their dimension.
4. Human-readable requirement ("Overall Length: 150.00 ±0.10 mm") + exact notation + inspection tool.
5. Review: flagged first; accept / edit / reject; add missed text as a characteristic.
6. Export the team's AS9102 template (Forms 1–3), Traceability sheet, ballooned drawing PDF/PNG, JSON.
7. Analysis in ~20–60 s with staged progress; repeat drawings load instantly from cache.

## Out of scope
ML training, YOLO, RAG, auth, DB, microservices, CAD interpretation, multi-page batch, every standard.

## Success criteria (demo)
- One representative drawing processed end-to-end in < 2 minutes.
- Every exported row links to balloon #, drawing file (+SHA-256), region, AI raw values, reviewer status.
- Low-confidence / flagged rows visibly highlighted and blocked from "auto-accept".

## Inputs
- Team AS9102 template → `templates/AS9102_template.xlsx` (built by `scripts/make_template.py`).
- Test drawings → `samples/drawings/` (flange, cylinder with/without balloons, synthetic plate).

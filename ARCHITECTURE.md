# Technical Architecture

## AI Engineering Drawing to AS9102 Automation

**Version:** 1.0\
**Status:** Hackathon MVP\
**Date:** 2026-09-26

------------------------------------------------------------------------

# 1. Architecture Overview

The system follows a pipeline architecture with a strict separation
between AI interpretation and deterministic document generation.

``` text
                  ┌─────────────────────┐
                  │       USER          │
                  └──────────┬──────────┘
                             │
                             v
                  ┌─────────────────────┐
                  │    Streamlit UI     │
                  └──────────┬──────────┘
                             │
                             v
                  ┌─────────────────────┐
                  │ Drawing Ingestion   │
                  │ PDF / Image Handler │
                  └──────────┬──────────┘
                             │
                             v
                  ┌─────────────────────┐
                  │     Claude API      │
                  │ Vision + Reasoning  │
                  └──────────┬──────────┘
                             │
                             v
                  ┌─────────────────────┐
                  │ Structured JSON     │
                  │ Characteristic Set  │
                  └───────┬─────┬───────┘
                          │     │
                ┌─────────┘     └──────────┐
                v                           v
      ┌──────────────────┐       ┌──────────────────┐
      │ Balloon Renderer │       │ Validation Layer │
      └────────┬─────────┘       └────────┬─────────┘
               │                          │
               v                          v
      Annotated Drawing          Reviewed Characteristics
                                          │
                                          v
                                ┌──────────────────┐
                                │ AS9102 Mapper    │
                                └────────┬─────────┘
                                         │
                                         v
                                ┌──────────────────┐
                                │ Excel Generator  │
                                └────────┬─────────┘
                                         │
                                         v
                                  AS9102 Workbook
```

------------------------------------------------------------------------

# 2. Component Responsibilities

## 2.1 Streamlit UI

Responsibilities:

-   File upload.
-   Trigger analysis.
-   Display processing state.
-   Display annotated drawing.
-   Display extracted characteristics.
-   Allow review/correction.
-   Trigger Excel generation.
-   Provide output artifacts.

The UI should contain minimal business logic.

------------------------------------------------------------------------

## 2.2 Drawing Ingestion

Responsibilities:

-   Validate input.
-   Read PDF/image.
-   Determine page count.
-   Preserve original file.
-   Provide a representation suitable for Claude.

Recommended MVP tools:

-   PyMuPDF for PDF handling.
-   PIL/OpenCV for image operations.

------------------------------------------------------------------------

## 2.3 Claude Extraction Service

Responsibilities:

-   Send drawing content to Claude.
-   Apply engineering-specific system instructions.
-   Request structured output.
-   Parse model response.
-   Return normalized characteristics.

The Claude integration should be isolated behind a Python function/class
so that the rest of the application does not depend directly on
API-specific implementation details.

------------------------------------------------------------------------

# 3. AI Prompt Architecture

Use four conceptual sections.

``` text
SYSTEM INSTRUCTIONS
        +
ENGINEERING REFERENCE
        +
DRAWING
        +
OUTPUT SCHEMA
```

## 3.1 System Instructions

The prompt should establish:

-   Engineering drawing interpretation role.
-   No invention.
-   Visual symbol interpretation.
-   Source preservation.
-   Explicit uncertainty.
-   Structured output.

## 3.2 Engineering Reference

For the MVP, use a small controlled reference containing:

-   Common GD&T symbols.
-   Datum concepts.
-   Tolerance conventions.
-   Approved examples.
-   AS9102 mapping guidance relevant to the template.

The reference should not replace the actual drawing.

## 3.3 Drawing

The drawing is the primary source of characteristic information.

## 3.4 Output Schema

All model results should conform to the application schema.

------------------------------------------------------------------------

# 4. Data Model

Recommended top-level object:

``` json
{
  "drawing": {
    "file_name": "drawing.pdf",
    "page_count": 1
  },
  "characteristics": [],
  "analysis": {
    "model": "claude",
    "status": "complete"
  }
}
```

Characteristic object:

``` json
{
  "balloon_id": "17",
  "type": "diameter",
  "requirement": "Ø25 ±0.05 mm",
  "nominal": 25.0,
  "upper_tolerance": 0.05,
  "lower_tolerance": -0.05,
  "unit": "mm",
  "gdt": {
    "type": null,
    "tolerance": null,
    "modifiers": [],
    "datums": []
  },
  "source": {
    "page": 1,
    "bbox": [1200, 800, 1340, 910],
    "text": "Ø25 ±0.05"
  },
  "confidence": 0.97,
  "status": "VERIFIED"
}
```

------------------------------------------------------------------------

# 5. Balloon Rendering

The rendering component consumes:

``` text
Original drawing
+
Characteristic bounding boxes
+
Balloon IDs
```

It generates:

``` text
Annotated drawing
```

Implementation approach:

1.  Render PDF page at sufficient resolution.
2.  Convert coordinates if necessary.
3.  Draw a numbered circle.
4.  Draw a leader line toward the source region.
5.  Save a separate annotated image.
6.  Optionally create an annotated PDF later.

For the hackathon, the renderer should prioritize clarity over exact
drafting-standard balloon aesthetics.

------------------------------------------------------------------------

# 6. Validation Architecture

Validation consists of two levels.

## 6.1 Schema Validation

Deterministic checks:

-   Correct data types.
-   Required fields.
-   Valid status values.
-   Valid numeric fields.
-   Valid bounding boxes.

## 6.2 Engineering Validation

AI/domain checks:

-   Does the characteristic correspond to the balloon?
-   Is the source text consistent with the parsed value?
-   Is the GD&T interpretation visually supported?
-   Are datum references preserved?
-   Is the requirement complete enough for documentation?

------------------------------------------------------------------------

# 7. Human Review

The review interface should show:

``` text
Balloon 17
--------------------------
Requirement:
Ø25 ±0.05 mm

Type:
Diameter

GD&T:
None

Confidence:
97%

Status:
VERIFIED

Source:
Sheet 1 / Region C4

[Approve] [Edit]
```

For low-confidence results:

``` text
Balloon 21
--------------------------
Status: REVIEW_REQUIRED

Potential issue:
Possible ambiguity between 0.10 and Ø0.10.

[View Source] [Edit]
```

------------------------------------------------------------------------

# 8. AS9102 Mapping Layer

The mapping layer translates normalized characteristics into the
supplied workbook's structure.

``` text
Characteristic JSON
        |
        v
AS9102 Mapping Rules
        |
        v
Template Cell Mapping
        |
        v
Workbook
```

Do not place AI interpretation directly inside Excel-writing code.

Example conceptual mapping:

``` python
mapping = {
    "characteristic_number": "A",
    "drawing_reference": "B",
    "requirement": "C"
}
```

The actual cell mapping must be configured against the supplied
template.

------------------------------------------------------------------------

# 9. Excel Generation

The generator should:

1.  Load a copy of the source template.
2.  Iterate through approved characteristics.
3.  Populate mapped cells.
4.  Preserve formatting.
5.  Save to a new file.
6.  Return the output path.

Recommended Python library:

``` text
openpyxl
```

------------------------------------------------------------------------

# 10. Recommended Project Structure

``` text
project/
│
├── app.py
│
├── ai/
│   ├── claude_client.py
│   ├── prompts.py
│   └── schemas.py
│
├── drawing/
│   ├── ingestion.py
│   └── balloon_renderer.py
│
├── validation/
│   └── validator.py
│
├── as9102/
│   ├── mapper.py
│   └── excel_generator.py
│
├── templates/
│   └── AS9102_template.xlsx
│
├── data/
│   └── demo_drawing.pdf
│
├── output/
│
└── docs/
    ├── PRD.md
    ├── SRS_PART1.md
    ├── SRS_PART2.md
    └── ARCHITECTURE.md
```

------------------------------------------------------------------------

# 11. Three-Person Ownership

## Technical Lead 1 --- AI/Backend

Owns:

-   Claude API.
-   Prompt engineering.
-   Structured output.
-   Schema validation.
-   Extraction and verification.
-   AI error handling.

Primary modules:

``` text
ai/
validation/
```

## Technical Lead 2 --- Application/UI

Owns:

-   Streamlit.
-   Drawing ingestion.
-   Balloon rendering.
-   Review interface.
-   Excel generation integration.

Primary modules:

``` text
app.py
drawing/
as9102/
```

## Mechanical Expert

Owns:

-   Drawing interpretation.
-   GD&T validation.
-   Characteristic taxonomy.
-   Domain reference material.
-   AS9102 mapping review.
-   Demo validation.

The mechanical expert should continuously review outputs from the AI
rather than waiting until the end.

------------------------------------------------------------------------

# 12. Three-Hour Implementation Plan

## 0:00--0:20

All members:

-   Select one representative drawing.
-   Confirm the AS9102 template.
-   Define extraction schema.
-   Define the demo scenario.

## 0:20--1:15

Technical Lead 1:

-   Claude integration.
-   Prompt.
-   JSON schema.
-   Extraction.

Technical Lead 2:

-   Streamlit UI.
-   Drawing upload.
-   PDF rendering.

Mechanical Expert:

-   Engineering extraction checklist.
-   GD&T/reference guidance.
-   Validate initial AI results.

## 1:15--2:00

Integrate:

``` text
Claude JSON
     ↓
Balloon renderer
     ↓
Review UI
```

## 2:00--2:30

Implement:

``` text
Validated JSON
     ↓
AS9102 mapper
     ↓
Excel
```

## 2:30--2:50

Run domain validation and correct the highest-impact issues.

## 2:50--3:00

Freeze code and rehearse the demo.

------------------------------------------------------------------------

# 13. Security Considerations

For the MVP:

-   Keep API keys in environment variables.
-   Never commit secrets.
-   Avoid logging full engineering drawings.
-   Avoid unnecessary persistent storage.
-   Treat uploaded drawings as potentially confidential.
-   Do not send drawings to external services other than the
    intentionally configured AI provider.

Production deployment should add:

-   Authentication.
-   Authorization.
-   Encryption.
-   Audit logs.
-   Data-retention policy.
-   Approved-region/API configuration.
-   Enterprise access controls.

------------------------------------------------------------------------

# 14. Architectural Tradeoffs

## Claude Vision vs Custom Computer Vision

**MVP choice:** Claude.

Reason:

-   Fast implementation.
-   No training dataset required.
-   Strong contextual interpretation.
-   Can reason about symbols and surrounding drawing context.

A custom detector may be introduced later for deterministic balloon
detection and high-volume processing.

## Direct Excel Generation vs AI-Generated Excel

**MVP choice:** Deterministic Python Excel generation.

Reason:

-   Predictable.
-   Easier to validate.
-   Preserves template formatting.
-   Avoids generative changes to structured documents.

## Full RAG vs Prompt Reference

**MVP choice:** Small reference pack.

A full RAG system is unnecessary for a 3-hour prototype. A controlled
reference pack can be added to the AI request. A retrieval system can be
introduced later when standards/company procedures become larger and
need versioned retrieval.

------------------------------------------------------------------------

# 15. Future Architecture

A production system can evolve toward:

``` text
                    DRAWING
                       |
                       v
             ┌───────────────────┐
             │ Document Router   │
             └─────────┬─────────┘
                       v
             ┌───────────────────┐
             │ Vision Extraction │
             └─────────┬─────────┘
                       v
             ┌───────────────────┐
             │ Characteristic    │
             │ Knowledge Graph   │
             └─────────┬─────────┘
                       v
        ┌──────────────┼──────────────┐
        v              v              v
   Standards       Company Rules    Drawing
   Retrieval       Retrieval        Context
        \              |              /
         \             |             /
          └────────────┼────────────┘
                       v
              Validation Engine
                       |
                       v
                Human Approval
                       |
                       v
               AS9102 / QMS
```

The hackathon implementation should preserve these boundaries so that
future expansion does not require rewriting the core workflow.

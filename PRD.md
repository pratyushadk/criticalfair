# Product Requirements Document (PRD)

## AI Engineering Drawing to AS9102 Automation

**Document Status:** Hackathon MVP\
**Version:** 1.0\
**Date:** 2026-09-26

------------------------------------------------------------------------

## 1. Executive Summary

The AI Engineering Drawing to AS9102 Automation system is a
human-verifiable workflow that analyzes ballooned engineering drawings,
extracts the characteristics associated with each balloon, interprets
dimensions, tolerances, GD&T symbols, datums and relevant notes, and
maps the validated results into an AS9102-oriented Excel template.

The MVP uses Claude's vision/document capabilities for visual
interpretation and reasoning, while deterministic Python components
handle structured data validation, balloon visualization and Excel
generation.

The core product principle is:

> **AI interprets the drawing; deterministic software produces the
> documentation; humans verify ambiguous results.**

The MVP is intentionally narrow enough to demonstrate a complete
end-to-end workflow during a 3-hour hackathon while establishing an
architecture that can later evolve into a production-grade aerospace
quality workflow.

------------------------------------------------------------------------

## 2. Problem Statement

Engineering organizations routinely need to convert information
contained in engineering drawings into inspection and first-article
documentation. A typical workflow involves:

1.  Opening an engineering drawing.
2.  Reviewing ballooned characteristics.
3.  Finding the dimension, tolerance, GD&T callout, note or
    specification associated with each balloon.
4.  Interpreting engineering symbols.
5.  Manually transcribing the requirements.
6.  Mapping them to the appropriate AS9102 documentation fields.
7.  Checking the resulting document for transcription and interpretation
    errors.

This process is repetitive and can be time-consuming. It also creates
opportunities for transcription mistakes, missed characteristics,
incorrect associations and inconsistent documentation.

The product aims to automate the repetitive portion without removing
engineering accountability.

------------------------------------------------------------------------

## 3. Product Vision

Provide a trustworthy engineering-documentation copilot that can
transform:

**Engineering Drawing → Ballooned Characteristic Dataset → Human Review
→ AS9102 Documentation**

while maintaining a traceable link between every generated
characteristic and its source location on the drawing.

------------------------------------------------------------------------

## 4. Goals

### 4.1 MVP Goals

-   Accept a PDF or image engineering drawing.
-   Analyze the drawing using Claude.
-   Identify balloon numbers.
-   Associate balloons with relevant drawing characteristics.
-   Extract dimensions and tolerances.
-   Interpret common GD&T symbols and datum references.
-   Extract relevant drawing notes/specifications where applicable.
-   Produce structured JSON.
-   Assign confidence/status to extracted characteristics.
-   Generate a numbered balloon overlay on the drawing.
-   Provide a reviewable characteristic table.
-   Generate/populate a supplied AS9102 Excel template.
-   Preserve source traceability.

### 4.2 Quality Goals

-   Do not silently invent missing engineering requirements.
-   Flag ambiguous or low-confidence results.
-   Preserve exact source text where possible.
-   Separate AI interpretation from deterministic Excel generation.
-   Keep the original drawing available for visual verification.

------------------------------------------------------------------------

## 5. Non-Goals for MVP

The MVP will not attempt to:

-   Replace engineering or quality approval.
-   Certify conformity automatically.
-   Guarantee production-grade aerospace compliance.
-   Interpret every possible proprietary drafting convention.
-   Train a custom computer-vision model.
-   Perform full CAD/3D geometric reasoning.
-   Automatically determine inspection results or measured values.
-   Modify the original engineering drawing.
-   Recreate an AS9102 standard from memory.
-   Build a full enterprise document-management system.
-   Support every possible drawing format or legacy drafting convention.

------------------------------------------------------------------------

## 6. Target Users

### 6.1 Quality / FAI Engineer

Needs to convert drawing characteristics into inspection documentation
quickly and verify that the resulting records are correct.

### 6.2 Manufacturing / Mechanical Engineer

Needs confidence that dimensions, tolerances, GD&T, datums and notes
have been interpreted correctly.

### 6.3 Quality Reviewer

Needs traceability from a documented characteristic back to the source
drawing.

### 6.4 Engineering Documentation Team

Needs a repeatable way to generate standardized spreadsheet outputs from
drawings.

------------------------------------------------------------------------

## 7. Primary User Journey

### Step 1 --- Upload

User uploads an engineering drawing in PDF or supported image format.

### Step 2 --- Analyze

User selects **Analyze Drawing**.

### Step 3 --- AI Extraction

Claude analyzes the drawing and returns structured characteristics.

### Step 4 --- Visual Balloon Map

The application creates an annotated copy of the drawing showing the
recognized balloon numbers and their associated locations.

### Step 5 --- Review

The user reviews extracted characteristics and confidence/status
indicators.

### Step 6 --- Correct

The user can correct or approve characteristics flagged for review.

### Step 7 --- Generate

The user selects **Generate AS9102**.

### Step 8 --- Export

The application populates the supplied AS9102 Excel template.

### Step 9 --- Trace

Each output characteristic remains traceable to its balloon and source
drawing region.

------------------------------------------------------------------------

## 8. Core Product Features

  ID     Feature                          Priority
  ------ -------------------------------- ----------
  P-01   Drawing upload                   Must
  P-02   Claude visual analysis           Must
  P-03   Balloon identification           Must
  P-04   Characteristic extraction        Must
  P-05   Dimension/tolerance extraction   Must
  P-06   GD&T interpretation              Must
  P-07   Datum identification             Must
  P-08   Confidence/status                Must
  P-09   Balloon overlay                  Must
  P-10   Human review                     Must
  P-11   AS9102 Excel generation          Must
  P-12   Source traceability              Must
  P-13   Advanced multi-sheet support     Later
  P-14   Custom model training            Later
  P-15   CAD integration                  Later

------------------------------------------------------------------------

## 9. Product Principles

### 9.1 Traceability First

Every extracted requirement should have a source reference such as
balloon ID, page, bounding region and source text.

### 9.2 Human-in-the-Loop

The system should assist the engineer rather than silently making
high-impact decisions.

### 9.3 Structured AI

AI output must conform to a defined schema rather than free-form prose.

### 9.4 Deterministic Documentation

The Excel-generation layer should be deterministic and independent of
generative interpretation.

### 9.5 Fail Explicitly

If the system cannot confidently interpret a characteristic, it should
mark it for review rather than invent a value.

------------------------------------------------------------------------

## 10. Success Criteria

The hackathon MVP is successful when a user can:

1.  Upload one representative engineering drawing.
2.  Run analysis.
3.  See recognized balloons and extracted requirements.
4.  See confidence/status information.
5.  View a ballooned drawing.
6.  Review/correct extracted characteristics.
7.  Generate a populated AS9102 Excel workbook.
8.  Trace generated characteristics back to the source drawing.

------------------------------------------------------------------------

## 11. MVP Demonstration Scenario

The recommended demonstration should use one representative drawing
containing:

-   Several balloons.
-   Linear dimensions.
-   Diameter dimensions.
-   At least one tolerance.
-   At least one GD&T feature-control frame.
-   At least one datum.
-   At least one drawing note.

The demonstration should show the full workflow rather than many
drawings.

------------------------------------------------------------------------

## 12. Future Product Direction

Potential future capabilities include:

-   Multi-page drawings.
-   Drawing revision comparison.
-   Automatic characteristic completeness checks.
-   Advanced GD&T validation.
-   Company-specific drafting rules.
-   Controlled standards/reference libraries.
-   CAD/PLM integration.
-   Measurement-data ingestion.
-   Automated inspection-plan generation.
-   Reviewer audit trails.
-   Enterprise authentication and permissions.
-   Model evaluation datasets.
-   Specialized vision models for difficult drawings.

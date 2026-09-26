# Software Requirements Specification (SRS) --- Part 1

## AI Engineering Drawing to AS9102 Automation

**Version:** 1.0\
**Status:** Hackathon MVP\
**Date:** 2026-09-26

------------------------------------------------------------------------

# 1. Introduction

## 1.1 Purpose

This Software Requirements Specification defines the functional and
non-functional requirements for an AI-assisted system that reads
ballooned engineering drawings and produces structured characteristic
data suitable for populating an AS9102-oriented Excel template.

The system is designed as a human-verifiable automation tool. It is not
intended to replace engineering, manufacturing or quality approval.

## 1.2 Scope

The MVP covers:

-   Engineering drawing ingestion.
-   Visual analysis through Claude.
-   Balloon and characteristic identification.
-   Dimension/tolerance extraction.
-   Common GD&T and datum interpretation.
-   Structured characteristic output.
-   Confidence and validation.
-   Ballooned drawing visualization.
-   Human review.
-   AS9102 Excel template population.
-   Source traceability.

## 1.3 Definitions

**Balloon:** A numbered annotation used to identify a characteristic on
an engineering drawing.

**Characteristic:** A drawing requirement that may need to be
documented, such as a dimension, tolerance, GD&T requirement, material
requirement or note.

**GD&T:** Geometric Dimensioning and Tolerancing.

**Datum:** A reference used to establish a datum reference frame or
geometric relationship.

**Source Region:** The page and coordinate region of the drawing from
which an extracted characteristic originates.

**Confidence:** A system estimate of how reliably a characteristic was
interpreted.

**Review Required:** A status indicating that the characteristic should
be checked by a human before export.

------------------------------------------------------------------------

# 2. System Context

The system consists of five logical layers:

1.  User interface.
2.  Drawing/document ingestion.
3.  AI extraction and interpretation.
4.  Validation and review.
5.  Deterministic AS9102/Excel generation.

High-level flow:

``` text
User
 |
 v
Web UI
 |
 v
Drawing Ingestion
 |
 v
Claude Vision / Document Analysis
 |
 v
Structured Characteristic JSON
 |
 +--> Balloon Overlay Generator
 |
 +--> Validation / Review
 |
 v
AS9102 Mapping
 |
 v
Excel Generator
 |
 v
Output Workbook
```

------------------------------------------------------------------------

# 3. Actors

## 3.1 Primary User

A quality, manufacturing or engineering professional who uploads
drawings, reviews extraction and generates documentation.

## 3.2 Mechanical Domain Expert

Validates engineering interpretation, GD&T behavior, drafting
conventions and AS9102 mapping.

## 3.3 System Administrator

Out of MVP scope. Future versions may introduce administrative
configuration and user management.

## 3.4 Claude API

External AI service responsible for visual document interpretation and
structured extraction.

------------------------------------------------------------------------

# 4. Functional Requirements

## FR-001 --- Drawing Upload

**Description:** The system shall allow a user to upload a supported
engineering drawing.

**Inputs:** - PDF - Supported image format

**Acceptance Criteria:** - User can select a file. - Invalid file types
are rejected. - The uploaded drawing is available to the analysis
pipeline. - Original file content is not modified.

------------------------------------------------------------------------

## FR-002 --- Drawing Analysis

The system shall submit the drawing to Claude for visual/document
analysis.

**Acceptance Criteria:** - The system provides explicit analysis
instructions. - The system requests structured output. - API failures
are surfaced to the user. - The original drawing remains associated with
the analysis session.

------------------------------------------------------------------------

## FR-003 --- Balloon Identification

The system shall attempt to identify numbered balloons.

For each recognized balloon, the system should capture:

-   Balloon ID.
-   Page.
-   Approximate location.
-   Associated feature/region.
-   Confidence.

**Acceptance Criteria:** - Recognized balloons appear in the structured
output. - Uncertain balloons are marked for review. - No unsupported
balloon ID is invented.

------------------------------------------------------------------------

## FR-004 --- Characteristic Extraction

The system shall extract relevant information associated with each
balloon.

Possible characteristic categories include:

-   Linear dimension.
-   Angular dimension.
-   Diameter.
-   Radius.
-   Limit dimension.
-   Bilateral tolerance.
-   Unilateral tolerance.
-   GD&T requirement.
-   Datum/reference.
-   Surface finish.
-   Material/specification.
-   Drawing note.
-   Other explicitly identifiable requirements.

------------------------------------------------------------------------

## FR-005 --- Dimension Extraction

The system shall attempt to extract:

-   Nominal value.
-   Upper tolerance.
-   Lower tolerance.
-   Units.
-   Exact source text.

Example:

``` json
{
  "nominal": 25.0,
  "upper_tolerance": 0.05,
  "lower_tolerance": -0.05,
  "unit": "mm",
  "source_text": "25 ±0.05"
}
```

------------------------------------------------------------------------

## FR-006 --- GD&T Extraction

The system shall identify common GD&T constructs when visually
recognizable.

The extracted representation should distinguish:

-   Geometric characteristic.
-   Tolerance value.
-   Diameter modifier where applicable.
-   Material condition modifier where applicable.
-   Datum references.
-   Additional modifiers where confidently identified.

The system shall not infer a symbol that is not visually supported by
the drawing.

------------------------------------------------------------------------

## FR-007 --- Datum Extraction

The system shall identify datum references associated with a
characteristic where visually supported.

Example:

``` json
{
  "datums": ["A", "B", "C"]
}
```

------------------------------------------------------------------------

## FR-008 --- Source Preservation

The system shall preserve source information for each characteristic.

Minimum source fields:

-   Page.
-   Balloon ID.
-   Approximate bounding box.
-   Source text when available.
-   Source image/crop reference where implemented.

------------------------------------------------------------------------

## FR-009 --- Confidence

Each extracted characteristic shall contain a confidence/status field.

Recommended statuses:

-   `VERIFIED`
-   `REVIEW_REQUIRED`
-   `UNRESOLVED`

The confidence score is advisory and shall not be represented as a
formal engineering approval.

------------------------------------------------------------------------

## FR-010 --- Structured Output

AI output shall be validated against a predefined JSON schema before
downstream processing.

------------------------------------------------------------------------

## FR-011 --- Human Review

The UI shall allow the user to review extracted characteristics.

At minimum, the review table shall display:

-   Balloon ID.
-   Characteristic.
-   Requirement.
-   Confidence/status.

Where possible, the UI shall display the source drawing region.

------------------------------------------------------------------------

## FR-012 --- Characteristic Correction

A reviewer shall be able to correct an extracted field before final
export.

The corrected value shall become the value passed to the Excel
generator.

------------------------------------------------------------------------

## FR-013 --- Balloon Overlay

The system shall generate an annotated representation of the drawing
with numbered balloon markers.

The overlay shall not alter the original drawing.

------------------------------------------------------------------------

## FR-014 --- AS9102 Mapping

The system shall map validated characteristics to the fields required by
the supplied AS9102 template.

The supplied template is the source of truth for workbook structure. The
system shall not assume undocumented company-specific fields.

------------------------------------------------------------------------

## FR-015 --- Excel Generation

The system shall generate an Excel workbook from validated structured
data.

Requirements:

-   Preserve template formatting where practical.
-   Populate appropriate rows/cells.
-   Avoid modifying unrelated template content.
-   Provide the generated workbook as an output artifact.

------------------------------------------------------------------------

## FR-016 --- Traceability

Every generated characteristic should be traceable to:

``` text
Excel row
   ↓
Characteristic ID
   ↓
Balloon ID
   ↓
Drawing page/region
   ↓
Original drawing
```

------------------------------------------------------------------------

# 5. Error Handling

The system shall explicitly handle:

-   Invalid file.
-   Unsupported file.
-   Empty drawing.
-   Unreadable drawing.
-   Claude API failure.
-   Claude response parsing failure.
-   Missing balloon association.
-   Ambiguous characteristic.
-   Invalid structured data.
-   Excel generation failure.

Errors shall not result in silent data creation.

------------------------------------------------------------------------

# 6. AI Guardrails

The AI shall be instructed to:

1.  Use only information visually supported by the drawing and supplied
    references.
2.  Avoid inventing values.
3.  Preserve exact source text when uncertain.
4.  Distinguish visual recognition from interpretation.
5.  Flag ambiguity.
6.  Return structured output.
7.  Identify missing information explicitly.
8.  Never represent a model confidence score as engineering approval.

------------------------------------------------------------------------

# 7. Data Quality Rules

Before a characteristic reaches Excel generation:

-   Required fields must pass schema validation.
-   Balloon ID must be present where applicable.
-   Requirement text must be non-empty.
-   Numerical values must be parseable where represented numerically.
-   Units must be explicit or marked unknown.
-   Ambiguous values must be flagged.
-   Reviewer corrections must be recorded in the session state.

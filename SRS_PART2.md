# Software Requirements Specification (SRS) --- Part 2

## AI Engineering Drawing to AS9102 Automation

**Version:** 1.0\
**Status:** Hackathon MVP\
**Date:** 2026-09-26

------------------------------------------------------------------------

# 8. Non-Functional Requirements

## NFR-001 --- Usability

A first-time user should be able to:

1.  Upload a drawing.
2.  Start analysis.
3.  Review characteristics.
4.  Generate the workbook.

The MVP should minimize configuration.

## NFR-002 --- Performance

For a representative single-page drawing, the system should provide an
interactive result within a practical hackathon-demo timeframe.

The exact response time will depend on drawing complexity, API latency
and network conditions.

## NFR-003 --- Reliability

The application shall fail explicitly when analysis or output generation
cannot be completed.

## NFR-004 --- Traceability

AI-generated values shall remain associated with their source drawing
information throughout the workflow.

## NFR-005 --- Security

The MVP shall avoid unnecessary persistence of engineering drawings.

API credentials shall be stored outside source code.

## NFR-006 --- Maintainability

The system should separate:

-   AI extraction.
-   Validation.
-   Visualization.
-   AS9102 mapping.
-   Excel generation.

## NFR-007 --- Determinism

Excel generation shall be deterministic given the same validated input
and template.

## NFR-008 --- Observability

The system should record sufficient application-level logs to diagnose:

-   Upload failures.
-   API failures.
-   Parsing failures.
-   Validation failures.
-   Export failures.

Sensitive drawing content should not be written to logs unnecessarily.

------------------------------------------------------------------------

# 9. AI-Specific Requirements

## 9.1 Visual Interpretation

The AI shall be given the drawing visually rather than relying
exclusively on OCR.

Engineering symbols shall be interpreted in visual context.

## 9.2 Reference Material

The system may provide:

-   Applicable drafting references.
-   GD&T symbol reference.
-   AS9102 field guidance.
-   Approved examples.
-   Company-specific instructions.

For the MVP, these can be provided as prompt/reference material rather
than a full retrieval system.

## 9.3 Structured Output

The model shall return data matching the application's schema.

Illustrative schema:

``` json
{
  "drawing": {
    "file_name": "example.pdf"
  },
  "characteristics": [
    {
      "balloon_id": "12",
      "type": "diameter",
      "requirement": "Ø25 ±0.05 mm",
      "nominal": 25.0,
      "upper_tolerance": 0.05,
      "lower_tolerance": -0.05,
      "unit": "mm",
      "gdt": null,
      "datums": [],
      "page": 1,
      "bbox": [1200, 800, 1300, 900],
      "source_text": "Ø25 ±0.05",
      "confidence": 0.97,
      "status": "VERIFIED"
    }
  ]
}
```

The production schema may be extended without changing the conceptual
model.

------------------------------------------------------------------------

# 10. Validation Strategy

The MVP should use a two-stage approach.

## Stage A --- Extraction

Claude analyzes the drawing and creates structured characteristics.

## Stage B --- Verification

A second AI pass and/or deterministic checks review the extracted result
against the drawing and identify:

-   Missing values.
-   Suspicious values.
-   Inconsistent tolerance formats.
-   Unclear balloon associations.
-   Unsupported inference.
-   Possible GD&T interpretation errors.

The system then assigns a review status.

------------------------------------------------------------------------

# 11. Balloon Rendering Requirements

The balloon renderer shall:

-   Use the original drawing as its visual base.
-   Add numbered markers.
-   Use source coordinates from the extraction layer.
-   Preserve drawing content.
-   Produce a separate output image/PDF.
-   Avoid claiming geometric accuracy beyond the precision of the
    extracted coordinates.

For the hackathon, approximate placement is acceptable if it clearly
identifies the associated feature.

------------------------------------------------------------------------

# 12. Excel Requirements

The Excel generator shall:

1.  Load the supplied template.
2.  Identify the intended data-entry region.
3.  Populate validated characteristics.
4.  Preserve existing workbook formatting where practical.
5.  Save a new output workbook.
6.  Avoid overwriting the source template.
7.  Report export errors.

The template shall be treated as the authoritative layout for the MVP.

------------------------------------------------------------------------

# 13. Interface Requirements

## 13.1 User Interface

The UI should provide:

-   Upload control.
-   Analyze button.
-   Processing status.
-   Annotated drawing.
-   Characteristic table.
-   Review indicators.
-   Edit/approve controls.
-   Generate Excel button.
-   Download/output link.

## 13.2 Claude API Interface

The AI adapter shall isolate Claude-specific API calls from the rest of
the application.

This allows a future model provider to be substituted without rewriting
the application.

## 13.3 File Interface

Inputs:

-   PDF/image.

Outputs:

-   Structured JSON.
-   Annotated drawing.
-   AS9102 Excel workbook.

------------------------------------------------------------------------

# 14. Testing Requirements

## 14.1 Unit Tests

Test:

-   JSON schema validation.
-   Tolerance parsing.
-   Characteristic normalization.
-   Confidence/status rules.
-   Excel cell mapping.
-   Balloon rendering.

## 14.2 Integration Tests

Test:

``` text
Drawing
→ Claude
→ JSON
→ Validation
→ Balloon overlay
→ Excel
```

## 14.3 Domain Validation

The mechanical expert shall verify representative results, particularly:

-   Balloon-to-feature association.
-   Dimensions.
-   Tolerances.
-   GD&T.
-   Datum references.
-   Units.
-   AS9102 mapping.

## 14.4 Negative Tests

Include examples containing:

-   Blurry text.
-   Overlapping annotations.
-   Unclear balloon leader.
-   Missing tolerance.
-   Unrecognized symbol.
-   Ambiguous association.

Expected behavior is to flag the issue rather than invent an answer.

------------------------------------------------------------------------

# 15. Acceptance Criteria

The MVP is accepted when:

### AC-01

A supported drawing can be uploaded.

### AC-02

The system identifies a representative set of balloons.

### AC-03

The system extracts associated requirements into structured data.

### AC-04

The system identifies common dimensions/tolerances and at least one
representative GD&T requirement in the demonstration drawing.

### AC-05

A balloon overlay is generated.

### AC-06

The UI displays confidence/status.

### AC-07

A human can review or correct extracted values.

### AC-08

Validated data populates the supplied AS9102 Excel template.

### AC-09

The output remains traceable to the source drawing.

### AC-10

The system does not silently invent unresolved values.

------------------------------------------------------------------------

# 16. Known Limitations

The hackathon MVP may have limitations around:

-   Very low-resolution scans.
-   Hand-drawn or heavily degraded drawings.
-   Complex multi-page relationships.
-   Extremely dense drawings.
-   Non-standard company drafting conventions.
-   Rare GD&T modifiers.
-   Legacy standards.
-   Exact geometric leader-line interpretation.
-   Automatic determination of whether every drawing annotation is an
    AS9102 characteristic.

These limitations should be disclosed rather than hidden.

------------------------------------------------------------------------

# 17. Future Requirements

Potential future versions may add:

-   Multi-sheet drawing intelligence.
-   Drawing revision comparison.
-   Controlled standards retrieval.
-   Company-specific knowledge base.
-   Automated characteristic completeness checks.
-   Advanced GD&T semantic validation.
-   CAD model comparison.
-   PLM/MES/QMS integrations.
-   User authentication.
-   Audit history.
-   Role-based approvals.
-   Enterprise data retention controls.
-   Evaluation datasets and automated regression testing.

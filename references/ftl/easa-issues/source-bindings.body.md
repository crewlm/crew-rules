## Purpose and source edition

This issue concerns a vendor-neutral, machine-readable description of crew rules and their meaning. Execution belongs to an external engine. Acceptance does not require an evaluator, roster ingestion, derived-fact computation, or implementation-specific algorithms.

Source: EASA Easy Access Rules for Air Operations, Revision 24, March 2026. The repository preserves the official PDF/XML and verbatim excerpts in `references/ftl/easa-issues/sources.json`. [Publisher publication page](https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-air-operations). ORO, CS, AMC and GM retain their distinct statuses; scheme applicability and operator interpretations must remain identifiable.

## Source text

### ORO.FTL.235(b) — regulatory requirement

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
(b)   Minimum rest period away from home base.
      The minimum rest period provided before undertaking an FDP starting away from home base
      shall be at least as long as the preceding duty period, or 10 hours, whichever is greater. This
      period shall include an 8-hour sleep opportunity in addition to the time for travelling and
      physiological needs.
```

### AMC1 ORO.FTL.235(b) — acceptable means of compliance

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
AMC1 ORO.FTL.235(b) Rest periods

MINIMUM REST PERIOD AWAY FROM HOME BASE
The time allowed for physiological needs should be 1 hour. Consequently, if the travelling time to the
suitable accommodation is more than 30 minutes, the operator should increase the rest period by
twice the amount of difference of travelling time above 30 minutes.
```

## Existing supported documentation

The repository already retains official documents, verbatim quotations, citations and edition information in its source bundle. Family-level example metadata carries sources. This issue does not claim that provenance is absent from the repository.

## Minimal documentary counterexample

An away-rest document combines the regulatory ten-hour/preceding-duty minimum and eight-hour sleep opportunity with AMC physiological/travel guidance and a selected operator interpretation of how the allowance interacts with a longer preceding duty. A family-wide citation list does not identify which particular requirement or update comes from ORO, which expresses AMC, and which is the operator interpretation.

The distinction matters even if the numerical expressions themselves are fully representable. A downstream reader must be able to recover the interpretation's status and dependencies from the structured artifact rather than guess from the order of source notes.

## Genuinely missing representation

Structured bindings from individual rules, shared definitions, table rows, updates and relationship/obligation objects to identified source versions/provisions and separate interpretation records. Bindings should retain source status and allow many-to-many attribution. An interpretation is not the original source and must not overwrite it.

Evidence: the fields of `Rule`, `Projection`, `DecisionTable` and `ConditionValue` have no source/interpretation bindings. The current family-level source arrays and the verbatim source bundle are useful inputs to this extension, not a substitute for element-level binding.

## Schema acceptance criteria

- [ ] Bind the away-rest minimum and sleep-opportunity requirement to ORO.FTL.235(b), and physiological/travel guidance to AMC1 ORO.FTL.235(b), preserving their different statuses.
- [ ] Represent a selected operator interpretation as a separate identified record linked to the source provisions and model elements it explains.
- [ ] Support one source provision informing several elements and one element depending on several sources or interpretations.
- [ ] Retain source edition, provision locator, document identity/link and relevant excerpt or excerpt reference through serialization.
- [ ] Allow bindings on shared definitions, rules, rows/updates and relationships or qualitative obligations, using a consistent approach.
- [ ] Reuse the existing preserved source bundle; do not require a new source acquisition workflow or executable regulatory assessment.

Affected examples: all ten families. This is provenance inside the documentary model, not merely additional README notes.

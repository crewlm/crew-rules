## Purpose and source edition

This issue concerns a vendor-neutral, machine-readable description of crew rules and their meaning. Execution belongs to an external engine. Acceptance does not require an evaluator, roster ingestion, derived-fact computation, or implementation-specific algorithms.

Source: EASA Easy Access Rules for Air Operations, Revision 24, March 2026. The repository preserves the official PDF/XML and verbatim excerpts in `references/ftl/easa-issues/sources.json`. [Publisher publication page](https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-air-operations). ORO, CS, AMC and GM retain their distinct statuses; scheme applicability and operator interpretations must remain identifiable.

## Source text

### ORO.FTL.235(a), (b) — regulatory requirement and derogation dependency

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
(a)   Minimum rest period at home base.
      (1)    The minimum rest period provided before undertaking an FDP starting at home base shall
             be at least as long as the preceding duty period, or 12 hours, whichever is greater.
      (2)    By way of derogation from point (1), the minimum rest provided under point (b) applies
             if the operator provides suitable accommodation to the crew member at home base.
(b)   Minimum rest period away from home base.
      The minimum rest period provided before undertaking an FDP starting away from home base
      shall be at least as long as the preceding duty period, or 10 hours, whichever is greater. This
      period shall include an 8-hour sleep opportunity in addition to the time for travelling and
      physiological needs.
```

### ORO.FTL.205(d)(4) — combination prohibition

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
(4)     Extension of the maximum basic daily FDP without in-flight rest shall not be combined
              with extensions due to in-flight rest or split duty in the same duty period.
```

### CS FTL.1.220(f) — combination prohibition

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
(f)   Split duty cannot be combined with in-flight rest.
```

## Existing supported encoding

Decision-table conditions can select the home-base accommodation derogation. They can also reject simultaneous claims of split-duty and in-flight-rest extensions. Numeric Boolean checks and finite alternatives are expressible today. This issue is not a request for missing equality, conjunction or OR behavior.

## Minimal documentary counterexample

An augmented FDP cap, sector restriction and minimum-rest restriction can all be serialized as valid independent rules. Their IDs do not state that they jointly govern one extension permission. An opaque `augmentation_eligibility_pass` input names the outcome but conceals the prerequisite graph.

Likewise, home-rest and away-rest rules can duplicate the correct branch logic without representing the source's explicit relationship: point (a)(2) derogates from (a)(1) by applying point (b). A pair of rule names and a source citation is not that machine-readable relationship.

## Genuinely missing representation

Explicit relationships or groups that identify jointly required provisions, prerequisites for permissions or dependent caps, conditional substitution/derogation, and incompatible extensions. Relationships must identify their subjects and conditions, such as the same duty period or the relevant employee rest interval.

Evidence: `models/rule.py` provides stable rule IDs, applicability, values and bounds, but no references to other rules, group semantics or regulatory relationship fields. Existing `EmployeeRestTime` preceding/succeeding-duty links are useful domain relationships; they do not supply rule-to-rule dependency edges.

## Schema acceptance criteria

- [ ] Serialize an augmentation permission/group referring to its identified cap, sector, individual-rest and eligibility provisions, with their joint meaning explicit.
- [ ] Serialize the home-rest derogation as a conditional relationship to the identified away-rest provision and the shared suitable-accommodation definition.
- [ ] Identify the same-duty incompatibility between split duty, in-flight-rest extension and the relevant planned extension without in-flight rest.
- [ ] Express the relationship between a basic-FDP domain restriction and its dependent cap without relying on example prose or an implicit list convention.
- [ ] Preserve graph references and their conditions through serialization, with human-readable labels and source bindings.
- [ ] Keep the distinction between a condition being false and a provision being inapplicable in the documented relationship semantics; no runtime result orchestration is required.

Affected examples: basic FDP, home/away rest, split duty, standby and augmentation. The requested artifact is a dependency graph with declared meaning, not code that evaluates the group.

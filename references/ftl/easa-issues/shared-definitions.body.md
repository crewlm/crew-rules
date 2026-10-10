## Purpose and source edition

This issue concerns a vendor-neutral, machine-readable description of crew rules and their meaning. Execution belongs to an external engine. Acceptance does not require an evaluator, roster ingestion, derived-fact computation, or implementation-specific algorithms.

Source: EASA Easy Access Rules for Air Operations, Revision 24, March 2026. The repository preserves the official PDF/XML and verbatim excerpts in `references/ftl/easa-issues/sources.json`. [Publisher publication page](https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-air-operations). ORO, CS, AMC and GM retain their distinct statuses; scheme applicability and operator interpretations must remain identifiable.

## Source text

### ORO.FTL.105 definitions (21, 14, 4, 11)

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
(21) ‘rest period’ means a continuous, uninterrupted and defined period of time, following duty or
     prior to duty, during which a crew member is free of all duties, standby and reserve.

(14) ‘home base’ means the location, assigned by the operator to the crew member, from where the
     crew member normally starts and ends a duty period or a series of duty periods and where,

      under normal circumstances, the operator is not responsible for the accommodation of the
      crew member concerned;

(4)   ‘suitable accommodation’ means, for the purpose of standby, split duty and rest, a separate
      room for each crew member located in a quiet environment and equipped with a bed, which is
      sufficiently ventilated, has a device for regulating temperature and light intensity, and access to
      food and drink;

(11) ‘duty period’ means a period which starts when a crew member is required by an operator to
     report for or to commence a duty and ends when that person is free of all duties, including post-flight duty;
```

## Existing supported encoding

`Condition.field` and `FieldValue.field` accept symbolic paths. Decision tables can express conjunctions such as the components of suitable accommodation, and values/updates already describe differences, scaling, offsets and min/max. Such symbols need not have Python properties. `Projection` already has an ID/code and `ProjectedValue` references that code. `TableLookupValue` names a table and maps parameters. These are useful precedents, not absent capabilities.

## Minimal documentary counterexample

Home-rest derogation and split duty both refer to `suitable_accommodation`. Each rule can contain a valid condition on that symbol, or duplicate its component conditions. Neither choice binds both uses to one identified definition carrying the criteria in ORO.FTL.105(4). A reviewer cannot follow a schema reference from both consumers to the same typed definition, or distinguish two similarly named interpretations.

The same problem occurs when FDP, split-duty WOCL and recovery-rest provisions refer to an individual's acclimatisation or local-time definition. Existing family-level prose input descriptions are useful documentation but do not establish a validated graph.

## Genuinely missing representation

A general shared-definition object with stable identity, declared subject/scope, typed inputs and result, dimensional units where relevant, and a structured definition body; plus references binding consumers to it. Include explicit relationship definitions when a concept depends on associations, such as an operating assignment connecting a crew member to a sector, or a facility associated with an individual rest allocation.

Evidence: `models/decision_table/condition.py` declares `field: str`; `models/decision_table/value.py` does the same for field values and carries named lookup references without a corresponding named-definition model. `models/rule.py` embeds tables; `models/projection.py` supplies the existing narrower reusable-object pattern. The absence of a runtime entity property or conversion implementation is not the problem.

## Schema acceptance criteria

- [ ] Serialize one identified suitable-accommodation definition with source-linked criteria, subject scope and declared Boolean result, and reference it from both a home-rest derogation and a split-duty provision.
- [ ] Preserve definition identity and references through serialization; give unresolved or conflicting references an explicit documentary status.
- [ ] Describe primitive external inputs separately from derived concepts; a field-name string must not silently claim to include an unstated definition.
- [ ] Represent person-sector-role and person-rest-facility associations as explicit shared concepts or declared relationships, without requiring a roster storage implementation.
- [ ] Allow business quantities to declare types and units independently of Python representation; this criterion does not concern runtime unit conversion.
- [ ] Retain and reuse the existing projection-reference and decision-table capabilities where sufficient.

Affected examples: all ten families. This issue supplies reusable vocabulary and definition bindings; temporal definition operators and normative rule relationships are tracked separately.

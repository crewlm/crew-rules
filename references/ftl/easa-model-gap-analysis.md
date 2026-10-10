# EASA FTL documentary schema assessment

The existing schema can describe the principal numerical rules and conditional adjustments in all ten families assessed here. It already provides symbolic field references, decision tables, period descriptors, projections and conditional arithmetic. A missing evaluator, Python property, roster dataset or calculation algorithm is not a limitation of its ability to document a rule.

The remaining work is to preserve the complete meaning of definitions and their relationships in a shared, machine-readable document. Five extensions are justified: shared typed definitions and references; explicit relationships between rules; temporal and collection definitions; source/interpretation bindings; and qualitative or procedural obligations. These are cross-cutting capabilities, not ten separate family-specific implementations.

## Purpose, scope and evidence

This assessment follows the [concept note](../../concept-note.md): an open, vendor-neutral description of crew rules, their meaning and relationships, between source material and system-specific implementation. Execution belongs to an external engine. The question is whether a reviewer or downstream system can recover the documented meaning, including shared definitions and joint dependencies, from valid structured content.

Assessment date: 8 October 2026. The source edition is the preserved official [EASA Easy Access Rules for Air Operations, Revision 24, March 2026](easa-air-operations-rev24-2026-03.pdf), particularly pages 854–886. Page references use the one-based PDF viewer numbering, matching printed pages. The [source record](README.md), [publisher page](https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-air-operations) and [verbatim source bundle](easa-issues/sources.json) identify the material. This is an assessment of that edition, not a claim about subsequent amendments or a complete compliance ruleset.

ORO.FTL requirements, CS specifications, AMC and GM have different regulatory roles. Applicable schemes and operator choices also matter. ORO.FTL.125 concerns approved flight time specification schemes; CS FTL.1.100 scopes the specifications to the relevant scheduled and charter aeroplane operations. Retaining those distinctions is part of documentation, not a requirement to automate regulatory interpretation.

The reviewed core files are [rules](../../models/rule.py), [values](../../models/decision_table/value.py), [conditions](../../models/decision_table/condition.py), [decision tables](../../models/decision_table/decision_table.py), [comparisons](../../models/comparison.py), [updates](../../models/update.py), [projections](../../models/projection.py), [time periods](../../models/time_period.py) and [entities](../../models/entity.py). The [ten examples](../../examples/easa_ftl/README.md) demonstrate valid schema fragments. A fragment's coverage is distinct from the schema's capability: an omitted applicability branch is not evidence that applicability is inexpressible.

## What the existing schema already describes

A `Rule` carries applicability, a measured value, a minimum and/or maximum, and conditional updates. `Condition.field` and `FieldValue.field` accept symbolic dot paths. Those names can describe business quantities supplied by another system; they need not correspond to an existing Python property to be legitimate documentary inputs.

Decision-table rows combine conditions with AND, provide ordered alternatives and have a default. Finite alternatives can be expanded into rows; a dedicated OR node is not required for overnight start bands or ordinary eligibility conditions. Numeric encodings of Boolean checks are possible. They should not be confused with a complete definition of an opaque eligibility flag.

`FieldValue` and `FieldDifferenceValue` express scaling, offsets, differences and clamps. Updates express set, increase, decrease, maximum, minimum and scale. Consequently, `max(preceding duty, 12 hours)`, half-break credits and reductions beyond a threshold already have suitable structures.

`Projection` is a shared object with an ID and reference code. `ProjectedValue` refers to that code, and interval descriptions contain anchors, fields, offsets, rates and clamps. `TimePeriod` includes day, month and year vocabulary. In particular, an `EmployeeTimePeriodRule` with `TimePeriod(anchor="year", unit="year", duration=1)`, an operating-flight `ProjectedValue`, and a 900-hour limit represents the calendar-year ceiling. Calendar-window resolution is an engine responsibility; absence of that algorithm does not invalidate the declaration.

Existing relationships also matter: `EmployeeRestTime` relates the employee to preceding and succeeding duties, and `EmployeeGroundTime` relates the employee to inbound and outbound activities. Collection helpers provide mapping, count, first/last, extrema and flattening. These capabilities should be extended where necessary, not rediscovered as missing features.

A named quantity can therefore make a rule shell complete while leaving the quantity's definition undocumented. For example, `minimum_landing_crew_uninterrupted_rest_hours >= 2` expresses the restriction, but its name alone does not define landing-role selection, per-person association or continuity. The assessment below distinguishes those two levels.

## Ten-family assessment

### 1. Cumulative duty

**Sources:** ORO.FTL.210(a), (c), page 869; ORO.FTL.105(10)–(11), page 855; ORO.FTL.225(c), page 870; CS FTL.1.225(b)(3), page 883.

The source limits assigned duty to 60 hours in seven consecutive days, 110 in fourteen and 190 in twenty-eight. Three employee-period rules, duty projections and limits describe those restrictions. Full airport-standby credit and quarter-credit for other standby can be represented with conditions and rates. No aggregation implementation is required in this repository to document that meaning.

What needs a shared definition is the duty quantity used by several provisions, including report/release endpoints, post-flight duty and purpose-specific accounting. Rules should reference that definition instead of relying on repeated prose or similarly named fields. Boundary attribution or overlap conventions, where a scheme needs them, should be recorded as explicit interpretations rather than silently assumed.

The phrase “spread as evenly as practicable” is an additional qualitative obligation. Preserve its wording, responsible operator and any adopted interpretation; the 190-hour cap does not represent it. A numerical balancing measure must not be invented to claim complete coverage.

### 2. Cumulative operating flight time

**Sources:** ORO.FTL.210(b), page 869; ORO.FTL.105(13), (17), pages 855–856; GM1 ORO.FTL.105(17), page 858.

The schema describes 100 hours in twenty-eight consecutive days, 900 in a calendar year and 1,000 in twelve consecutive calendar months using operating-flight projections, period descriptors and limits. A calendar year is directly representable; a trailing twelve-month declaration is also distinct from a fixed number of days.

The documentary extension is a reusable definition of operating flight time for an individual, connected to person-sector role and block-time definitions. GM explains that in-flight rest retains operating status and counts for ORO.FTL.210. A shared relationship makes that connection visible to both cumulative-time and augmentation models. Missing employee assignment data or block-time extraction code is not itself a schema defect.

### 3. Basic maximum daily FDP

**Sources:** ORO.FTL.205(b), pages 865–866; ORO.FTL.105(1), (2), (12), pages 854–855; associated GM, pages 856–857.

All finite rows of Tables 2–4 are expressible through decision tables, reference-start and sector conditions, and updates. Unknown-state FRM eligibility is also expressible. The acclimatisation table's finite mapping can itself be documented using table structure; it does not require an engine to exist here.

The unresolved meaning lies in shared definitions and historical relationships: reference time, elapsed time since the relevant report, state persistence during a rotation, and the individual's last operating endpoint. A supplied acclimatisation symbol is valid, but does not itself document those dependencies. Where an example separates supported-domain checks from the cap, the document should explicitly state their joint relationship. A reader should not have to infer from prose that the cap is meaningful only within the other rule's domain.

### 4. Positioning accounting

**Sources:** ORO.FTL.215, page 870; ORO.FTL.105(18), page 856.

“All time spent on positioning counts as duty period.” Positioning after report and before operating counts as FDP but not as a sector. Projections, conditional categorisation, symbolic endpoints and a zero sector contribution already describe these effects. A report-to-last-operating interval naturally includes intervening positioning; a contrived subtraction and add-back is unnecessary.

The complete shared definition must distinguish positioning from excluded ordinary/local travel and connect timing and operating role to the same crew member. A symbolic “pre-operating positioning” input remains legitimate. The documentary gap is a structured, reusable definition of that relationship, not an inability to add positioning time or a demand to implement chronological sorting.

### 5. Minimum rest at home base

**Sources:** ORO.FTL.235(a), page 871; ORO.FTL.105(21), (14), (4), pages 855–856; GM1 ORO.FTL.235(a)(2), page 872.

The ordinary rule is rest of at least the greater of preceding full duty and twelve hours. `EmployeeRestTimeRule`, a symbolic rest duration, and a clamp or maximum update suffice. Applicability can describe the succeeding FDP starting at home base; absent home-base fields in Python do not prevent that declaration.

The accommodation derogation is likewise expressible as conditional selection of the away-rest provision. What is missing is an explicit reference connecting that substitution to the identified away-rest rule and to the shared definition of suitable accommodation. Qualifying uninterrupted rest and crew-specific home-base assignment also need reusable definitions if the complete meaning is to travel with the rule.

### 6. Minimum rest away from home base

**Sources:** ORO.FTL.235(b), page 871; AMC1 ORO.FTL.235(b), page 872; ORO.FTL.105(21), page 856.

The greater of preceding duty and ten hours, plus an independent eight-hour sleep-opportunity requirement, fits existing rule structures. Travel-related adjustments selected under an operator interpretation can be described with the existing arithmetic. Neither a new maximum operator nor prepared-fact validation is needed to establish expressiveness.

Full documentation should identify the protected sleep interval, travel/physiological allowances and their relationship to qualifying rest. AMC's one-hour physiological allowance and travel guidance must remain distinguishable from the regulatory text and any operator interpretation of their interaction with a longer preceding duty. Continuity and interval definitions belong in shared temporal descriptions; calculating actual intervals belongs elsewhere.

### 7. Recurrent extended recovery rest

**Sources:** ORO.FTL.235(d), (e), page 872; ORO.FTL.105(15), (16), (21), page 856; CS FTL.1.235(a), page 885.

Duration thresholds of 36 or 60 hours, two local nights, a maximum 168-hour gap and two qualifying two-local-day rests per month are all expressible with named quantities. Conditions also express the four-disruptive-duty trigger.

This family particularly exposes missing definitional structure: selecting the preceding qualifying rest, counting specified duties between qualifying rests, containing separate local-night occurrences, and associating rests with a month. A 36-hour interval from 02:00 on day one to 14:00 on day two overlaps the 22:00–08:00 windows for sixteen hours in total, but only one occurrence contains eight hours. Total overlap cannot substitute for a count of separately qualifying nights. A named count solves the shell; documenting that count needs a richer temporal/collection definition.

### 8. Split duty

**Sources:** ORO.FTL.220, page 870; CS FTL.1.220, page 882; ORO.FTL.205(d)(4), page 867; ORO.FTL.105 definitions, pages 854–856.

The three-hour continuous break minimum, duty/travel exclusion allowance, half-break extension, facility conditions, reduced-rest restriction and prohibited combinations all fit existing conditions and arithmetic. The full FDP can remain the measured value, retaining the break as the source requires. A new Boolean language is not necessary.

The complete description needs a shared continuous-break definition and an eligible-credit definition relating exclusions, accommodation and WOCL. “Suitable accommodation” and WOCL are reused across families. The extension's joint prerequisites and incompatibility with in-flight rest should also be explicit relationships between identified provisions. A single `eligible` flag would conceal these definitions even though it is syntactically a valid input.

### 9. Standby accounting and FDP impact

**Sources:** ORO.FTL.225, pages 870–871; CS FTL.1.225, pages 882–883; associated GM, pages 883–884.

Full versus quarter duty credit, four/six/eight-hour reduction thresholds and the correctly scoped sixteen-hour ceilings are expressible. Separate projections can describe different accounting purposes. The existing `home_standby` enum need not be treated as a barrier to a symbolic classification covering all other standby.

Definitions should describe the link to the assigned FDP and the overnight interval excluded until operator contact. The 23:00–07:00 rule concerns a selected interval bounded by a related event; a named effective-duration input alone omits that relationship.

The source also requires advance notification, accommodation and operator procedures designed to avoid more than eighteen hours awake. Those procedural obligations must remain visible with their actors and regulatory status. An individual numerical awake-time check is an illustrative condition, not a complete representation of the operator-procedure obligation.

### 10. Augmentation and in-flight rest

**Sources:** ORO.FTL.205(e), page 867; CS FTL.1.205(c), pages 876–877; ORO.FTL.105(5), (17), (19), pages 855–856; combination restrictions and GM in the source bundle.

The six class/extra-crew caps, three-sector ceiling, strictly greater-than-nine-hour adjustment, cabin-rest matrix, ninety-minute/two-hour requirements and `max(preceding duty, 14 hours)` destination rest are expressible. Extension incompatibilities are expressible as conditions.

The complete definition must connect each crew member to operating/landing role, their rest intervals, facility class and appropriately qualified relief. Two separate one-hour rests do not describe one consecutive two-hour rest. A mixed facility-class cabin group also requires preserving which class and corresponding rest requirement belongs to each person. Collection minima can help once those associations and quantities are defined; a new quantifier should not be presumed necessary. The actual gap is the shared relational/temporal definition and the joint extension-permission graph, not a missing cap table.

## Five cohesive schema extensions

The remaining work is tracked in five source-backed GitHub issues. Earlier family issues #1–#10 are closed as superseded, with corrected assessments and replacement links.

- [#11 — Shared typed definitions and stable references](https://github.com/crewlm/crew-rules/issues/11)
- [#12 — Joint rule groups, prerequisites and derogation relationships](https://github.com/crewlm/crew-rules/issues/12)
- [#13 — Temporal and collection definitions](https://github.com/crewlm/crew-rules/issues/13)
- [#14 — Source and interpretation bindings](https://github.com/crewlm/crew-rules/issues/14)
- [#15 — Qualitative and procedural obligations](https://github.com/crewlm/crew-rules/issues/15)

### Shared definitions and references

Provide identified definitions with declared inputs, result type/unit, subject scope and a structured definition body. Bind symbolic references to those definitions. Include relationship definitions where needed, such as person-sector role and rest-facility allocation. Build on existing projection references and table-lookup names.

For example, ORO.FTL.105(4)'s “separate room for each crew member” is part of suitable accommodation used by several families. Repeating conditions or using the same string does not establish a single shared definition whose consumers can be found. Types and units here document meaning; this is not a request to repair numeric conversions in Python.

### Rule relationships and joint obligations

Describe groups, prerequisites, derogations, substitutions and incompatible permissions through stable references. ORO.FTL.235(a)(2) explicitly says “By way of derogation from point (1)” and points to point (b). CS FTL.1.220(f) says “Split duty cannot be combined with in-flight rest.” Existing Boolean conditions express the restrictions, but the model has no corresponding first-class graph edges.

These relationships connect normative nodes; they do not by themselves supply a representation for qualitative or procedural obligations. Those require the additional normative form described below.

### Temporal and collection definitions

Add declarative ways to describe selected/qualifying intervals, adjacency, containment, continuity, occurrence counts and person-correlated collections. Reuse anchors, projections, overlap comparisons and existing collection operations where sufficient. The recovery-rest local-night counterexample and augmentation continuity example are concrete acceptance cases. Historical acclimatisation and standby contact exclusions are further consumers. The artifact must preserve meaning; implementing interval processing is outside this task.

### Source and interpretation bindings

The source bundle already preserves quotations and family citations. Extend the model to bind source edition, provision, status and interpretation records to individual rules, definitions, rows or updates. A family-wide source list cannot identify which away-rest element comes from ORO, which from AMC and which records an operator interpretation. Bindings should survive serialization and permit one source to support several elements, and one element to depend on several sources.

### Qualitative and procedural obligations

Add a normative form that can identify an actor, required action or qualitative outcome, subject, conditions and applicable interpretation without demanding a numerical requirement or limit. Existing `Rule` objects require at least one such bound. Definitions describe what concepts mean, and relationships connect provisions; neither supplies this missing kind of obligation.

ORO.FTL.210(a)(3) requires duty to be “spread as evenly as practicable”. CS FTL.1.225(b)(2) requires the operator's standby procedures to be designed so standby and FDP do not lead to more than eighteen hours awake. A roster-duration cap does not preserve that actor/action obligation. These clauses can currently be retained in source annotations, but the normative meaning is not a native schema object. A Boolean attestation can record an external judgment, yet must not replace the underlying obligation or conceal its criteria. Supporting a structured obligation and any separately sourced interpretation is sufficient; automating judgment or procedure assessment is not required.

## Documentary examples and acceptance

Keep ten family examples, but track the five cross-cutting capabilities rather than ten runtime completion projects. Example metadata should identify represented provisions, symbolic inputs with meanings/types/units, definition references, remaining prose-only meaning, sources and interpretations. Distinguish external primitive facts from derived concepts whose definitions should be included in the shared document.

Acceptance concerns valid serialization, preserved references and relationships, source attribution, and whether representative documents state the intended meaning without an opaque flag concealing material conditions. Illustrative scenarios can demonstrate the distinction between aggregate and consecutive rest or total overlap and qualifying nights. They need not be executable compliance tests.

Evaluator completion, lookup/projection execution, roster ingestion, missing-value behavior, timestamp accessors and arithmetic implementation bugs are external engine concerns. They are not findings in this schema assessment. The roadmap's operation-semantics work should be understood as engine-independent documentation; it must not make a local execution implementation a prerequisite for the ontology.

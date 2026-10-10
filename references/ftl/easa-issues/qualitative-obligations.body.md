## Purpose and source edition

This issue concerns a vendor-neutral, machine-readable description of crew rules and their meaning. Execution belongs to an external engine. Acceptance does not require an evaluator, roster ingestion, derived-fact computation, or implementation-specific algorithms.

Source: EASA Easy Access Rules for Air Operations, Revision 24, March 2026. The repository preserves the official PDF/XML and verbatim excerpts in `references/ftl/easa-issues/sources.json`. [Publisher publication page](https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-air-operations). ORO, CS, AMC and GM retain their distinct statuses; scheme applicability and operator interpretations must remain identifiable.

## Source text

### ORO.FTL.210(a), (c) — regulatory requirements

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
(a)   The total duty periods to which a crew member may be assigned shall not exceed:
      (1)   60 duty hours in any 7 consecutive days;
      (2)   110 duty hours in any 14 consecutive days; and
      (3)   190 duty hours in any 28 consecutive days, spread as evenly as practicable throughout
            that period.

(c)   Post-flight duty shall count as duty period. The operator shall specify in its operations manual
      the minimum time period for post-flight duties.
```

### CS FTL.1.225 — complete governing certification specification

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
CS FTL.1.225 Standby

The modification of limits on flight duty, duty and rest periods under the provisions of ORO.FTL.225
complies with the following:

(a)   Airport standby
      (1)   If not leading to the assignment of an FDP, airport standby is followed by a rest period as
            specified in ORO.FTL.235.
      (2)   If an assigned FDP starts during airport standby, the following applies:
            (i)    the FDP counts from the start of the FDP. The maximum FDP is reduced by any time
                   spent on standby in excess of 4 hours;
            (ii)   the maximum combined duration of airport standby and assigned FDP as specified
                   in ORO.FTL.205(b) and (d) is 16 hours.
(b)   Standby other than airport standby:
      (1)   the maximum duration of standby other than airport standby is 16 hours;
      (2)   The operator’s standby procedures are designed to ensure that the combination of
            standby and FDP do not lead to more than 18 hours awake time;
      (3)   25 % of time spent on standby other than airport standby counts as duty time for the
            purpose of ORO.FTL.210;
      (4)   standby is followed by a rest period in accordance with ORO.FTL.235;
      (5)   standby ceases when the crew member reports at the designated reporting point;
      (6)   if standby ceases within the first 6 hours, the maximum FDP counts from reporting;
      (7)   if standby ceases after the first 6 hours, the maximum FDP is reduced by the amount of
            standby time exceeding 6 hours;
      (8)   if the FDP is extended due to in-flight rest according to CS FTL.1.205(c), or to split duty
            according to CS FTL.1.220, the 6 hours of paragraph (6) and (7) are extended to 8 hours;
      (9)   if standby starts between 23:00 and 07:00, the time between 23:00 and 07:00 does not
            count towards the reduction of the FDP under (6), (7) and (8) until the crew member is
            contacted by the operator; and
      (10) the response time between call and reporting time established by the operator allows
           the crew member to arrive from his/her place of rest to the designated reporting point
           within a reasonable time.
```

## Existing supported encoding

The duty-hour ceilings and numeric standby restrictions fit the existing rule form. The source text can also be preserved in annotations. A numeric or Boolean symbol can record an external judgment about a procedure or distribution of duty. These are useful capabilities, but none by itself states the underlying qualitative or procedural obligation in a native normative object.

## Minimal documentary counterexample

ORO.FTL.210(a)(3) requires 190 duty hours in twenty-eight consecutive days to be “spread as evenly as practicable”. A 190-hour cap describes the ceiling but omits that distinct obligation. Setting `distribution_is_acceptable = 1` merely names a judgment unless the duty-distribution obligation and any adopted criteria are documented separately.

CS FTL.1.225(b)(2) requires the *operator's standby procedures* to be designed so the combination of standby and FDP does not lead to more than eighteen hours awake. A rule checking one individual's supplied awake-duration value does not preserve the actor, required action and subject of this procedure-design obligation. The threshold is part of its intended outcome, not a replacement for the normative statement.

## Genuinely missing representation

A normative object that can describe actor, obligation or permission, action/qualitative outcome, subject and conditions without requiring a numerical minimum or maximum. It should reference source provisions and, where available, a separate operator interpretation, criteria or evidence specification. Text retained only in a source annotation is not yet a native statement of that obligation.

Evidence: `models/rule.py` requires at least one of `limit` or `requirement`, both calculation-value decision tables. A shared definition describes a concept; a relationship links provisions. Neither introduces a qualitative normative node, so this is distinct from the other four issues.

## Schema acceptance criteria

- [ ] Serialize the obligation to distribute duty as evenly as practicable, identifying its subject, responsible actor and twenty-eight-day context without inventing a numerical balancing threshold.
- [ ] Serialize the standby procedure-design obligation with the operator as actor and the eighteen-hour awake-time outcome correctly attached to that obligation.
- [ ] Preserve the distinction between this obligation and any illustrative individual duration check, attestation or scheme-specific interpretation.
- [ ] Allow conditions, sources, interpretations and relationships to use the same reference mechanisms as other normative objects.
- [ ] Permit meaningful documentation when the source leaves a qualitative judgment open; record interpretation status instead of concealing it in an opaque compliance flag.
- [ ] Require no automatic assessment of procedure quality, evidence gathering, optimization or runtime judgment.

Affected examples: cumulative duty and standby establish independent source-backed requirements. Other operator duties in the source material can reuse this normative form.

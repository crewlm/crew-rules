## Purpose and source edition

This issue concerns a vendor-neutral, machine-readable description of crew rules and their meaning. Execution belongs to an external engine. Acceptance does not require an evaluator, roster ingestion, derived-fact computation, or implementation-specific algorithms.

Source: EASA Easy Access Rules for Air Operations, Revision 24, March 2026. The repository preserves the official PDF/XML and verbatim excerpts in `references/ftl/easa-issues/sources.json`. [Publisher publication page](https://www.easa.europa.eu/en/document-library/easy-access-rules/easy-access-rules-air-operations). ORO, CS, AMC and GM retain their distinct statuses; scheme applicability and operator interpretations must remain identifiable.

## Source text

### ORO.FTL.235(d), (e) — regulatory requirements

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
(d)   Recurrent extended recovery rest periods
      Flight time specification schemes shall specify recurrent extended recovery rest periods to
      compensate for cumulative fatigue. The minimum recurrent extended recovery rest period shall
      be 36 hours, including 2 local nights, and in any case the time between the end of one recurrent
      extended recovery rest period and the start of the next extended recovery rest period shall not
      be more than 168 hours. The recurrent extended recovery rest period shall be increased to 2
      local days twice every month.
(e)   Flight time specification schemes shall specify additional rest periods in accordance with the
      applicable certification specifications to compensate for:
      (1)   the effects of time zone differences and extensions of the FDP;
      (2)   additional cumulative fatigue due to disruptive schedules; and
      (3)   a change of home base.
```

### ORO.FTL.105 definitions (15, 16, 21, 8, 9)

Verbatim quotation (line wrapping and layout whitespace normalized):

```text
(15) ‘local day’ means a 24-hour period commencing at 00:00 local time;

(16) ‘local night’ means a period of 8 hours falling between 22:00 and 08:00 local time;

(21) ‘rest period’ means a continuous, uninterrupted and defined period of time, following duty or
     prior to duty, during which a crew member is free of all duties, standby and reserve.

(8)   ‘disruptive schedule’ means a crew member’s roster which disrupts the sleep opportunity
      during the optimal sleep time window by comprising an FDP or a combination of FDPs which
      encroach, start or finish during any portion of the day or of the night where a crew member is
      acclimatised. A schedule may be disruptive due to early starts, late finishes or night duties.
      (a)   ‘early type’ of disruptive schedule means:
            (i)    for ‘early start’ a duty period starting in the period between 05:00 and 05:59 in the
                   time zone to which a crew member is acclimatised, and
            (ii)   for ‘late finish’ a duty period finishing in the period between 23:00 and 01:59 in the
                   time zone to which a crew member is acclimatised;
      (b)   ‘late type’ of disruptive schedule means:
            (i)    for ‘early start’ a duty period starting in the period between 05:00 and 06:59 in the
                   time zone to which a crew member is acclimatised; and
            (ii)   for ‘late finish’ a duty period finishing in the period between 00:00 and 01:59 in the
                   time zone to which a crew member is acclimatised;

(9)   ‘night duty’ means a duty period encroaching any portion of the period between 02:00 and
      04:59 in the time zone to which the crew is acclimatised;
```

## Existing supported encoding

Named quantities already allow rules such as `local_nights_count >= 2`, `gap_hours <= 168` and `minimum_landing_crew_uninterrupted_rest_hours >= 2`. Projections support anchors, offsets, rates and clamps; time periods include calendar years and months. The annual 900-hour operating-flight restriction is directly expressible with a year-anchored, one-year employee-period rule and projection. Collection helpers already provide map/count/extrema/first/last/flatten, and an overlap comparison is present. Do not reopen these as missing capabilities.

## Minimal documentary counterexample

A continuous 36-hour rest from 02:00 on day one to 14:00 on day two overlaps the recurring 22:00–08:00 windows for sixteen hours: six in the first occurrence and ten in the second. It contains only one qualifying eight-hour local night. Total overlap is therefore insufficient to describe the source's requirement for two separately qualifying local nights.

`local_nights_count` can legitimately be a symbolic input, but its name and an informal definition do not structurally describe how separate occurrences qualify and are counted. Similarly, a supplied preceding-recovery-rest endpoint does not document selection of the preceding *qualifying* event. Two one-hour rest intervals also do not describe a single consecutive two-hour rest for an individual landing crew member.

## Genuinely missing representation

Reusable definition bodies for qualifying/selecting related intervals and events, containment, continuity, occurrence-specific predicates and counts, event adjacency/history, and person-correlated collections. These definitions should connect quantities to their constituent concepts through explicit references. This is a missing description of meaning, not a missing interval-processing algorithm.

Evidence: `models/time_period.py` supplies anchor/unit/duration; `ProjectionValue` describes one anchored interval with rates/clamps; the `CalculationValue` union has no general definition form for selecting prior qualifying events or counting independently qualifying occurrences. Existing collection paths can remain sufficient for simple minima once the collection and member quantities are defined; a new quantifier is not inherently required for every “each crew member” clause.

## Schema acceptance criteria

- [ ] Serialize a local-night definition and a count of separately qualifying occurrences contained within a rest, preserving the distinction in the 36-hour example.
- [ ] Describe the preceding/next qualifying recovery rest and the gap between their specified endpoints; identify intervening disruptive-duty selection separately from its threshold.
- [ ] Describe continuity for individual in-flight rest and association with each applicable crew member/landing role, distinguishing one two-hour interval from two one-hour intervals.
- [ ] Describe a standby interval's overnight exclusion until the related first-contact event, referencing the relevant local-time definition.
- [ ] Identify any calendar attribution or boundary interpretation adopted by a scheme without inventing regulatory requirements or replacing calendar periods with fixed hours.
- [ ] Reuse existing projection, period, overlap and collection structures where they already convey the required meaning.

Affected examples: all ten can consume temporal definitions; recovery rest, augmentation, standby and split duty supply the clearest counterexamples. Acceptance is documentary serialization and review of meaning, not derived-fact computation.

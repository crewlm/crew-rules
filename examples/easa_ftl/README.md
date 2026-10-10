# EASA FTL documentary schema catalog

This package records ten source-backed EASA flight time limitation examples in
the repository's existing `Rule` and `Projection` models. Each family also
declares the source concepts behind symbolic field paths, what its current
schema represents, its source citations, and the schema areas still missing.
The catalog is documentation and interchange data; it does not derive roster
facts, calculate regulatory outcomes, or make a compliance claim.

The symbolic field strings in conditions and values are valid schema
declarations. Their presence does not require matching Python attributes or
prepared runtime values. Missing shared definitions remain explicit metadata
because they affect how an external engine would interpret and connect the
declarations.

| No. | Family | Represented in the current schema | Main schema gaps |
|---:|---|---|---|
| 01 | [Cumulative duty](specifications/cumulative-duty.json) | 7-, 14-, and 28-day limits and duty-credit projections; the even-spread obligation is source text | shared definitions, rule relationships, temporal collections, source bindings, qualitative obligations |
| 02 | [Cumulative operating flight time](specifications/cumulative-operating-flight-time.json) | 28-day, calendar-year, and 12-consecutive-calendar-month limits with operating-flight projection | shared definitions, rule relationships, temporal collections, source bindings |
| 03 | [Basic maximum daily FDP](specifications/basic-daily-fdp.json) | EASA Tables 2–4, sector limits, FRM guard, and nine-hour floor | shared definitions, rule relationships, temporal collections, source bindings |
| 04 | [Positioning](specifications/positioning-accounting.json) | Duty credit, FDP inclusion, and zero operating-sector contribution | shared definitions, rule relationships, temporal collections, source bindings |
| 05 | [Home-base rest](specifications/home_rest.json) | Ordinary 12-hour / preceding-duty maximum; the 10-hour branch requires both a claimed derogation and suitable accommodation | shared definitions, rule relationships, temporal collections, source bindings |
| 06 | [Away-base rest](specifications/away_rest.json) | 10-hour / preceding-duty maximum and separate eight-hour protected-sleep opportunity; the AMC travel formula and unresolved order are documented | shared definitions, rule relationships, temporal collections, source bindings |
| 07 | [Recovery rest](specifications/recovery_rest.json) | Duration, local-night, gap, monthly local-day, and disruptive-schedule conditions | shared definitions, rule relationships, temporal collections, source bindings |
| 08 | [Split duty](specifications/split_duty.json) | Three-hour qualified break, full-break FDP inclusion, conditional half-break extension credit, accommodation branches, and zero-occurrence prohibitions | shared definitions, rule relationships, temporal collections, source bindings |
| 09 | [Standby](specifications/standby.json) | Duty projections, clamped 4/6/8-hour reductions, and scoped 16-hour limits; overnight and procedure clauses remain documentary annotations | shared definitions, rule relationships, temporal collections, source bindings, qualitative obligations |
| 10 | [Augmentation and in-flight rest](specifications/augmentation.json) | Six total FDP caps, strict one-hour extension guard, all 24 cabin-table cells, crew rest minima, and destination rest | shared definitions, rule relationships, temporal collections, source bindings |

The stable gap identifiers are `shared-definitions`, `rule-relationships`,
`temporal-collection-definitions`, `source-bindings`, and
`qualitative-obligations`. The latter tracks source obligations whose actors,
actions, or outcomes cannot be expressed as numeric limits in the current
`Rule` model. Family JSON exports
preserve `Rule` and `Projection` model objects plus documentary metadata. They
are not complete ontology definitions and do not supply the temporal
collections, crew relationships, provenance bindings, or shared definitions
needed by an external evaluator.

Export deterministic JSON files with:

```sh
python -m examples.easa_ftl \
  --output examples/easa_ftl/specifications \
  --manifest
```

This writes ten family specifications and, with `--manifest`, a catalog index.
The source bundle at
[`references/ftl/easa-issues/sources.json`](../../references/ftl/easa-issues/sources.json)
retains quotations and source references. The canonical citations and scope
analysis are also in the [EASA model gap analysis](../../references/ftl/easa-model-gap-analysis.md).

Schema-gap issue drafts are prepared separately from the EASA family
fragments. When a source-backed JSON draft list is available, export it with:

```sh
python -m examples.easa_ftl \
  --output /tmp/easa-ftl-json \
  --gap-issues references/ftl/easa-issues/schema-gap-drafts.json \
  --issues-output /tmp/easa-ftl-issues
```

The draft file is a JSON list of `{ "slug", "title", "body" }` records.
This command copies those prepared bodies and writes a file manifest; it does
not regenerate per-family issues from rule fragments or source quotations.
The current source-backed drafts are [shared definitions](../../references/ftl/easa-issues/shared-definitions.body.md),
[rule relationships](../../references/ftl/easa-issues/rule-relationships.body.md),
[temporal and collection definitions](../../references/ftl/easa-issues/temporal-collection-definitions.body.md),
[source bindings](../../references/ftl/easa-issues/source-bindings.body.md), and
[qualitative obligations](../../references/ftl/easa-issues/qualitative-obligations.body.md).
Their GitHub tracking issues are [#11](https://github.com/crewlm/crew-rules/issues/11),
[#12](https://github.com/crewlm/crew-rules/issues/12),
[#13](https://github.com/crewlm/crew-rules/issues/13),
[#14](https://github.com/crewlm/crew-rules/issues/14), and
[#15](https://github.com/crewlm/crew-rules/issues/15), respectively.

Run the documentary schema checks with:

```sh
.venv/bin/python -m pytest tests/easa_ftl -q
```

These checks cover model round trips, deterministic exports, source coverage,
symbolic concept and projection references, and structural transcription of
the FDP matrix. Any runtime evaluation belongs to a separate external engine
with its own temporal and relationship definitions.

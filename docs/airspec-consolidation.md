# AirSpec handoff consolidation

This note records the public repository work brought together in the
`codex/consolidation-airspec-20261010` branch. Both source commits remain in the
Git history.

## Source handoffs

- `codex/easa-documentary-schema-20261010` (`c4c9c7b`) adds ten documentary
  EASA FTL schema families, deterministic JSON exports, source and gap
  references, a gap analysis, and schema tests.
- `codex/easa-source-model-explorer-20261010` (`90394a2`) adds a React browser
  for one pinned EASA source, five smaller draft models, model-to-paragraph
  links, a generated catalogue, and catalogue tests. The catalogue has 74
  topics, 1,137 source paragraphs, and 9 tables.

The ten schema families and five browser models serve separate purposes and
are not duplicate counts. Explorer links apply to a whole draft model and a
source paragraph. They do not claim field-level or clause-level provenance.
Unlinked paragraphs remain visible as unlinked.

## Scope and limits

The repository is a vendor-neutral, permissively licensed specification and
independent reference. It does not prescribe a vendor plugin or runtime.
The EASA schemas and browser models document draft interpretations, source
references, and known gaps. Neither is an operational compliance result.
`Rule.evaluate` in the existing upstream model is still a TODO; a full rule
engine, compliance calculation, or runtime integration is outside these
handoffs. Schema/export and catalogue checks validate declarations and source
links, not regulatory outcomes.

The source bundle pins EASA Revision 24 (March 2026), with corresponding FAA
and CASA reference materials. This consolidation adds no customer data,
credentials, private artifacts, or working notes.

## Validation

From the repository root, run the combined Python suites and regenerate both
the schema exports and browser catalogue:

```sh
python -m pytest -q tests/easa_ftl tests/catalogue
python -m examples.easa_ftl --output examples/easa_ftl/specifications --manifest
python -m catalogue.export
```

To build the browser bundle:

```sh
cd web
npm ci
npm run build
```

Validation records should identify the exact Python and Node versions used.
The generated `web/dist` directory is ignored by Git.

For this consolidation, Python 3.14.7 ran the combined suite successfully:
17 tests passed. Both export commands completed without changing tracked
outputs. `npm ci` and `npm run build` completed successfully with Vite 8.3.3.
The browser build used Node.js 24.19.0 and npm 11.9.0.

# AirSpec rule draft contract 1.0.0

The browser's rule workshop uses a versioned, engine-independent JSON contract. The `rule` property retains the repository's original `AnyRule` JSON shape. This interface defines authoring, structural checks, provenance, and export only; it does not define or connect an evaluator.

## Draft

```json
{
  "format": "airspec.rule-draft",
  "formatVersion": "1.0.0",
  "definitionId": "stable catalogue definition ID",
  "revision": 1,
  "basedOn": {
    "catalogueCommit": "catalogue source commit",
    "sourceDocumentId": "EASA document ID",
    "sourceRevision": "Revision 24, March 2026",
    "sourceHash": "source document SHA-256"
  },
  "rule": { "id": "same as definitionId", "scope": "..." },
  "provenance": [
    { "sourceId": "...", "citation": "...", "relation": "models", "note": "...", "text": "...", "locator": {} }
  ],
  "coverageGaps": ["Catalogue model limitations, carried through to export"]
}
```

`definitionId` is stable across revisions, while `revision` is a positive integer. Each provenance link preserves the source unit ID, citation, relation, note, source text, and locator where available. `coverageGaps` records limitations from the catalogue interpretation independently of executable support.

## Functions

- `validateRuleDraft(draft)` returns `{status, errors, unsupported}`. `status` is `invalid` when structure is malformed and `valid_non_executable` for structurally valid drafts. `errors` are structural issues with `{path, code, message}`. `unsupported` currently reports `ENGINE_DISCONNECTED`; this means validity is not a compliance result.
- `diffRuleDraft(before, after)` returns changed JSON paths with their before/after values.
- `exportRuleDraft(draft)` rejects invalid drafts and returns an `airspec.rule-definition` version `1.0.0` with the stable ID, revision, based-on identity, AnyRule payload, provenance, coverage gaps, and validation/unsupported summary. Valid non-executable drafts can be exported.

The current catalogue is a partial EASA Air Operations Revision 24 subset. Catalogue interpretations are explicitly identified as drafts, and exported coverage gaps remain visible. Neither a valid draft nor an export implies complete legality coverage or operational compliance.

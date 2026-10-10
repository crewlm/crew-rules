import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { diffRuleDraft, exportRuleDraft, makeRuleDraft, validateRuleDraft } from './airspec.js';
import { clearDraftLocally, loadDraftLocally, saveDraftLocally } from './draftStorage.js';

const catalogue = JSON.parse(await readFile(new URL('../public/catalogue.json', import.meta.url), 'utf8'));
const source = catalogue.documents[0];
const model = catalogue.models[0];
const links = catalogue.links.filter((link) => link.model_id === model.id);
const draft = makeRuleDraft(model, links, source);

test('malformed drafts report structural errors separately from unsupported semantics', () => {
  const result = validateRuleDraft({ ...draft, rule: { ...draft.rule, scope: 'unknown', value: null } });
  assert.equal(result.status, 'invalid');
  assert.ok(result.errors.some((item) => item.path === 'rule.scope'));
  assert.ok(result.errors.some((item) => item.path === 'rule.value'));
  assert.deepEqual(result.unsupported, []);
});

test('deep table shape, stable IDs, and period-scope requirements are checked', () => {
  const edited = structuredClone(draft);
  edited.rule.id = 'wrong-stable-id';
  edited.rule.value = { items: [{ condition: [{ field: '', comparison: {} }], value: null }] };
  edited.rule.scope = 'employee_time_period';
  delete edited.rule.time_period;
  const result = validateRuleDraft(edited);
  assert.equal(result.status, 'invalid');
  assert.ok(result.errors.some((item) => item.code === 'DEFINITION_ID_MISMATCH'));
  assert.ok(result.errors.some((item) => item.path === 'rule.value'));
  assert.ok(result.errors.some((item) => item.path.includes('condition[0]')));
  assert.ok(result.errors.some((item) => item.path === 'rule.time_period'));
});

test('structurally valid drafts remain explicitly non-executable', () => {
  const result = validateRuleDraft(draft);
  assert.equal(result.status, 'valid_non_executable');
  assert.equal(result.errors.length, 0);
  assert.ok(result.unsupported.some((item) => item.code === 'ENGINE_DISCONNECTED'));
});

test('draft and export preserve revision and source provenance', () => {
  assert.equal(draft.basedOn.catalogueCommit, 'ac94f6e092555931781c31e23848b0af5aee295b');
  assert.equal(draft.basedOn.sourceDocumentId, source.id);
  assert.equal(draft.basedOn.sourceHash, source.sha256);
  assert.ok(draft.provenance.length > 0);
  assert.ok(draft.provenance.every((item) => item.sourceId && item.citation && item.relation && item.text));
  const exported = exportRuleDraft(draft);
  assert.equal(exported.format, 'airspec.rule-definition');
  assert.equal(exported.revision, 1);
  assert.deepEqual(exported.provenance, draft.provenance);
  assert.deepEqual(exported.coverageGaps, model.limitations);
  assert.equal(exported.validation.status, 'valid_non_executable');
  assert.throws(() => exportRuleDraft({ ...draft, rule: null }), /Invalid drafts/);
});

test('diff reports JSON paths without coupling to the engine model', () => {
  const edited = structuredClone(draft);
  edited.rule.name = 'Edited locally';
  const changes = diffRuleDraft(draft, edited);
  assert.deepEqual(changes.map((item) => item.path), ['rule.name']);
  assert.equal(changes[0].before, draft.rule.name);
  assert.equal(changes[0].after, 'Edited locally');
});

test('cancel restores a saved revision and a fresh session reloads it from local storage', () => {
  const values = new Map();
  const storage = { setItem: (key, value) => values.set(key, value), getItem: (key) => values.get(key) ?? null, removeItem: (key) => values.delete(key) };
  const saved = { ...draft, revision: 3, rule: { ...draft.rule, name: 'Saved revision' } };
  saveDraftLocally(storage, saved);
  const freshSession = loadDraftLocally(storage, draft.definitionId);
  assert.equal(freshSession.revision, 3);
  assert.equal(freshSession.rule.name, 'Saved revision');
  const unsaved = { ...freshSession, rule: { ...freshSession.rule, name: 'Unsaved change' } };
  const cancelled = loadDraftLocally(storage, draft.definitionId);
  assert.equal(cancelled.rule.name, 'Saved revision');
  assert.equal(unsaved.rule.name, 'Unsaved change');
  clearDraftLocally(storage, draft.definitionId);
  assert.equal(loadDraftLocally(storage, draft.definitionId), null);
});

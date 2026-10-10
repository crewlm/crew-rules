import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { diffRuleDraft, exportRuleDraft, makeRuleDraft, validateRuleDraft } from './airspec.js';
import { clearDraftLocally, loadDraftLocally, loadDraftRevisionLocally, saveDraftLocally } from './draftStorage.js';

const catalogue = JSON.parse(await readFile(new URL('../public/catalogue.json', import.meta.url), 'utf8'));
const parityCases = JSON.parse(await readFile(new URL('../../tests/catalogue/airspec_parity_cases.json', import.meta.url), 'utf8'));
const source = catalogue.documents[0];
const model = catalogue.models[0];
const links = catalogue.links.filter((link) => link.model_id === model.id);
const draft = makeRuleDraft(model, links, source);

function parityRule(testCase) {
  const rule = structuredClone(model.model);
  if (testCase.kind === 'number') {
    rule.value.default = { kind: 'number_value', number: testCase.value };
  } else if (testCase.kind === 'duration') {
    rule.value.default = { kind: 'duration_value', duration: testCase.value };
  } else {
    const comparison = testCase.kind === 'time'
      ? { kind: 'time_window_overlap_comparison', start: '09:00', end: '10:00' }
      : testCase.kind === 'datetime'
        ? { kind: 'range_datetime_comparison', lower: '2026-01-01T00:00:00Z', upper: '2026-01-02T00:00:00Z' }
        : { kind: testCase.comparisonKind, items: [] };
    const field = testCase.field ?? (testCase.kind === 'datetime' ? 'lower' : 'items');
    comparison[field] = testCase.value;
    rule.value.items = [{ condition: [{ field: 'duration', comparison }], value: rule.value.default }];
  }
  return { ...draft, rule };
}

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

test('time period integer inputs follow Python AnyRule integer coercion', () => {
  const integerRule = structuredClone(draft.rule);
  integerRule.scope = 'employee_time_period';
  integerRule.time_period = { anchor: 'day', unit: 'hour', duration: 1 };
  for (const duration of [12, 12.0, '12', '1.0', '1_0', ' 1 ']) {
    assert.equal(validateRuleDraft({ ...draft, rule: { ...integerRule, time_period: { ...integerRule.time_period, duration } } }).status, 'valid_non_executable', String(duration));
  }
  for (const duration of [1.5, '0x10', '1e3', null]) {
    assert.equal(validateRuleDraft({ ...draft, rule: { ...integerRule, time_period: { ...integerRule.time_period, duration } } }).status, 'invalid', String(duration));
  }
});

test('AnyRule structural errors stay invalid and separate from engine support', () => {
  const cases = [
    ['missing field on calculation default', (rule) => { delete rule.value.default.field; }],
    ['unknown comparison kind', (rule) => { rule.value.items = [{ condition: [{ field: 'duration', comparison: { kind: 'unknown_comparison' } }], value: rule.value.default }]; }],
    ['comparison field type', (rule) => { rule.value.items = [{ condition: [{ field: 'duration', comparison: { kind: 'ge_number_comparison', number: 'not a number' } }], value: rule.value.default }]; }],
    ['scalar calculation default', (rule) => { rule.value.default = 7; }],
    ['calculation field type', (rule) => { rule.value.default = { kind: 'number_value', number: 'not a number' }; }],
    ['missing update table default', (rule) => { rule.value_updates = [{ name: 'x', table: { items: [] } }]; }],
    ['null update method', (rule) => { rule.value_updates = [{ name: 'x', method: null, table: { default: { kind: 'none_value' } } }]; }],
  ];
  for (const [label, mutate] of cases) {
    const malformed = structuredClone(draft);
    mutate(malformed.rule);
    const result = validateRuleDraft(malformed);
    assert.equal(result.status, 'invalid', label);
    assert.ok(result.errors.length > 0, label);
    assert.deepEqual(result.unsupported, [], label);
  }
  const throwingUpdate = structuredClone(draft);
  throwingUpdate.rule.value_updates = [{ name: 'x', table: {} }];
  assert.doesNotThrow(() => validateRuleDraft(throwingUpdate));
  assert.equal(validateRuleDraft(throwingUpdate).status, 'invalid');
});

test('69 numeric, duration, time, datetime, and set cases apply AnyRule and JSON-safe constraints', () => {
  assert.equal(parityCases.length, 69);
  for (const testCase of parityCases) {
    const fixtureDraft = parityRule(testCase);
    const result = validateRuleDraft(fixtureDraft);
    assert.equal(result.status !== 'invalid', testCase.valid, testCase.name);
    assert.equal(result.unsupported.length > 0, testCase.valid, `${testCase.name}: unsupported status tracks structural validity`);
    if (testCase.valid) {
      const reloaded = JSON.parse(JSON.stringify(fixtureDraft));
      assert.deepEqual(reloaded, fixtureDraft, `${testCase.name}: fixture JSON round-trip must preserve its values`);
      assert.deepEqual(validateRuleDraft(reloaded), result, `${testCase.name}: revalidation must preserve status and issues`);
      const exportPayload = exportRuleDraft(reloaded);
      const exported = JSON.parse(JSON.stringify(exportPayload));
      assert.deepEqual(exported, exportPayload, `${testCase.name}: full exported definition JSON round-trip must preserve its values`);
      assert.deepEqual(exported.rule, reloaded.rule, `${testCase.name}: exported rule JSON round-trip must preserve its values`);
    }
  }
});

test('non-finite and JSON-normalized numbers are rejected by validation, export, and save', () => {
  const values = [Infinity, NaN, -0, 'Infinity', 'NaN', '1e400'];
  const valuesStore = new Map();
  const storage = { setItem: (key, value) => valuesStore.set(key, value), getItem: (key) => valuesStore.get(key) ?? null, removeItem: (key) => valuesStore.delete(key) };
  for (const number of values) {
    const unsafe = structuredClone(draft);
    unsafe.rule.value.default = { kind: 'number_value', number };
    assert.equal(validateRuleDraft(unsafe).status, 'invalid', String(number));
    assert.throws(() => exportRuleDraft(unsafe), /Invalid drafts/);
    assert.throws(() => saveDraftLocally(storage, unsafe), /cannot survive JSON serialization|Invalid drafts/);
  }
  assert.equal(loadDraftLocally(storage, draft.definitionId), null, 'unsafe drafts must not enter local storage');

  const unsafeExtra = structuredClone(draft);
  unsafeExtra.unused = { number: Infinity };
  assert.ok(validateRuleDraft(unsafeExtra).errors.some((item) => item.code === 'JSON_VALUE_UNSAFE'), 'the JSON-safety check must cover the entire draft');

  const negativeZeroEdit = { ...draft, rule: { ...draft.rule, value: { ...draft.rule.value, default: { kind: 'number_value', number: -0 } } } };
  assert.equal(diffRuleDraft(draft, negativeZeroEdit).some((change) => change.path === 'rule.value.default.number'), true, 'the changed-path view must distinguish negative zero from zero');
});

test('updates require their matching base requirement or limit', () => {
  const missingRequirement = structuredClone(draft);
  missingRequirement.rule.limit = structuredClone(missingRequirement.rule.requirement);
  missingRequirement.rule.requirement = null;
  missingRequirement.rule.requirement_updates = [{ name: 'x', table: { default: { kind: 'none_value' } } }];
  const requirementResult = validateRuleDraft(missingRequirement);
  assert.ok(requirementResult.errors.some((item) => item.path === 'rule.requirement_updates' && item.code === 'UPDATE_BASE_REQUIRED'));
  assert.deepEqual(requirementResult.unsupported, []);

  const missingLimit = structuredClone(draft);
  missingLimit.rule.limit_updates = [{ name: 'x', table: { default: { kind: 'none_value' } } }];
  const limitResult = validateRuleDraft(missingLimit);
  assert.ok(limitResult.errors.some((item) => item.path === 'rule.limit_updates' && item.code === 'UPDATE_BASE_REQUIRED'));
  assert.deepEqual(limitResult.unsupported, []);
});

test('structurally valid drafts remain explicitly non-executable', () => {
  const result = validateRuleDraft(draft);
  assert.equal(result.status, 'valid_non_executable');
  assert.equal(result.errors.length, 0);
  assert.ok(result.unsupported.some((item) => item.code === 'ENGINE_DISCONNECTED'));
});

test('catalogue rule fixtures remain structurally valid', () => {
  for (const model of catalogue.models) {
    const sourceLinks = catalogue.links.filter((link) => link.model_id === model.id);
    assert.equal(validateRuleDraft(makeRuleDraft(model, sourceLinks, source)).status, 'valid_non_executable', model.name);
  }
});

test('Python AnyRule defaults remain accepted when optional arrays are omitted', () => {
  const partial = structuredClone(draft.rule);
  for (const field of ['applicability', 'value', 'requirement']) if (partial[field]) delete partial[field].items;
  partial.value_updates = [{ name: 'x', table: { default: { kind: 'none_value' } } }];
  for (const field of ['requirement_updates', 'limit_updates']) delete partial[field];
  assert.equal(validateRuleDraft({ ...draft, rule: partial }).status, 'valid_non_executable');
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
  assert.equal(loadDraftRevisionLocally(storage, draft.definitionId), 3, 'clearing source-backed draft state must preserve its revision high-water mark');
  saveDraftLocally(storage, { ...draft, revision: 1 });
  assert.equal(loadDraftRevisionLocally(storage, draft.definitionId), 3, 'storing a reset revision must not lower the high-water mark');
});

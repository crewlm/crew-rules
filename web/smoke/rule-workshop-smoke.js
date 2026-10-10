import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { access, readFile } from 'node:fs/promises';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium } from 'playwright';

const port = Number(process.env.SMOKE_PORT || 5178);
const baseUrl = `http://127.0.0.1:${port}`;
const catalogue = JSON.parse(await readFile(new URL('../public/catalogue.json', import.meta.url), 'utf8'));
const sourceDocument = catalogue.documents[0];
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], {
  cwd: new URL('..', import.meta.url),
  stdio: 'ignore',
});
let browser;

async function getWorkshopGeometry(page) {
  return page.evaluate(() => {
    const app = document.querySelector('.app-shell');
    const panel = document.querySelector('.view-panel:not([hidden])');
    const workshop = document.querySelector('.workshop');
    const body = document.querySelector('.workshop-body');
    const rect = (element) => {
      const box = element.getBoundingClientRect();
      return { top: box.top, bottom: box.bottom, width: box.width, height: box.height };
    };
    return {
      viewport: { width: innerWidth, height: innerHeight, bodyWidth: document.body.scrollWidth },
      app: rect(app), panel: rect(panel), workshop: rect(workshop), body: rect(body),
      panelDisplay: getComputedStyle(panel).display,
      bodyClientHeight: body.clientHeight, bodyScrollHeight: body.scrollHeight,
    };
  });
}

async function waitForServer() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (server.exitCode !== null) throw new Error(`Vite exited with code ${server.exitCode}`);
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch { /* Vite is still starting. */ }
    await delay(250);
  }
  throw new Error(`Vite did not become ready at ${baseUrl}`);
}

try {
  await waitForServer();
  const launchOptions = { headless: true, args: ['--no-sandbox'] };
  const systemChromium = process.env.CHROMIUM_PATH || '/usr/bin/chromium';
  try {
    await access(systemChromium);
    launchOptions.executablePath = systemChromium;
  } catch { /* Use the browser installed by `npx playwright install chromium`. */ }
  browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  const firstModel = catalogue.models[0];
  await page.addInitScript(({ id }) => {
    const key = `airspec.rule-draft:${id}`;
    if (localStorage.getItem(key) === null) localStorage.setItem(key, JSON.stringify({ format: 'obsolete-draft', revision: 9 }));
  }, { id: firstModel.id });
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Rule workshop', exact: true }).click();
  const desktopGeometry = await getWorkshopGeometry(page);
  assert.equal(desktopGeometry.panelDisplay, 'flex');
  assert.ok(desktopGeometry.workshop.height > 300 && desktopGeometry.workshop.width > 600, 'desktop workshop should fill its flex panel');
  assert.ok(desktopGeometry.bodyClientHeight > 0 && desktopGeometry.bodyScrollHeight >= desktopGeometry.bodyClientHeight, 'desktop workshop body should have a valid scroll viewport');
  const editor = page.getByRole('textbox', { name: 'AnyRule JSON draft' });
  await assert.doesNotReject(() => page.getByText('Valid · non-executable', { exact: true }).waitFor());
  const originalRule = JSON.parse(await editor.inputValue());

  // A rejected stale object must not become a saved revision or a Cancel target.
  assert.equal(originalRule.name, firstModel.name);
  await page.getByRole('button', { name: 'Cancel edits' }).click();
  assert.deepEqual(JSON.parse(await editor.inputValue()), originalRule);
  assert.equal(await page.getByText(/obsolete-draft/).count(), 0);
  assert.equal(await page.evaluate((id) => localStorage.getItem(`airspec.rule-draft:${id}`), firstModel.id), null, 'invalid stored data should be discarded before it can block or poison a new revision');

  // Open a second tab against the same empty local state before the first tab saves.
  const stalePage = await context.newPage();
  const stalePageErrors = [];
  stalePage.on('pageerror', (error) => stalePageErrors.push(error.message));
  await stalePage.goto(baseUrl, { waitUntil: 'networkidle' });
  await stalePage.getByRole('button', { name: 'Rule workshop', exact: true }).click();
  const staleEditor = stalePage.getByRole('textbox', { name: 'AnyRule JSON draft' });
  assert.equal(JSON.parse(await staleEditor.inputValue()).name, firstModel.name);

  // Invalid JSON is a parse failure, distinct from a valid but unsupported draft.
  await editor.fill('{');
  await page.getByText(/JSON parse error:/).waitFor();
  await page.getByText('Invalid JSON', { exact: true }).waitFor();
  assert.equal(await page.getByText(/SCOPE_INVALID/).count(), 0, 'a parse failure should not be reported as a structural validation error');
  assert.equal(await page.getByRole('button', { name: 'Save locally' }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), true);

  // Reproduce table:{} without throwing or blanking the React root.
  const malformedUpdate = structuredClone(originalRule);
  malformedUpdate.value_updates = [{ name: 'x', table: {} }];
  await editor.fill(JSON.stringify(malformedUpdate, null, 2));
  await page.getByText('Needs correction', { exact: true }).waitFor();
  assert.equal(await page.getByRole('heading', { name: 'Rule workshop', exact: true }).count(), 1, 'the workshop must stay rendered after malformed update input');
  assert.ok(pageErrors.length === 0, `malformed update caused uncaught errors: ${pageErrors.join('; ')}`);
  assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), true);

  const malformed = structuredClone(originalRule);
  malformed.scope = 'invalid_scope';
  await editor.fill(JSON.stringify(malformed, null, 2));
  await page.getByText('Needs correction', { exact: true }).waitFor();
  await page.getByText(/must be one of the declared AnyRule scopes/).waitFor();
  assert.equal(await page.getByText(/JSON parse error:/).count(), 0, 'valid JSON with invalid structure should not be reported as a parse failure');
  assert.equal(await page.getByRole('button', { name: 'Save locally' }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), true);

  for (const [label, mutate] of [
    ['missing default field', (rule) => { delete rule.value.default.field; }],
    ['scalar calculation default', (rule) => { rule.value.default = 7; }],
    ['invalid calculation field type', (rule) => { rule.value.default = { kind: 'number_value', number: 'not a number' }; }],
    ['unknown comparison kind', (rule) => { rule.value.items = [{ condition: [{ field: 'duration', comparison: { kind: 'unknown_comparison' } }], value: rule.value.default }]; }],
    ['invalid comparison field type', (rule) => { rule.value.items = [{ condition: [{ field: 'duration', comparison: { kind: 'ge_number_comparison', number: 'not a number' } }], value: rule.value.default }]; }],
    ['missing update default', (rule) => { rule.value_updates = [{ name: 'x', table: { items: [] } }]; }],
    ['requirement update without requirement', (rule) => { rule.limit = structuredClone(rule.requirement); rule.requirement = null; rule.requirement_updates = [{ name: 'x', table: { default: { kind: 'none_value' } } }]; }],
    ['limit update without limit', (rule) => { rule.limit_updates = [{ name: 'x', table: { default: { kind: 'none_value' } } }]; }],
    ['invalid time and datetime strings', (rule) => { rule.value.items = [{ condition: [{ field: 'start', comparison: { kind: 'time_window_overlap_comparison', start: '25:99', end: 'garbage' } }], value: rule.value.default }]; }],
    ['unhashable set item', (rule) => { rule.value.items = [{ condition: [{ field: 'status', comparison: { kind: 'equal_set_comparison', items: [{}] } }], value: rule.value.default }]; }],
    ['hex numeric string', (rule) => { rule.value.default = { kind: 'number_value', number: '0x10' }; }],
    ['invalid duration string', (rule) => { rule.value.default = { kind: 'duration_value', duration: 'pt12h' }; }],
  ]) {
    const malformedRule = structuredClone(originalRule);
    mutate(malformedRule);
    await editor.fill(JSON.stringify(malformedRule, null, 2));
    await page.getByText('Needs correction', { exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Save locally' }).isDisabled(), true, label);
    assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), true, label);
    assert.equal(await page.getByText(/ENGINE_DISCONNECTED/).count(), 0, `${label} must remain a structural error`);
  }
  await editor.fill(JSON.stringify(originalRule, null, 2));

  // The unchanged catalogue payload is structurally valid but explicitly non-executable.
  await editor.fill(JSON.stringify(originalRule, null, 2));
  await page.getByText('Valid · non-executable', { exact: true }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), false);
  const engineDisconnectedCode = page.locator('code').filter({ hasText: 'ENGINE_DISCONNECTED' });
  await engineDisconnectedCode.waitFor();
  assert.equal(await engineDisconnectedCode.count(), 1);
  const engineDisconnected = page.getByText(/No executable rule engine is connected/);
  await engineDisconnected.waitFor();
  assert.equal(await engineDisconnected.count(), 1, 'structural validity must retain its explicit unsupported status');

  const provenanceSummary = page.locator('details.provenance-json').first();
  await provenanceSummary.locator('summary').click();
  const provenance = JSON.parse(await provenanceSummary.locator('pre').innerText());
  assert.ok(provenance.length > 0, 'source provenance should be present in the draft');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export versioned JSON' }).click();
  const download = await downloadPromise;
  const exported = JSON.parse(await readFile(await download.path(), 'utf8'));
  assert.equal(exported.format, 'airspec.rule-definition');
  assert.equal(exported.formatVersion, '1.0.0');
  assert.equal(exported.basedOn.catalogueCommit, 'ac94f6e092555931781c31e23848b0af5aee295b');
  assert.equal(exported.basedOn.sourceDocumentId, sourceDocument.id);
  assert.equal(exported.basedOn.sourceRevision, sourceDocument.version);
  assert.equal(exported.basedOn.sourceHash, sourceDocument.sha256);
  assert.ok(exported.provenance.length > 0, 'export must carry source provenance');
  for (const entry of exported.provenance) {
    for (const field of ['sourceId', 'citation', 'relation', 'text']) {
      assert.equal(typeof entry[field], 'string', `export provenance ${field} should be a string`);
      assert.ok(entry[field].length > 0, `export provenance ${field} should be populated`);
    }
  }
  assert.deepEqual(exported.provenance, provenance, 'export must preserve the source provenance');
  assert.equal(exported.validation.status, 'valid_non_executable');

  // Invalid time values cannot be exported or persisted over the saved valid revision.
  const invalidTime = structuredClone(originalRule);
  invalidTime.value.items = [{ condition: [{ field: 'start', comparison: { kind: 'time_window_overlap_comparison', start: '25:99', end: 'garbage' } }], value: originalRule.value.default }];
  await editor.fill(JSON.stringify(invalidTime, null, 2));
  await page.getByText('Needs correction', { exact: true }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Save locally' }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), true);
  assert.equal(await page.getByText(/ENGINE_DISCONNECTED/).count(), 0);
  const persistedDuringInvalid = await page.evaluate((id) => JSON.parse(localStorage.getItem(`airspec.rule-draft:${id}`)), firstModel.id);
  assert.equal(persistedDuringInvalid.revision, 1);
  assert.deepEqual(persistedDuringInvalid.rule, originalRule);

  // JSON numeric overflow parses as Infinity in JavaScript, so reject it before save/export and keep the raw editor text.
  const overflowDraft = structuredClone(originalRule);
  overflowDraft.value.default = { kind: 'number_value', number: 'AIRSPEC_OVERFLOW_SENTINEL' };
  const overflowText = JSON.stringify(overflowDraft, null, 2).replace('"AIRSPEC_OVERFLOW_SENTINEL"', '1e400');
  await editor.fill(overflowText);
  await page.getByText('Needs correction', { exact: true }).waitFor();
  await page.getByText(/survive JSON serialization and parsing unchanged/).waitFor();
  assert.equal(await editor.inputValue(), overflowText, 'rejecting 1e400 must not normalize or erase the editor text');
  const overflowDiff = await page.locator('.diff-row').filter({ hasText: 'value.default.number' }).innerText();
  assert.match(overflowDiff, /Infinity/, 'the changed-path view should show the parsed overflow value instead of JSON null');
  assert.equal(await page.getByRole('button', { name: 'Save locally' }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), true);
  const persistedDuringOverflow = await page.evaluate((id) => JSON.parse(localStorage.getItem(`airspec.rule-draft:${id}`)), firstModel.id);
  assert.equal(persistedDuringOverflow.revision, 1);
  assert.deepEqual(persistedDuringOverflow.rule, originalRule, 'overflow rejection must retain the prior safe stored revision');
  await editor.fill(JSON.stringify(originalRule, null, 2));
  await page.getByText('Valid · non-executable', { exact: true }).waitFor();

  // Dirty edits survive definition and workspace navigation.
  const changed = structuredClone(originalRule);
  changed.name = `${originalRule.name} — unsaved smoke edit`;
  await editor.fill(JSON.stringify(changed, null, 2));
  const otherOption = page.getByRole('option').nth(1);
  const otherName = (await otherOption.locator('strong').innerText()).trim();
  await otherOption.click();
  assert.equal(JSON.parse(await editor.inputValue()).name, otherName, 'definition switch selects its own draft');
  await page.getByRole('option').first().click();
  assert.equal(JSON.parse(await editor.inputValue()).name, changed.name, 'switching back restores the unsaved per-definition draft');
  await page.getByRole('button', { name: 'Source explorer', exact: true }).click();
  await page.getByRole('button', { name: 'Rule workshop', exact: true }).click();
  assert.equal(JSON.parse(await editor.inputValue()).name, changed.name, 'switching workspaces preserves unsaved edits');

  // Export commits dirty edits before assigning revision and filename. Repeated export is stable.
  const firstDownloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export versioned JSON' }).click();
  const firstDownload = await firstDownloadPromise;
  const firstExport = JSON.parse(await readFile(await firstDownload.path(), 'utf8'));
  assert.equal(firstExport.revision, 2, 'an edited initial catalogue revision must export as the next revision');
  assert.equal(firstDownload.suggestedFilename(), `${firstExport.definitionId}-r${firstExport.revision}.airspec.json`);
  assert.equal(firstExport.rule.name, changed.name);
  const secondDownloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export versioned JSON' }).click();
  const secondDownload = await secondDownloadPromise;
  const secondExport = JSON.parse(await readFile(await secondDownload.path(), 'utf8'));
  assert.equal(secondDownload.suggestedFilename(), firstDownload.suggestedFilename());
  assert.deepEqual(secondExport, firstExport, 'repeated export of the same saved revision must keep identity and contents coherent');

  // A stale tab must not overwrite a newer revision, then can explicitly restore and edit it.
  const staleEdit = structuredClone(JSON.parse(await staleEditor.inputValue()));
  staleEdit.name = 'Stale-tab edit';
  await staleEditor.fill(JSON.stringify(staleEdit, null, 2));
  await stalePage.getByRole('button', { name: 'Save locally' }).click();
  await stalePage.getByText(/changed in another tab/).waitFor();
  const persistedAfterStaleSave = await page.evaluate((id) => JSON.parse(localStorage.getItem(`airspec.rule-draft:${id}`)), firstModel.id);
  assert.equal(persistedAfterStaleSave.revision, 2);
  assert.equal(persistedAfterStaleSave.rule.name, changed.name);
  const unexpectedDownload = stalePage.waitForEvent('download', { timeout: 300 }).then(() => true, () => false);
  await stalePage.getByRole('button', { name: 'Export versioned JSON' }).click();
  assert.equal(await unexpectedDownload, false, 'stale export must be blocked instead of generating a colliding revision');
  const persistedAfterStaleExport = await page.evaluate((id) => JSON.parse(localStorage.getItem(`airspec.rule-draft:${id}`)), firstModel.id);
  assert.equal(persistedAfterStaleExport.revision, 2);
  assert.equal(persistedAfterStaleExport.rule.name, changed.name);

  // The reported A -> Reload source -> B flow must allocate the next revision.
  await page.getByRole('button', { name: 'Reload source' }).click();
  assert.equal(JSON.parse(await editor.inputValue()).name, firstModel.name);
  const afterReset = structuredClone(JSON.parse(await editor.inputValue()));
  afterReset.name = 'Edited after source reset';
  await editor.fill(JSON.stringify(afterReset, null, 2));
  const resetDownloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export versioned JSON' }).click();
  const resetDownload = await resetDownloadPromise;
  const resetExport = JSON.parse(await readFile(await resetDownload.path(), 'utf8'));
  assert.equal(resetExport.revision, 3, 'reload source must preserve revision 2 as the high-water mark');
  assert.equal(resetExport.rule.name, afterReset.name);

  // The stale tab can restore the reset edit, then create the next revision.
  await stalePage.getByRole('button', { name: 'Restore saved' }).click();
  assert.equal(JSON.parse(await staleEditor.inputValue()).name, afterReset.name);
  const concurrentEdit = structuredClone(JSON.parse(await staleEditor.inputValue()));
  concurrentEdit.name = 'Concurrent-tab edit';
  await staleEditor.fill(JSON.stringify(concurrentEdit, null, 2));
  const concurrentDownloadPromise = stalePage.waitForEvent('download');
  await stalePage.getByRole('button', { name: 'Export versioned JSON' }).click();
  const concurrentDownload = await concurrentDownloadPromise;
  const concurrentExport = JSON.parse(await readFile(await concurrentDownload.path(), 'utf8'));
  assert.equal(concurrentExport.revision, 4);
  assert.equal(concurrentExport.rule.name, concurrentEdit.name);

  // A stale source reset must not erase a newer other-tab revision.
  await page.getByRole('button', { name: 'Reload source' }).click();
  await page.getByText(/changed in another tab/).waitFor();
  const persistedAfterStaleReset = await page.evaluate((id) => JSON.parse(localStorage.getItem(`airspec.rule-draft:${id}`)), firstModel.id);
  assert.equal(persistedAfterStaleReset.revision, 4);
  assert.equal(persistedAfterStaleReset.rule.name, concurrentEdit.name);
  await page.getByRole('button', { name: 'Restore saved' }).click();
  assert.equal(JSON.parse(await editor.inputValue()).name, concurrentEdit.name);
  await page.getByRole('button', { name: 'Reload source' }).click();
  assert.equal(JSON.parse(await editor.inputValue()).name, firstModel.name);
  const afterSecondReset = structuredClone(JSON.parse(await editor.inputValue()));
  afterSecondReset.name = 'Edited after second source reset';
  await editor.fill(JSON.stringify(afterSecondReset, null, 2));
  const secondResetDownloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export versioned JSON' }).click();
  const secondResetDownload = await secondResetDownloadPromise;
  const secondResetExport = JSON.parse(await readFile(await secondResetDownload.path(), 'utf8'));
  assert.equal(secondResetExport.revision, 5, 'source resets must preserve the maximum issued revision');
  assert.equal(secondResetExport.rule.name, afterSecondReset.name);

  const unsaved = { ...afterSecondReset, name: 'Unsaved smoke edit' };
  await editor.fill(JSON.stringify(unsaved, null, 2));
  await page.getByRole('button', { name: 'Cancel edits' }).click();
  assert.equal(JSON.parse(await editor.inputValue()).name, afterSecondReset.name, 'cancel should restore the persisted export revision');
  await page.reload({ waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Rule workshop', exact: true }).click();
  await page.getByText('Restored the locally saved revision.', { exact: true }).waitFor();
  assert.equal(JSON.parse(await editor.inputValue()).name, afterSecondReset.name, 'saved revision should survive a page reload');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(100);
  const mobileGeometry = await getWorkshopGeometry(page);
  assert.equal(mobileGeometry.panelDisplay, 'flex');
  assert.ok(mobileGeometry.workshop.width <= mobileGeometry.viewport.width && mobileGeometry.workshop.width > 300, 'mobile workshop should fit the viewport width');
  assert.ok(mobileGeometry.workshop.height > 500 && mobileGeometry.workshop.bottom <= mobileGeometry.app.bottom + 1, 'mobile workshop should fill the available vertical panel');
  assert.ok(mobileGeometry.bodyScrollHeight > mobileGeometry.bodyClientHeight, 'mobile workshop body should scroll its content instead of pushing the panel off screen');
  assert.ok(mobileGeometry.viewport.bodyWidth <= mobileGeometry.viewport.width, 'mobile layout should not overflow horizontally');
  assert.ok(pageErrors.length === 0 && stalePageErrors.length === 0, `page had uncaught errors: ${[...pageErrors, ...stalePageErrors].join('; ')}`);
  console.log('Rule Workshop browser smoke checks passed.');
} finally {
  await browser?.close();
  server.kill('SIGTERM');
}

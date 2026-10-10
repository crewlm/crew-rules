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
  await page.goto(baseUrl, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Rule workshop', exact: true }).click();
  const editor = page.getByRole('textbox', { name: 'AnyRule JSON draft' });
  await assert.doesNotReject(() => page.getByText('Valid · non-executable', { exact: true }).waitFor());
  const originalRule = JSON.parse(await editor.inputValue());

  // Invalid JSON is a parse failure, distinct from a valid but unsupported draft.
  await editor.fill('{');
  await page.getByText(/JSON parse error:/).waitFor();
  await page.getByText('Invalid JSON', { exact: true }).waitFor();
  assert.equal(await page.getByText(/SCOPE_INVALID/).count(), 0, 'a parse failure should not be reported as a structural validation error');
  assert.equal(await page.getByRole('button', { name: 'Save locally' }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), true);

  const malformed = structuredClone(originalRule);
  malformed.scope = 'invalid_scope';
  await editor.fill(JSON.stringify(malformed, null, 2));
  await page.getByText('Needs correction', { exact: true }).waitFor();
  await page.getByText(/must be one of the declared AnyRule scopes/).waitFor();
  assert.equal(await page.getByText(/JSON parse error:/).count(), 0, 'valid JSON with invalid structure should not be reported as a parse failure');
  assert.equal(await page.getByRole('button', { name: 'Save locally' }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Export versioned JSON' }).isDisabled(), true);

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

  // Save, make an unsaved change, cancel it, then reload and verify persistence.
  const changed = structuredClone(originalRule);
  changed.name = `${originalRule.name} — smoke saved`;
  await editor.fill(JSON.stringify(changed, null, 2));
  await page.getByRole('button', { name: 'Save locally' }).click();
  await page.getByText('Saved locally as revision 1.').waitFor();
  const savedText = await editor.inputValue();
  const unsaved = { ...changed, name: 'Unsaved smoke edit' };
  await editor.fill(JSON.stringify(unsaved, null, 2));
  await page.getByRole('button', { name: 'Cancel edits' }).click();
  assert.deepEqual(JSON.parse(await editor.inputValue()), JSON.parse(savedText), 'cancel should restore the saved revision');
  await page.reload({ waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Rule workshop', exact: true }).click();
  await page.getByText('Restored the locally saved revision.', { exact: true }).waitFor();
  assert.equal(JSON.parse(await editor.inputValue()).name, changed.name, 'saved revision should survive a page reload');
  console.log('Rule Workshop browser smoke checks passed.');
} finally {
  await browser?.close();
  server.kill('SIGTERM');
}

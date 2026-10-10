import { useMemo, useState } from 'react';
import { findParagraph, findTopicForParagraph, linksForModel } from '../data.js';
import { diffRuleDraft, exportRuleDraft, makeRuleDraft, validateRuleDraft } from '../airspec.js';
import { clearDraftLocally, loadDraftLocally, saveDraftLocally } from '../draftStorage.js';

function isValidStoredDraft(value, baseline) {
  return value && value.definitionId === baseline.definitionId
    && value.basedOn?.sourceHash === baseline.basedOn.sourceHash
    && validateRuleDraft(value).status === 'valid_non_executable';
}

function initialDraftState(models, links, document, catalogueCommit) {
  const drafts = {};
  const savedDrafts = {};
  const texts = {};
  const notices = {};
  for (const model of models) {
    const baseline = makeRuleDraft(model, links, document, catalogueCommit);
    const stored = loadDraftLocally(localStorage, model.id);
    const validStored = isValidStoredDraft(stored, baseline) ? stored : null;
    const draft = validStored ?? baseline;
    drafts[model.id] = draft;
    savedDrafts[model.id] = validStored;
    texts[model.id] = JSON.stringify(draft.rule, null, 2);
    notices[model.id] = validStored ? 'Restored the locally saved revision.' : '';
  }
  return { drafts, savedDrafts, texts, notices };
}

function setForId(setter, id, value) {
  setter((current) => ({ ...current, [id]: typeof value === 'function' ? value(current[id]) : value }));
}

export function RuleWorkshop({ models, links, document, catalogueCommit }) {
  const [selectedId, setSelectedId] = useState(models[0]?.id ?? '');
  const [{ drafts: initialDrafts, savedDrafts: initialSaved, texts: initialTexts, notices: initialNotices }] = useState(() => initialDraftState(models, links, document, catalogueCommit));
  const [drafts, setDrafts] = useState(initialDrafts);
  const [savedDrafts, setSavedDrafts] = useState(initialSaved);
  const [texts, setTexts] = useState(initialTexts);
  const [parseErrors, setParseErrors] = useState({});
  const [notices, setNotices] = useState(initialNotices);
  const model = models.find((item) => item.id === selectedId) ?? models[0];
  const draft = drafts[selectedId] ?? (model && makeRuleDraft(model, links, document, catalogueCommit));
  const text = texts[selectedId] ?? JSON.stringify(draft?.rule ?? {}, null, 2);
  const parseError = parseErrors[selectedId] ?? '';
  const notice = notices[selectedId] ?? '';
  const baseline = useMemo(() => model && makeRuleDraft(model, links, document, catalogueCommit), [model, links, document, catalogueCommit]);
  const validation = useMemo(() => draft ? validateRuleDraft(draft) : { status: 'invalid', errors: [], unsupported: [] }, [draft]);
  const changes = useMemo(() => baseline && draft ? diffRuleDraft(baseline.rule, draft.rule) : [], [baseline, draft]);

  const updateText = (value) => {
    setForId(setTexts, selectedId, value);
    try {
      const rule = JSON.parse(value);
      setForId(setDrafts, selectedId, (current) => ({ ...current, rule }));
      setForId(setParseErrors, selectedId, '');
    } catch (error) {
      setForId(setParseErrors, selectedId, error.message);
    }
    setForId(setNotices, selectedId, '');
  };
  const writeDraft = (next, message) => {
    setForId(setDrafts, selectedId, next);
    setForId(setTexts, selectedId, JSON.stringify(next.rule, null, 2));
    setForId(setParseErrors, selectedId, '');
    setForId(setNotices, selectedId, message);
  };
  const commitDraft = (sourceDraft, announce = false) => {
    const currentSaved = savedDrafts[selectedId] ?? null;
    const reference = currentSaved ?? baseline;
    const referenceRule = reference?.rule;
    const changed = referenceRule ? diffRuleDraft(referenceRule, sourceDraft.rule).length > 0 : false;
    const next = { ...sourceDraft, revision: (reference?.revision ?? sourceDraft.revision ?? 1) + (changed ? 1 : 0) };
    saveDraftLocally(localStorage, next);
    setForId(setSavedDrafts, selectedId, next);
    writeDraft(next, announce ? `Saved locally as revision ${next.revision}.` : '');
    return next;
  };
  const save = () => {
    if (validation.status === 'invalid' || parseError || !draft) return;
    commitDraft(draft, true);
  };
  const restore = () => {
    const local = loadDraftLocally(localStorage, selectedId);
    if (!isValidStoredDraft(local, baseline)) {
      setForId(setSavedDrafts, selectedId, null);
      setForId(setNotices, selectedId, 'No valid saved local revision for this definition.');
      return;
    }
    setForId(setSavedDrafts, selectedId, local);
    writeDraft(local, `Restored local revision ${local.revision}.`);
  };
  const cancel = () => {
    const local = loadDraftLocally(localStorage, selectedId);
    const validSaved = isValidStoredDraft(local, baseline) ? local : null;
    setForId(setSavedDrafts, selectedId, validSaved);
    writeDraft(validSaved ?? baseline, validSaved ? 'Unsaved edits cancelled; restored the saved revision.' : 'Unsaved edits cancelled; restored the catalogue definition.');
  };
  const reloadSource = () => {
    clearDraftLocally(localStorage, selectedId);
    setForId(setSavedDrafts, selectedId, null);
    writeDraft(baseline, 'Reloaded the source-backed catalogue definition.');
  };
  const exportDraft = () => {
    if (validation.status !== 'valid_non_executable' || parseError || !draft) return;
    const persisted = commitDraft(draft);
    const blob = new Blob([`${JSON.stringify(exportRuleDraft(persisted), null, 2)}\n`], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = Object.assign(window.document.createElement('a'), { href: url, download: `${persisted.definitionId}-r${persisted.revision}.airspec.json` });
    anchor.click();
    URL.revokeObjectURL(url);
    setForId(setNotices, selectedId, 'Versioned definition exported with provenance.');
  };
  const sourceLinks = linksForModel(links, selectedId);

  return <section className="workshop" aria-label="AirSpec rule workshop">
    <header className="workshop-header">
      <div><h1>Rule workshop</h1><p>Browse source-backed catalogue draft interpretations and prepare a local draft.</p></div>
      <div className="engine-state"><span className="engine-indicator" /> <span><strong>Active engine</strong><small>Disconnected · export is non-executable</small></span></div>
    </header>
    <div className="workshop-body">
      <aside className="definition-browser">
        <div className="workshop-section-head"><h2>Catalogue draft interpretations</h2><span>{models.length} source-linked</span></div>
        <div className="definition-list" role="listbox" aria-label="Source-backed definitions">
          {models.map((item) => <button key={item.id} role="option" aria-selected={item.id === selectedId} className={`definition-option ${item.id === selectedId ? 'active' : ''}`} onClick={() => setSelectedId(item.id)}>
            <strong>{item.name}</strong><small>{item.status} · {linksForModel(links, item.id).length} source links</small>
          </button>)}
        </div>
        {model && <div className="definition-source">
          <h2>{model.name}</h2><div className="interpretation-label">Catalogue draft interpretation · not official EASA structured text</div><p className="definition-summary">{model.interpretation}</p>
          <div className="source-revision">{document.title} <span>·</span> {document.version}</div>
          {sourceLinks.map((link) => link.source_unit_ids.map((sourceId) => {
            const paragraph = findParagraph(document, sourceId);
            const topic = findTopicForParagraph(document, sourceId);
            return <article className="provenance-item" key={`${link.id}:${sourceId}`}>
              <div className="provenance-meta"><strong>EASA source · {paragraph?.citation || paragraph?.locator?.structural_path || sourceId}</strong><span>{link.relation}</span></div>
              <p>{paragraph?.text ?? 'Source text unavailable in this catalogue.'}</p>
              {link.note && <small>{link.note}</small>}
              {topic && <small className="topic-note">{topic.title}</small>}
            </article>;
          }))}
          {!!model.limitations?.length && <section className="coverage-gaps"><h3>Known coverage gaps</h3><p>Source-model limitations carried into exports for review.</p><ul>{model.limitations.map((limitation, index) => <li key={`${index}:${limitation}`}>{limitation}</li>)}</ul></section>}
        </div>}
      </aside>
      <section className="draft-editor" aria-label="Editable rule draft">
        <div className="draft-heading">
          <div><h2>Draft definition</h2><p>{model?.name} · revision {draft?.revision ?? '—'}</p></div>
          <span className={`validation-state ${parseError ? 'invalid' : validation.status}`}>{parseError ? 'Invalid JSON' : validation.status === 'invalid' ? 'Needs correction' : 'Valid · non-executable'}</span>
        </div>
        <label className="editor-label" htmlFor="rule-json">AnyRule JSON draft</label>
        <textarea id="rule-json" className="rule-json-editor" spellCheck="false" value={text} onChange={(event) => updateText(event.target.value)} aria-describedby="draft-help" />
        <p id="draft-help" className="editor-help">Only the AnyRule payload is editable. Catalogue identity, source hash, provenance links, and coverage gaps stay fixed from the selected source-backed definition.</p>
        <div className="validation-block" aria-live="polite">
          {parseError && <p className="issue error">JSON parse error: {parseError}</p>}
          {validation.errors.map((item, index) => <p key={`${item.path}:${index}`} className="issue error"><code>{item.path}</code> {item.message}</p>)}
          {validation.unsupported.map((item, index) => <p key={`${item.path}:${index}`} className="issue unsupported"><code>{item.code}</code> {item.message}</p>)}
        </div>
        <div className="draft-actions">
          <button className="primary-action" onClick={save} disabled={validation.status === 'invalid' || !!parseError}>Save locally</button>
          <button onClick={restore}>Restore saved</button>
          <button onClick={cancel}>Cancel edits</button>
          <button onClick={reloadSource}>Reload source</button>
          <button className="export-action" onClick={exportDraft} disabled={validation.status !== 'valid_non_executable' || !!parseError}>Export versioned JSON</button>
        </div>
        {notice && <p className="workshop-notice" role="status">{notice}</p>}
        <div className="diff-panel"><div className="workshop-section-head"><h3>Changed paths</h3><span>{changes.length} changes</span></div>
          {!changes.length && <p className="empty-diff">No changes from the catalogue definition.</p>}
          {changes.slice(0, 20).map((change) => <div className="diff-row" key={change.path}><code>{change.path}</code><span>{JSON.stringify(change.before) ?? '—'} <b>→</b> {JSON.stringify(change.after) ?? '—'}</span></div>)}
          {changes.length > 20 && <p className="empty-diff">Showing first 20 of {changes.length} changed paths.</p>}
        </div>
        <details className="provenance-json"><summary>Export provenance <span>{draft?.provenance?.length ?? 0} source links</span></summary><pre>{JSON.stringify(draft?.provenance ?? [], null, 2)}</pre></details>
        <details className="provenance-json"><summary>Catalogue identity <span>read-only</span></summary><pre>{JSON.stringify({ definitionId: draft?.definitionId, revision: draft?.revision, basedOn: draft?.basedOn, coverageGaps: draft?.coverageGaps }, null, 2)}</pre></details>
      </section>
    </div>
    <footer className="workshop-footer"><span>Source subset: EASA Air Operations, Revision 24 (March 2026)</span><span>Not a complete legality coverage claim · engine disconnected</span></footer>
  </section>;
}

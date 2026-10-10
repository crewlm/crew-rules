import { useMemo, useState } from 'react';
import { findParagraph, findTopicForParagraph, formatValue, humanizeKey, linksForModel, normalizeSearchText, sourceReferencesForModel } from '../data.js';

const MODEL_STAGES = [
  ['input', 'Input'], ['applicability', 'Applicability'], ['value', 'Value'], ['requirement', 'Requirement'], ['limit', 'Limit'],
  ['value_updates', 'Value updates'], ['requirement_updates', 'Requirement updates'], ['limit_updates', 'Limit updates'],
];

function compactObject(value) {
  if (value == null) return 'Not specified';
  if (typeof value !== 'object') return formatValue(value);
  if (Array.isArray(value)) return value.length ? value.map(formatValue).join('; ') : 'None';
  return Object.entries(value).filter(([, child]) => child !== undefined && child !== null).map(([key, child]) => `${humanizeKey(key)}: ${formatValue(child)}`).join(' · ') || 'Not specified';
}

function durationLabel(value) {
  const match = String(value ?? '').match(/^(-)?PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$/);
  if (!match) return String(value ?? '');
  const amount = (Number(match[2] || 0) + Number(match[3] || 0) / 60 + Number(match[4] || 0) / 3600) * (match[1] ? -1 : 1);
  return `${Number.isInteger(amount) ? amount : amount.toFixed(1)} hours`;
}

function valueSummary(value) {
  if (value == null) return 'Not specified';
  if (typeof value !== 'object') return formatValue(value);
  const kind = value.kind ?? '';
  if (kind === 'applicable_value') return value.applicable ? 'Applicable' : 'Not applicable';
  const phrase = value.phrase && value.phrase !== 'Matched' ? value.phrase : '';
  const details = [];
  if (value.field) details.push(value.field.replaceAll('.', ' '));
  if (value.start_field || value.end_field) details.push(`${value.start_field?.replaceAll('.', ' ') || 'start'} to ${value.end_field?.replaceAll('.', ' ') || 'end'}`);
  if (value.clamp_lower != null) details.push(`minimum ${value.clamp_lower} hours`);
  if (value.clamp_upper != null) details.push(`maximum ${value.clamp_upper} hours`);
  if (value.duration != null) details.push(durationLabel(value.duration));
  if (value.number != null) details.push(`${value.number} hours`);
  if (value.lower != null || value.upper != null) details.push(`${value.lower ?? '…'} to ${value.upper ?? '…'}`);
  if (value.table_name) details.push(`lookup in ${value.table_name}`);
  if (value.code) details.push(`${value.code} ${value.element ?? 'aggregate'}`);
  if (value.tag) details.push(value.tag);
  return [phrase, ...details].filter(Boolean).join(' · ') || kind.replaceAll('_', ' ');
}

function conditionSummary(conditions = []) {
  return conditions.map((item) => {
    const field = (item.field ?? 'input').replaceAll('_', ' ');
    const comparison = item.comparison ?? {};
    const kind = comparison.kind ?? '';
    let test = comparison.number ?? comparison.text ?? comparison.duration ?? comparison.items?.join(', ') ?? '';
    if (kind === 'truth_comparison') test = 'is true';
    if (kind === 'false_comparison') test = 'is false';
    if (kind.startsWith('ge_')) test = `at least ${durationLabel(test)}`;
    else if (kind.startsWith('le_')) test = `at most ${durationLabel(test)}`;
    else if (kind.startsWith('gt_')) test = `greater than ${durationLabel(test)}`;
    else if (kind.startsWith('lt_')) test = `less than ${durationLabel(test)}`;
    else if (kind.startsWith('equal_')) test = `equals ${durationLabel(test)}`;
    else if (kind === 'range_number_comparison' || kind === 'range_duration_comparison') test = `between ${durationLabel(comparison.lower)} and ${durationLabel(comparison.upper)}`;
    if (item.reverse_match) test = `not ${test}`;
    return `${field} ${test}`;
  }).join(' and ');
}

function decisionTableSummary(table) {
  if (!table || typeof table !== 'object') return valueSummary(table);
  const fallback = valueSummary(table.default);
  const cases = (table.items ?? []).map((item) => {
    const when = conditionSummary(item.condition);
    const value = valueSummary(item.value);
    return `${when ? `When ${when}: ` : ''}${value}`;
  });
  return [fallback ? `Otherwise ${fallback.toLowerCase()}` : '', ...cases].filter(Boolean).join('; ') || 'No values defined';
}

function citationLabel(document, paragraphId) {
  const paragraph = findParagraph(document, paragraphId);
  if (!paragraph) return '';
  const fullCitation = String(paragraph.citation ?? '').match(/^(?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3})(?:\([^)]+\))+/);
  if (fullCitation) return fullCitation[0];
  const inline = String(paragraph.text ?? '').match(/^\s*((?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3})(?:\([^)]+\))*)/);
  if (inline?.[1] && /\([^)]+\)/.test(inline[1])) return inline[1];
  const topic = findTopicForParagraph(document, paragraphId);
  const sectionCode = String(topic?.title ?? '').match(/^(?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3})/);
  const marker = String(paragraph.text ?? '').match(/^\s*((?:\([^)]+\))+)(?:\s|$)/);
  return `${sectionCode?.[0] ?? ''}${marker?.[1] ?? ''}` || paragraph.citation || 'Source passage';
}

function FlowStages({ model }) {
  const rule = model.model ?? {};
  const present = MODEL_STAGES.filter(([key]) => key === 'input' || (rule[key] !== undefined && rule[key] !== null && !(Array.isArray(rule[key]) && !rule[key].length)));
  if (!present.length) return <div className="model-json-only">Structured flow is not available for this draft.</div>;
  return <div className="model-flow">{present.map(([key, label], index) => <div className="flow-step-wrap" key={key}>
    {index > 0 && <div className="flow-arrow" aria-hidden="true">↓</div>}
    <div className="flow-step"><div className="flow-label">{label}</div><div className="flow-value"><strong>{key === 'input' ? rule.name || rule.scope?.replaceAll('_', ' ') || 'Rule inputs' : label}</strong>
      <span>{key === 'input' ? `${rule.scope?.replaceAll('_', ' ') || 'Entity'} data${rule.time_period ? ` · ${compactObject(rule.time_period)}` : ''}` : ['value_updates', 'requirement_updates', 'limit_updates'].includes(key) ? `${rule[key].length} update${rule[key].length === 1 ? '' : 's'}` : ['applicability', 'value', 'requirement', 'limit'].includes(key) ? decisionTableSummary(rule[key]) : compactObject(rule[key])}</span></div></div>
  </div>)}</div>;
}

function ModelDetail({ model, links, document, onNavigateReference }) {
  const [jsonOpen, setJsonOpen] = useState(false);
  const references = sourceReferencesForModel(links, model.id);
  const allLinks = linksForModel(links, model.id);
  return <article className="model-detail">
    <div className="model-title-row"><h2>{model.name}</h2><span className="draft-tag">{model.status || 'draft'} mapping</span></div>
    {model.interpretation && <p className="interpretation">{model.interpretation}</p>}
    {model.limitations?.length > 0 && <section className="limitations"><h3>Draft limitations</h3>
      <ul>{[model.limitations[0], model.limitations.find((item) => item.toLowerCase().includes('complete'))].filter(Boolean).map((limitation, index) => <li key={`${index}-${limitation}`}>{limitation}</li>)}</ul>
      <details className="more-limitations"><summary>All draft limitations ({model.limitations.length})</summary><ul>{model.limitations.map((limitation, index) => <li key={`${index}-${limitation}`}>{limitation}</li>)}</ul></details>
    </section>}
    <section className="reference-section" aria-labelledby="reference-heading"><h3 id="reference-heading">Source references <span>{references.length}</span></h3>
      {references.length ? <div className="reference-list">{references.map(({ link, paragraphId }, index) => <button key={`${link.id}-${paragraphId}-${index}`} className="reference-button" onClick={() => onNavigateReference(paragraphId)}>
        <span className="reference-icon" aria-hidden="true">§</span><span>{citationLabel(document, paragraphId)}</span><span className={`relation-tag ${link.relation === 'context' ? 'context' : ''}`}>{link.relation === 'context' ? 'Context' : 'Models'}</span>
      </button>)}</div> : <p className="muted-copy">No source references linked.</p>}
      {allLinks.some((link) => link.note) && <div className="link-notes">{allLinks.filter((link) => link.note).map((link) => <p key={link.id}><span>{link.relation === 'context' ? 'Context' : 'Mapping'}:</span> {link.note}</p>)}</div>}
    </section>
    <section className="logic-section"><h3>Rule logic</h3><FlowStages model={model} /></section>
    {model.mermaid && <details className="diagram-disclosure"><summary>Rule flow source</summary><pre>{model.mermaid}</pre></details>}
    <details className="json-disclosure" open={jsonOpen} onToggle={(event) => setJsonOpen(event.currentTarget.open)}>
      <summary><span className="chevron" aria-hidden="true">›</span> Model JSON</summary>
      <pre>{JSON.stringify(model.model, null, 2)}</pre>
    </details>
  </article>;
}

export function ModelPane({ models, links, document, selectedModel, relatedModels, selectedParagraphId, selectedModelId, onSelectModel, onNavigateReference }) {
  const [query, setQuery] = useState('');
  const visibleModels = useMemo(() => {
    const source = models;
    const lowered = normalizeSearchText(query);
    return lowered ? source.filter((model) => normalizeSearchText(`${model.name} ${model.interpretation ?? ''} ${(model.limitations ?? []).join(' ')}`).includes(lowered)) : source;
  }, [models, query, relatedModels, selectedParagraphId]);
  const selectedIsHidden = selectedModel && !visibleModels.some((model) => model.id === selectedModel.id);
  return <section className="pane model-pane" aria-labelledby="model-title">
    <div className="pane-heading model-pane-heading"><h1 id="model-title">Rule model</h1>
      <label className="search-field model-search"><span className="sr-only">Search rules</span><span className="search-icon" aria-hidden="true" />
        <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search rules" />
        {query && <button type="button" className="clear-search" aria-label="Clear rule search" onClick={() => setQuery('')}>×</button>}
      </label>
      {selectedParagraphId && <p className="model-list-context">{relatedModels.length ? `${relatedModels.length} model${relatedModels.length === 1 ? '' : 's'} linked to this source` : 'No linked rule model for this source'}</p>}
    </div>
    <div className="model-list" role="listbox" aria-label="Rule models">
      {visibleModels.map((model) => <button type="button" role="option" aria-selected={selectedModel?.id === model.id} key={model.id} className={`model-list-item ${selectedModel?.id === model.id ? 'active' : ''}`} onClick={() => onSelectModel(model.id)}>
      <span className="model-list-name">{model.name}</span><span className="model-list-meta">{selectedParagraphId && linksForModel(links, model.id).some((link) => link.source_unit_ids?.includes(selectedParagraphId)) && <span className="linked-indicator">{linksForModel(links, model.id).some((link) => link.source_unit_ids?.includes(selectedParagraphId) && link.relation === 'context') ? 'Context' : 'Linked'}</span>}<span className="model-list-status">{model.status || 'draft'}</span></span>
      </button>)}
      {visibleModels.length === 0 && <div className="model-list-empty">No rules match this search.</div>}
    </div>
    {selectedIsHidden && <div className="search-destination-note">The selected linked model is outside these search results and remains open below.</div>}
    <div className="model-detail-scroll" key={selectedModel?.id ?? 'none'}>
      {selectedModel ? <ModelDetail key={selectedModel.id} model={selectedModel} links={links} document={document} onNavigateReference={onNavigateReference} />
        : <div className="no-model-state"><div className="empty-symbol" aria-hidden="true">↔</div><h2>{selectedParagraphId ? 'No linked rule model' : 'Select a rule model'}</h2><p>{selectedParagraphId ? 'This passage has no rule mapping in the current catalogue.' : 'Choose a draft model to see its interpretation, source references, and structured logic.'}</p></div>}
    </div>
    <footer className="pane-footer"><span>{selectedModel ? `${linksForModel(links, selectedModel.id).length} linked source relationships` : `${models.length} draft models`}</span><span>Draft mappings for review</span></footer>
  </section>;
}

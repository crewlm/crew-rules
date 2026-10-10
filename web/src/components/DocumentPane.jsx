import { useEffect, useMemo, useState } from 'react';
import { allParagraphs, findTopicForParagraph, linksForParagraph, normalizeSearchText, paragraphsForUnit, relationLabel, searchableParagraphText } from '../data.js';

function Highlight({ text, query }) {
  const safe = String(text ?? '');
  const needle = query.trim();
  if (!needle) return safe;
  const escaped = needle.trim().split(/\s+/u).map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+');
  const pieces = safe.split(new RegExp(`(${escaped})`, 'ig'));
  return pieces.map((piece, index) => new RegExp(`^${escaped}$`, 'i').test(piece)
    ? <mark key={`${piece}-${index}`}>{piece}</mark> : piece);
}

function LocatorText({ paragraph, query }) {
  const sourceText = String(paragraph.text ?? '');
  const prefixedCode = sourceText.match(/^\s*(?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3})(\([^)]+\)(?:\([^)]+\))*)/);
  const leadingMarker = sourceText.match(/^\s*((?:\([^)]+\))+)(?:\s|$)/);
  const citationCode = String(paragraph.citation ?? '').match(/^(?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3})((?:\([^)]+\))+)/);
  const label = prefixedCode?.[1] || leadingMarker?.[1] || citationCode?.[1] || '';
  return <span className="locator-text" title={paragraph.id}><Highlight text={label} query={query} /></span>;
}

function preciseCitation(paragraph) {
  return String(paragraph.citation ?? '').match(/^(?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3})(?:\([^)]+\))+/)?.[0] ?? '';
}

function textWithoutLeadingLocator(paragraph) {
  const text = String(paragraph.text ?? '');
  return text.replace(/^\s*(?:(?:ORO\.FTL\.\d{3}|CS FTL\.1\.\d{3})(?:\([^)]+\))*)?\s*((?:\([^)]+\))+)(?=\s)/, '').trimStart();
}

function SourceParagraph({ paragraph, query, selected, relations, onSelect, onSelectModel, register }) {
  if (!String(paragraph.text ?? '').trim()) return <span className="empty-source-anchor" ref={(node) => register(paragraph.id, node)} tabIndex="-1" aria-label="Empty source paragraph" />;
  const choose = (event) => {
    const selection = window.getSelection();
    if (selection?.toString() && event.currentTarget.contains(selection.anchorNode)) return;
    onSelect(paragraph.id);
  };
  return <article
    ref={(node) => register(paragraph.id, node)}
    className={`source-paragraph ${selected ? 'is-selected' : ''}`}
    tabIndex="0"
    aria-current={selected ? 'location' : undefined}
    aria-label={`${paragraph.citation || 'Source passage'}: ${paragraph.text}`}
    onClick={choose}
    onKeyDown={(event) => {
      if (event.target !== event.currentTarget) return;
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(paragraph.id); }
    }}
  >
    <div className="paragraph-locator"><LocatorText paragraph={paragraph} query={query} /></div>
    <div className="paragraph-content"><p><Highlight text={textWithoutLeadingLocator(paragraph)} query={query} /></p>
      {preciseCitation(paragraph) && <span className="paragraph-citation">{preciseCitation(paragraph)}</span>}
      {relations.length > 0 && <div className="paragraph-links" onClick={(event) => event.stopPropagation()}>
        <span className="related-caption">{relations.length} linked {relations.length === 1 ? 'model' : 'models'}</span>
        {relations.map(({ link, model }) => model && <button
          type="button" className="related-model-link" key={`${link.id}-${model.id}`}
          onClick={() => onSelectModel(model.id, paragraph.id)} title={`${relationLabel(link.relation)}: ${model.name}`}
        >{model.name}<span className={`relation-tag ${link.relation === 'context' ? 'context' : ''}`}>{relationLabel(link.relation)}</span></button>)}
      </div>}
    </div>
  </article>;
}

function SourceTable({ unit, query, selectedParagraphId, links, models, onSelectParagraph, onSelectModel, register }) {
  const rows = (unit.rows ?? []).map((row) => row.map((cell) => ({ ...cell, paragraphs: [...(cell.paragraphs ?? [])] })));
  rows.forEach((row, rowIndex) => row.forEach((cell, columnIndex) => {
    if (cell.vertical_merge !== 'continue') return;
    const retained = cell.paragraphs.filter((paragraph) => String(paragraph.text ?? '').trim());
    for (let originRow = rowIndex - 1; originRow >= 0 && retained.length; originRow -= 1) {
      const origin = rows[originRow]?.[columnIndex];
      if (!origin) continue;
      if (origin.vertical_merge === 'restart') {
        origin.paragraphs.push(...retained);
        break;
      }
    }
  }));
  return <div className="source-table-wrap"><table className="source-table">
    <tbody>{rows.map((row, rowIndex) => <tr key={`${unit.id}-${rowIndex}`}>
      {row.map((cell, cellIndex) => cell.vertical_merge === 'continue' ? null : <td key={`${unit.id}-${rowIndex}-${cellIndex}`} colSpan={cell.colspan || undefined} rowSpan={cell.rowspan || undefined}>
        {(cell.paragraphs ?? []).map((paragraph) => <SourceParagraph
          key={paragraph.id} paragraph={paragraph} query={query} selected={selectedParagraphId === paragraph.id}
          relations={linksForParagraph(links, paragraph.id).map((link) => ({ link, model: models.find((item) => item.id === link.model_id) }))}
          onSelect={onSelectParagraph} onSelectModel={onSelectModel} register={register}
        />)}
      </td>)}
    </tr>)}</tbody>
  </table></div>;
}

export function DocumentPane({ documents, document, links, models, selectedParagraphId, onSelectDocument, onSelectParagraph, onSelectModel, paragraphRefs, revealRevision, shouldRevealSource }) {
  const [query, setQuery] = useState('');
  const topics = document.topics ?? [];
  const topic = findTopicForParagraph(document, selectedParagraphId) ?? topics[0];
  const [activeTopicId, setActiveTopicId] = useState(null);
  const activeTopic = topics.find((item) => item.id === activeTopicId) ?? topic;
  const railRefs = useMemo(() => new Map(), []);
  useEffect(() => {
    if (selectedParagraphId) setActiveTopicId(findTopicForParagraph(document, selectedParagraphId)?.id ?? null);
  }, [document, selectedParagraphId]);
  useEffect(() => {
    const item = activeTopic && railRefs.get(activeTopic.id);
    item?.scrollIntoView({ block: 'nearest' });
  }, [activeTopic, railRefs]);
  useEffect(() => {
    if (!selectedParagraphId || !shouldRevealSource) return undefined;
    const timer = window.setTimeout(() => {
      const element = paragraphRefs.current.get(selectedParagraphId);
      if (!element) return;
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      element.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
      element.focus({ preventScroll: true });
    }, 60);
    return () => window.clearTimeout(timer);
  }, [document, paragraphRefs, revealRevision, selectedParagraphId, shouldRevealSource]);
  const topicHits = useMemo(() => {
    const lowered = normalizeSearchText(query);
    if (!lowered) return topics;
    return topics.filter((item) => normalizeSearchText(`${item.id} ${item.title} ${(item.units ?? []).flatMap(paragraphsForUnit).map(searchableParagraphText).join(' ')}`).includes(lowered));
  }, [topics, query]);
  const register = (id, node) => {
    if (node) paragraphRefs.current.set(id, node); else paragraphRefs.current.delete(id);
  };
  const handleSelectParagraph = (id) => {
    setActiveTopicId(findTopicForParagraph(document, id)?.id ?? null);
    onSelectParagraph(id);
  };
  const setQueryAndRevealSelection = (value) => {
    setQuery(value);
    if (selectedParagraphId) setActiveTopicId(findTopicForParagraph(document, selectedParagraphId)?.id ?? null);
  };

  return <section className="pane document-pane" aria-labelledby="requirements-title">
    <div className="pane-heading"><h1 id="requirements-title">Requirement documents</h1>
      <div className="document-meta-row">
        <label className="select-field"><span>Document</span><select value={document.id} onChange={(event) => onSelectDocument(event.target.value)} aria-label="Requirement document">
          {documents.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}
        </select></label>
        <div className="select-field"><span>Revision</span><div className="revision-value" aria-label={`Revision ${document.version || document.title}`}>{document.version || document.title}</div></div>
      </div>
      <label className="search-field source-search"><span className="sr-only">Search source paragraphs</span><span className="search-icon" aria-hidden="true" />
        <input type="search" value={query} onChange={(event) => setQueryAndRevealSelection(event.target.value)} placeholder="Search paragraphs" />
        {query && <button type="button" className="clear-search" aria-label="Clear source search" onClick={() => setQueryAndRevealSelection('')}>×</button>}
      </label>
      <div className="source-search-hint" aria-live="polite">{query ? `${topicHits.length} matching sections · all source text stays available` : <><a href={document.publisher_url} target="_blank" rel="noreferrer">Open publisher source ↗</a><span>{document.sha256 ? `SHA-256 ${document.sha256.slice(0, 12)}…` : ''}</span></>}</div>
    </div>
    <div className="source-workspace">
      <aside className="section-rail" aria-label="Document sections">
        <div className="rail-heading">Sections <span>{topicHits.length}</span></div>
        <div className="section-list">
          {topicHits.map((item) => <button ref={(node) => node ? railRefs.set(item.id, node) : railRefs.delete(item.id)} key={item.id} className={`section-button ${activeTopic?.id === item.id ? 'active' : ''}`} onClick={() => setActiveTopicId(item.id)} title={item.title}>
            <span>{item.title}</span>
          </button>)}
          {topicHits.length === 0 && <div className="empty-rail">No section matches. Search results do not remove document text.</div>}
        </div>
      </aside>
      <div className="source-content" key={activeTopic?.id}>
        {activeTopic ? <>
          <div className="topic-header"><h2>{activeTopic.title}</h2><span className="content-type">{activeTopic.content_type || 'Requirement'}</span></div>
          <div className="topic-body">
            {(activeTopic.units ?? []).map((unit) => unit.kind === 'paragraph'
              ? <SourceParagraph key={unit.id} paragraph={unit} query={query} selected={selectedParagraphId === unit.id}
                relations={linksForParagraph(links, unit.id).map((link) => ({ link, model: models.find((item) => item.id === link.model_id) }))}
                onSelect={handleSelectParagraph} onSelectModel={onSelectModel} register={register} />
              : <SourceTable key={unit.id} unit={unit} query={query} selectedParagraphId={selectedParagraphId} links={links} models={models}
                onSelectParagraph={handleSelectParagraph} onSelectModel={onSelectModel} register={register} />)}
          </div>
        </> : <div className="empty-content">No sections in this document.</div>}
      </div>
    </div>
    <footer className="pane-footer"><span>{document.publisher || 'Source document'}</span><span>{allParagraphs(document).length.toLocaleString()} source passages</span></footer>
  </section>;
}

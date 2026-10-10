import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { loadCatalogue, findParagraph, findTopicForParagraph, linksForParagraph } from './data.js';
import { DocumentPane } from './components/DocumentPane.jsx';
import { ModelPane } from './components/ModelPane.jsx';
import { RuleWorkshop } from './components/RuleWorkshop.jsx';

function readLocation() {
  const params = new URLSearchParams(window.location.search);
  return { documentId: params.get('doc'), paragraphId: params.get('source'), modelId: params.get('model') };
}

export default function App() {
  const [catalogue, setCatalogue] = useState(null);
  const [error, setError] = useState('');
  const [location, setLocation] = useState(readLocation);
  const [activeMobilePane, setActiveMobilePane] = useState('source');
  const [activeView, setActiveView] = useState('explorer');
  const paragraphRefs = useRef(new Map());
  const [revealRevision, setRevealRevision] = useState(0);
  const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 680px)').matches);

  useEffect(() => {
    let alive = true;
    loadCatalogue().then((data) => { if (alive) setCatalogue(data); })
      .catch((reason) => { if (alive) setError(reason.message); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    const handlePop = () => {
      const nextLocation = readLocation();
      setLocation(nextLocation);
      setActiveMobilePane(nextLocation.modelId ? 'rules' : 'source');
    };
    window.addEventListener('popstate', handlePop);
    return () => window.removeEventListener('popstate', handlePop);
  }, []);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 680px)');
    const handleChange = () => setIsMobile(media.matches);
    media.addEventListener('change', handleChange);
    return () => media.removeEventListener('change', handleChange);
  }, []);

  const documents = catalogue?.documents ?? [];
  const currentDocument = documents.find((item) => item.id === location.documentId) ?? documents[0];
  const models = catalogue?.models ?? [];
  const links = catalogue?.links ?? [];
  const relatedLinks = useMemo(() => location.paragraphId
    ? linksForParagraph(links, location.paragraphId)
    : [], [links, location.paragraphId]);
  const relatedModels = useMemo(() => [...new Map(relatedLinks.map((link) => models.find((model) => model.id === link.model_id))
    .filter(Boolean).map((model) => [model.id, model])).values()], [relatedLinks, models]);
  const selectedModel = models.find((model) => model.id === location.modelId) ?? relatedModels[0] ?? null;
  const invalidSelection = catalogue && ((location.documentId && !documents.some((d) => d.id === location.documentId))
    || (location.paragraphId && !findParagraph(currentDocument, location.paragraphId))
    || (location.modelId && !models.some((model) => model.id === location.modelId)));

  const updateUrl = useCallback((next, replace = false) => {
    const params = new URLSearchParams();
    if (next.documentId) params.set('doc', next.documentId);
    if (next.paragraphId) params.set('source', next.paragraphId);
    if (next.modelId) params.set('model', next.modelId);
    const query = params.toString();
    const url = `${window.location.pathname}${query ? `?${query}` : ''}`;
    window.history[replace ? 'replaceState' : 'pushState']({}, '', url);
    setLocation(next);
  }, []);

  useEffect(() => {
    if (!catalogue || !currentDocument) return;
    if (!location.documentId) {
      const inferredDocument = (location.paragraphId && documents.find((doc) => findParagraph(doc, location.paragraphId)))
        || (location.modelId && documents.find((doc) => links.some((link) => link.model_id === location.modelId && link.source_unit_ids?.some((id) => findParagraph(doc, id)))))
        || currentDocument;
      updateUrl({ documentId: inferredDocument.id, paragraphId: location.paragraphId, modelId: location.modelId }, true);
      return;
    }
    if (!documents.some((doc) => doc.id === location.documentId)) return;
    if (!location.paragraphId && !location.modelId) {
      const initialModel = models[0];
      const initialLink = initialModel && links.find((link) => link.model_id === initialModel.id && link.relation === 'models');
      const initialSource = initialLink?.source_unit_ids?.find((id) => findParagraph(currentDocument, id));
      if (initialSource) updateUrl({ documentId: currentDocument.id, paragraphId: initialSource, modelId: initialModel.id }, true);
    }
  }, [catalogue, currentDocument, documents, links, location, models, updateUrl]);

  const selectDocument = (documentId) => updateUrl({ documentId, paragraphId: null, modelId: null });
  const selectParagraph = (paragraphId) => {
    const paragraphLinks = linksForParagraph(links, paragraphId);
    const nextModel = models.find((model) => paragraphLinks.some((link) => link.model_id === model.id))?.id ?? null;
    updateUrl({ documentId: currentDocument.id, paragraphId, modelId: nextModel });
    setRevealRevision((revision) => revision + 1);
    setActiveMobilePane(nextModel ? 'rules' : 'source');
  };
  const selectModel = (modelId, preferredSourceId = null) => {
    const modelLinks = links.filter((link) => link.model_id === modelId);
    const preferredSourceStillLinked = preferredSourceId && modelLinks.some((link) => link.source_unit_ids?.includes(preferredSourceId));
    const selectedSourceStillLinked = location.paragraphId && modelLinks.some((link) => link.source_unit_ids?.includes(location.paragraphId));
    const sourceId = preferredSourceStillLinked ? preferredSourceId : selectedSourceStillLinked ? location.paragraphId : modelLinks.flatMap((link) => link.source_unit_ids ?? []).find((id) => findParagraph(currentDocument, id)) ?? null;
    updateUrl({ documentId: currentDocument.id, paragraphId: sourceId ?? location.paragraphId, modelId });
    setRevealRevision((revision) => revision + 1);
    setActiveMobilePane('rules');
  };
  const navigateToReference = (paragraphId) => {
    const topic = findTopicForParagraph(currentDocument, paragraphId);
    if (!topic) return;
    updateUrl({ documentId: currentDocument.id, paragraphId, modelId: location.modelId });
    setRevealRevision((revision) => revision + 1);
    setActiveMobilePane('source');
  };
  const resetLocation = () => updateUrl({ documentId: documents[0]?.id ?? null, paragraphId: null, modelId: null });

  if (!catalogue && !error) return <main className="state-screen"><div className="spinner" aria-hidden="true" /><p>Loading requirement catalogue…</p></main>;
  if (error) return <main className="state-screen"><div className="state-card"><h1>Catalogue unavailable</h1><p>{error}</p><button className="retry-button" onClick={() => window.location.reload()}>Reload catalogue</button></div></main>;
  if (!currentDocument) return <main className="state-screen"><div className="state-card"><h1>No requirement documents</h1><p>The catalogue contains no documents to display.</p></div></main>;

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="?" onClick={(event) => { event.preventDefault(); resetLocation(); }}>Crew Rules</a>
        <div className="topbar-divider" />
        <nav className="view-tabs" aria-label="Workspace">
          <button className={activeView === 'explorer' ? 'active' : ''} onClick={() => setActiveView('explorer')}>Source explorer</button>
          <button className={activeView === 'workshop' ? 'active' : ''} onClick={() => setActiveView('workshop')}>Rule workshop</button>
        </nav>
      </header>
      <div className="view-panel" hidden={activeView !== 'workshop'}><RuleWorkshop models={models} links={links} document={currentDocument} catalogueCommit="ac94f6e092555931781c31e23848b0af5aee295b" /></div>
      <div className="view-panel" hidden={activeView !== 'explorer'}>
      {invalidSelection && <div className="notice notice-error" role="alert">
        <span>The URL points to an item that is not in this catalogue.</span>
        <button className="text-button" onClick={resetLocation}>Reset to a valid selection</button>
      </div>}
      <nav className="mobile-tabs" aria-label="Workspace pane">
        <button className={activeMobilePane === 'source' ? 'active' : ''} onClick={() => setActiveMobilePane('source')}>Requirements</button>
        <button className={activeMobilePane === 'rules' ? 'active' : ''} onClick={() => setActiveMobilePane('rules')}>Rule model</button>
      </nav>
      <div className={`workspace ${activeMobilePane === 'rules' ? 'mobile-rules' : ''}`}>
        <DocumentPane
          documents={documents}
          document={currentDocument}
          links={links}
          models={models}
          selectedParagraphId={location.paragraphId}
          selectedModelId={location.modelId}
          onSelectDocument={selectDocument}
          onSelectParagraph={selectParagraph}
          onSelectModel={selectModel}
          paragraphRefs={paragraphRefs}
          revealRevision={revealRevision}
          shouldRevealSource={!isMobile || activeMobilePane === 'source'}
        />
        <ModelPane
          models={models}
          links={links}
          selectedModel={selectedModel}
          relatedModels={relatedModels}
          selectedParagraphId={location.paragraphId}
          selectedModelId={location.modelId}
          onSelectModel={selectModel}
          onNavigateReference={navigateToReference}
          document={currentDocument}
        />
      </div>
      </div>
    </main>
  );
}

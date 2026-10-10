export async function loadCatalogue() {
  const response = await fetch('./catalogue.json');
  if (!response.ok) throw new Error(`Catalogue could not be loaded (${response.status}).`);
  const data = await response.json();
  if (!Array.isArray(data.documents) || !Array.isArray(data.models) || !Array.isArray(data.links)) {
    throw new Error('The catalogue is missing documents, models, or links.');
  }
  return data;
}

export const unitsForTopic = (topic) => topic?.units ?? [];
export const paragraphsForUnit = (unit) => unit?.kind === 'paragraph'
  ? [unit]
  : (unit?.rows ?? []).flatMap((row) => row.flatMap((cell) => cell.paragraphs ?? []));
export const allParagraphs = (document) => (document?.topics ?? []).flatMap((topic) =>
  unitsForTopic(topic).flatMap(paragraphsForUnit));
export const findParagraph = (document, id) => allParagraphs(document).find((p) => p.id === id);
export const findTopicForParagraph = (document, id) => (document?.topics ?? []).find((topic) =>
  unitsForTopic(topic).some((unit) => paragraphsForUnit(unit).some((p) => p.id === id)));
export const linksForParagraph = (links, paragraphId) => links.filter((link) =>
  link.source_unit_ids?.includes(paragraphId));
export const linksForModel = (links, modelId) => links.filter((link) => link.model_id === modelId);
export const normalizeSearchText = (value) => String(value ?? '').replace(/\s+/gu, ' ').trim().toLowerCase();
export const searchableParagraphText = (paragraph) => `${paragraph?.text ?? ''} ${paragraph?.citation ?? ''} ${paragraph?.locator ?? ''}`;
export const relationLabel = (relation) => relation === 'context' ? 'Context' : 'Models';

export function locationForParagraph(document, paragraphId) {
  const topic = findTopicForParagraph(document, paragraphId);
  const topicIndex = document?.topics?.findIndex((item) => item.id === topic?.id) ?? -1;
  return { topic, topicIndex };
}

export function sourceReferencesForModel(links, modelId) {
  return linksForModel(links, modelId).flatMap((link) =>
    (link.source_unit_ids ?? []).map((paragraphId) => ({ link, paragraphId })));
}

export function formatValue(value) {
  if (value === null) return 'None';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map(formatValue).join(', ');
  if (value && typeof value === 'object') {
    const entries = Object.entries(value).filter(([, child]) => child !== undefined && child !== null);
    return entries.map(([key, child]) => `${humanizeKey(key)}: ${formatValue(child)}`).join(' · ');
  }
  return String(value ?? '');
}

export function humanizeKey(key) {
  return String(key).replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const keyFor = (id) => `airspec.rule-draft:${id}`;

export function saveDraftLocally(storage, draft) {
  storage.setItem(keyFor(draft.definitionId), JSON.stringify(draft));
}

export function loadDraftLocally(storage, definitionId) {
  try { return JSON.parse(storage.getItem(keyFor(definitionId)) || 'null'); } catch { return null; }
}

export function clearDraftLocally(storage, definitionId) {
  storage.removeItem(keyFor(definitionId));
}

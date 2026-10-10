const keyFor = (id) => `airspec.rule-draft:${id}`;
const revisionKeyFor = (id) => `airspec.rule-draft-revision:${id}`;

export function loadDraftRevisionLocally(storage, definitionId) {
  const revision = Number(storage.getItem(revisionKeyFor(definitionId)));
  return Number.isSafeInteger(revision) && revision > 0 ? revision : 0;
}

export function rememberDraftRevisionLocally(storage, definitionId, revision) {
  const highWater = Math.max(loadDraftRevisionLocally(storage, definitionId), Number.isSafeInteger(revision) ? revision : 0);
  if (highWater > 0) storage.setItem(revisionKeyFor(definitionId), String(highWater));
  return highWater;
}

export function saveDraftLocally(storage, draft) {
  storage.setItem(keyFor(draft.definitionId), JSON.stringify(draft));
  rememberDraftRevisionLocally(storage, draft.definitionId, draft.revision);
}

export function loadDraftLocally(storage, definitionId) {
  try { return JSON.parse(storage.getItem(keyFor(definitionId)) || 'null'); } catch { return null; }
}

export function clearDraftLocally(storage, definitionId) {
  storage.removeItem(keyFor(definitionId));
}

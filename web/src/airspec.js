/** Stable, engine-independent authoring contract for AirSpec rule drafts. */
export const DRAFT_FORMAT = 'airspec.rule-draft';
export const DEFINITION_FORMAT = 'airspec.rule-definition';
export const FORMAT_VERSION = '1.0.0';

const SUPPORTED_SCOPES = new Set([
  'activity', 'duty', 'pairing', 'employee_time_period', 'aircraft_time_period',
  'employee_rest_time', 'employee_ground_time', 'aircraft_ground_time', 'port_time_period',
]);

const issue = (path, code, message) => ({ path, code, message });

export function validateRuleDraft(draft) {
  const errors = [];
  const unsupported = [];
  if (!draft || typeof draft !== 'object' || Array.isArray(draft)) {
    errors.push(issue('$', 'DRAFT_NOT_OBJECT', 'Draft must be a JSON object.'));
    return { status: 'invalid', errors, unsupported };
  }
  if (draft.format !== DRAFT_FORMAT) errors.push(issue('format', 'FORMAT_MISMATCH', `format must be "${DRAFT_FORMAT}".`));
  if (draft.formatVersion !== FORMAT_VERSION) errors.push(issue('formatVersion', 'VERSION_UNSUPPORTED', `formatVersion must be "${FORMAT_VERSION}".`));
  if (typeof draft.definitionId !== 'string' || !draft.definitionId.trim()) errors.push(issue('definitionId', 'REQUIRED', 'A stable definitionId is required.'));
  if (!Number.isInteger(draft.revision) || draft.revision < 1) errors.push(issue('revision', 'REVISION_INVALID', 'revision must be a positive integer.'));
  if (!draft.basedOn || typeof draft.basedOn !== 'object') errors.push(issue('basedOn', 'PROVENANCE_REQUIRED', 'basedOn catalogue and source identity are required.'));
  else {
    for (const key of ['catalogueCommit', 'sourceDocumentId', 'sourceRevision', 'sourceHash']) {
      if (typeof draft.basedOn[key] !== 'string' || !draft.basedOn[key].trim()) errors.push(issue(`basedOn.${key}`, 'PROVENANCE_FIELD_REQUIRED', `${key} is required.`));
    }
  }
  if (!Array.isArray(draft.provenance) || draft.provenance.length === 0) errors.push(issue('provenance', 'SOURCE_LINK_REQUIRED', 'At least one source link is required.'));
  else draft.provenance.forEach((link, index) => {
    if (!link || typeof link !== 'object' || typeof link.sourceId !== 'string' || !link.sourceId) errors.push(issue(`provenance[${index}].sourceId`, 'SOURCE_ID_REQUIRED', 'Each source link needs a sourceId.'));
  });

  const rule = draft.rule;
  if (!rule || typeof rule !== 'object' || Array.isArray(rule)) {
    errors.push(issue('rule', 'RULE_NOT_OBJECT', 'rule must be an AnyRule JSON object.'));
  } else {
    if (rule.id !== draft.definitionId) errors.push(issue('rule.id', 'DEFINITION_ID_MISMATCH', 'rule.id must match the stable definitionId.'));
    if (typeof rule.id !== 'string' || !rule.id) errors.push(issue('rule.id', 'REQUIRED', 'Rule id is required.'));
    if (typeof rule.name !== 'string' || !rule.name.trim()) errors.push(issue('rule.name', 'REQUIRED', 'Rule name is required.'));
    if (!SUPPORTED_SCOPES.has(rule.scope)) errors.push(issue('rule.scope', 'SCOPE_INVALID', 'rule.scope must be one of the declared AnyRule scopes.'));
    for (const field of ['applicability', 'value']) {
      const table = rule[field];
      if (!table || typeof table !== 'object' || Array.isArray(table)) errors.push(issue(`rule.${field}`, 'DECISION_TABLE_INVALID', `${field} must be a decision table with default and items.`));
      else {
        if (!Array.isArray(table.items) || !Object.hasOwn(table, 'default')) errors.push(issue(`rule.${field}`, 'DECISION_TABLE_INVALID', `${field} must be a decision table with default and items.`));
        if (Array.isArray(table.items)) validateTable(table, `rule.${field}`, errors);
      }
    }
    for (const field of ['value_updates', 'requirement_updates', 'limit_updates']) {
      if (!Array.isArray(rule[field])) errors.push(issue(`rule.${field}`, 'ARRAY_REQUIRED', `${field} must be an array.`));
      else rule[field].forEach((update, index) => {
        if (!update || typeof update !== 'object' || typeof update.name !== 'string' || !update.table || typeof update.table !== 'object') errors.push(issue(`rule.${field}[${index}]`, 'UPDATE_INVALID', 'Each update requires a name and decision table.'));
        else validateTable(update.table, `rule.${field}[${index}].table`, errors);
      });
    }
    if (rule.requirement == null && rule.limit == null) errors.push(issue('rule.requirement', 'REQUIREMENT_OR_LIMIT_REQUIRED', 'At least one of requirement or limit is required.'));
    for (const field of ['requirement', 'limit']) {
      if (rule[field] != null) {
        if (typeof rule[field] !== 'object' || Array.isArray(rule[field])) errors.push(issue(`rule.${field}`, 'DECISION_TABLE_INVALID', `${field} must be null or a decision table with default and items.`));
        else {
          if (!Array.isArray(rule[field].items) || !Object.hasOwn(rule[field], 'default')) errors.push(issue(`rule.${field}`, 'DECISION_TABLE_INVALID', `${field} must be null or a decision table with default and items.`));
          if (Array.isArray(rule[field].items)) validateTable(rule[field], `rule.${field}`, errors);
        }
      }
    }
    if (['employee_time_period', 'aircraft_time_period', 'port_time_period'].includes(rule.scope)) {
      const period = rule.time_period;
      if (!period || !['day', 'duty_end', 'duty_start', 'week', 'month', 'year'].includes(period.anchor)
        || !['minute', 'hour', 'day', 'month', 'year'].includes(period.unit) || !Number.isInteger(period.duration)) {
        errors.push(issue('rule.time_period', 'TIME_PERIOD_INVALID', 'This scope requires a time_period with a valid anchor, unit, and integer duration.'));
      }
    }
  }
  if (!Array.isArray(draft.coverageGaps) || draft.coverageGaps.some((item) => typeof item !== 'string')) errors.push(issue('coverageGaps', 'COVERAGE_GAPS_INVALID', 'coverageGaps must be an array of strings.'));

  if (errors.length === 0) unsupported.push(issue('$', 'ENGINE_DISCONNECTED', 'No executable rule engine is connected; structural validity does not establish operational compliance.'));
  return { status: errors.length ? 'invalid' : 'valid_non_executable', errors, unsupported };
}

function validateTable(table, path, errors) {
  table.items.forEach((item, index) => {
    const itemPath = `${path}.items[${index}]`;
    if (!item || typeof item !== 'object' || !Array.isArray(item.condition) || !Object.hasOwn(item, 'value')) {
      errors.push(issue(itemPath, 'TABLE_ITEM_INVALID', 'Each table item requires a condition array and value.'));
      return;
    }
    item.condition.forEach((condition, conditionIndex) => {
      if (!condition || typeof condition !== 'object' || typeof condition.field !== 'string' || !condition.field
        || !condition.comparison || typeof condition.comparison !== 'object' || typeof condition.comparison.kind !== 'string') {
        errors.push(issue(`${itemPath}.condition[${conditionIndex}]`, 'CONDITION_INVALID', 'Each condition requires a field and comparison kind.'));
      }
    });
  });
}

function stableJson(value) {
  if (Array.isArray(value)) return value.map(stableJson);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableJson(value[key])]));
  return value;
}

export function diffRuleDraft(before, after) {
  const changes = [];
  const walk = (left, right, path) => {
    if (JSON.stringify(stableJson(left)) === JSON.stringify(stableJson(right))) return;
    if (left && right && typeof left === 'object' && typeof right === 'object' && !Array.isArray(left) && !Array.isArray(right)) {
      for (const key of [...new Set([...Object.keys(left), ...Object.keys(right)])].sort()) walk(left[key], right[key], path ? `${path}.${key}` : key);
    } else changes.push({ path: path || '$', before: left, after: right });
  };
  walk(before ?? {}, after ?? {}, '');
  return changes;
}

export function exportRuleDraft(draft) {
  const validation = validateRuleDraft(draft);
  if (validation.status === 'invalid') throw new Error('Invalid drafts cannot be exported.');
  return {
    format: DEFINITION_FORMAT,
    formatVersion: FORMAT_VERSION,
    definitionId: draft.definitionId,
    revision: draft.revision,
    basedOn: draft.basedOn,
    rule: draft.rule,
    provenance: draft.provenance,
    coverageGaps: draft.coverageGaps,
    validation: { status: validation.status, unsupported: validation.unsupported },
  };
}

export function makeRuleDraft(model, links, document, catalogueCommit = 'ac94f6e092555931781c31e23848b0af5aee295b') {
  const sourceLinks = links.filter((link) => link.model_id === model.id);
  const sourceParagraphs = new Map((document.topics ?? []).flatMap((topic) => (topic.units ?? []).flatMap((unit) => {
    const paragraphs = unit.kind === 'paragraph' ? [unit] : (unit.rows ?? []).flatMap((row) => row.flatMap((cell) => cell.paragraphs ?? []));
    return paragraphs.map((paragraph) => [paragraph.id, paragraph]);
  })));
  return {
    format: DRAFT_FORMAT,
    formatVersion: FORMAT_VERSION,
    definitionId: model.id,
    revision: 1,
    basedOn: {
      catalogueCommit,
      sourceDocumentId: document.id,
      sourceRevision: document.version,
      sourceHash: document.sha256,
    },
    rule: structuredClone(model.model),
    coverageGaps: [...(model.limitations ?? [])],
    provenance: sourceLinks.flatMap((link) => link.source_unit_ids.map((sourceId) => {
      const source = sourceParagraphs.get(sourceId);
      return {
        sourceId,
        citation: source?.citation ?? '',
        relation: link.relation,
        note: link.note ?? '',
        text: source?.text ?? '',
        locator: source?.locator ?? null,
      };
    })),
  };
}

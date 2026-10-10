/** Stable, engine-independent authoring contract for AirSpec rule drafts. */
export const DRAFT_FORMAT = 'airspec.rule-draft';
export const DEFINITION_FORMAT = 'airspec.rule-definition';
export const FORMAT_VERSION = '1.0.0';

const SUPPORTED_SCOPES = new Set([
  'activity', 'duty', 'pairing', 'employee_time_period', 'aircraft_time_period',
  'employee_rest_time', 'employee_ground_time', 'aircraft_ground_time', 'port_time_period',
]);
const COMPARISON_FIELDS = {
  equal_number_comparison: ['number'], ge_number_comparison: ['number'], le_number_comparison: ['number'],
  gt_number_comparison: ['number'], lt_number_comparison: ['number'], range_number_comparison: ['lower', 'upper'],
  equal_duration_comparison: ['duration'], ge_duration_comparison: ['duration'], le_duration_comparison: ['duration'],
  gt_duration_comparison: ['duration'], lt_duration_comparison: ['duration'], range_duration_comparison: ['lower', 'upper'],
  equal_text_comparison: ['text'], regex_text_comparison: ['expression'], range_datetime_comparison: ['lower', 'upper'],
  time_window_overlap_comparison: ['start', 'end'], equal_set_comparison: ['items'], within_set_comparison: ['items'],
  contain_set_comparison: ['items'], truth_comparison: [], false_comparison: [],
};
const VALUE_FIELDS = {
  applicable_value: ['applicable'], number_value: ['number'], duration_value: ['duration'],
  number_range_value: ['lower', 'upper'], duration_range_value: ['lower', 'upper'],
  field_value: ['field'], field_difference_value: ['start_field', 'end_field'],
  table_lookup_number_value: ['table_name', 'lookup_map'], projected_value: ['code'], none_value: [],
};
const COMPARISON_TYPES = {
  equal_number_comparison: { number: 'number', tolerance: 'number?' }, ge_number_comparison: { number: 'number' }, le_number_comparison: { number: 'number' },
  gt_number_comparison: { number: 'number' }, lt_number_comparison: { number: 'number' }, range_number_comparison: { lower: 'number', upper: 'number' },
  equal_duration_comparison: { duration: 'duration', tolerance: 'duration?' }, ge_duration_comparison: { duration: 'duration' }, le_duration_comparison: { duration: 'duration' },
  gt_duration_comparison: { duration: 'duration' }, lt_duration_comparison: { duration: 'duration' }, range_duration_comparison: { lower: 'duration', upper: 'duration' },
  equal_text_comparison: { text: 'string', case_sensitive: 'boolean?' }, regex_text_comparison: { expression: 'string' }, range_datetime_comparison: { lower: 'string', upper: 'string' },
  time_window_overlap_comparison: { start: 'string', end: 'string', overlap: 'duration?' }, equal_set_comparison: { items: 'array' }, within_set_comparison: { items: 'array' },
  contain_set_comparison: { items: 'array' }, truth_comparison: {}, false_comparison: {},
};
const VALUE_TYPES = {
  applicable_value: { applicable: 'boolean' }, number_value: { number: 'number' }, duration_value: { duration: 'duration' },
  number_range_value: { lower: 'number', upper: 'number' }, duration_range_value: { lower: 'duration', upper: 'duration' },
  field_value: { field: 'string', multiplier: 'number?', offset: 'number?', clamp_lower: 'number|null?', clamp_upper: 'number|null?' },
  field_difference_value: { start_field: 'string', end_field: 'string', multiplier: 'number?', offset: 'number?', clamp_lower: 'number|null?', clamp_upper: 'number|null?' },
  table_lookup_number_value: { table_name: 'string', lookup_map: 'lookup_array' }, projected_value: { code: 'string', element: 'projected_element?' },
  none_value: {},
};
const COMPARISON_KINDS = new Set(Object.keys(COMPARISON_FIELDS));
const UPDATE_METHODS = new Set(['set', 'increase', 'decrease', 'max', 'min', 'scale']);

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
    if (typeof rule.id !== 'string' || !isUuid(rule.id)) errors.push(issue('rule.id', 'RULE_ID_INVALID', 'Rule id must be a UUID accepted by AnyRule.'));
    if (typeof rule.name !== 'string' || !rule.name.trim()) errors.push(issue('rule.name', 'REQUIRED', 'Rule name is required.'));
    if (!SUPPORTED_SCOPES.has(rule.scope)) errors.push(issue('rule.scope', 'SCOPE_INVALID', 'rule.scope must be one of the declared AnyRule scopes.'));
    for (const field of ['applicability', 'value']) {
      const table = rule[field];
      if (!table || typeof table !== 'object' || Array.isArray(table)) errors.push(issue(`rule.${field}`, 'DECISION_TABLE_INVALID', `${field} must be a decision table with default and items.`));
      else {
        if ((Object.hasOwn(table, 'items') && !Array.isArray(table.items)) || !Object.hasOwn(table, 'default')) errors.push(issue(`rule.${field}`, 'DECISION_TABLE_INVALID', `${field} must be a decision table with a default and optional items array.`));
        if (!Object.hasOwn(table, 'items') || Array.isArray(table.items)) validateTable(table, `rule.${field}`, errors, field === 'applicability' ? 'applicable' : 'calculation');
      }
    }
    for (const field of ['value_updates', 'requirement_updates', 'limit_updates']) {
      if (!Object.hasOwn(rule, field)) continue; // AnyRule supplies an empty-list default.
      if (!Array.isArray(rule[field])) errors.push(issue(`rule.${field}`, 'ARRAY_REQUIRED', `${field} must be an array.`));
      else rule[field].forEach((update, index) => {
        const updatePath = `rule.${field}[${index}]`;
        if (!isObject(update)) {
          errors.push(issue(updatePath, 'UPDATE_INVALID', 'Each update requires a name and decision table.'));
          return;
        }
        if (typeof update.name !== 'string') errors.push(issue(`${updatePath}.name`, 'UPDATE_INVALID', 'Each update requires a string name.'));
        if (Object.hasOwn(update, 'method') && !UPDATE_METHODS.has(update.method)) errors.push(issue(`${updatePath}.method`, 'UPDATE_METHOD_INVALID', 'Update method must be one of the declared AnyRule methods.'));
        if (!isObject(update.table) || (Object.hasOwn(update.table, 'items') && !Array.isArray(update.table.items)) || !Object.hasOwn(update.table, 'default')) {
          errors.push(issue(`${updatePath}.table`, 'DECISION_TABLE_INVALID', 'Update table must be a decision table with a default and optional items array.'));
          return;
        }
        validateTable(update.table, `${updatePath}.table`, errors, 'nullable_calculation');
      });
    }
    if (rule.requirement == null && Array.isArray(rule.requirement_updates) && rule.requirement_updates.length > 0) {
      errors.push(issue('rule.requirement_updates', 'UPDATE_BASE_REQUIRED', 'A base requirement is required when requirement updates are present.'));
    }
    if (rule.limit == null && Array.isArray(rule.limit_updates) && rule.limit_updates.length > 0) {
      errors.push(issue('rule.limit_updates', 'UPDATE_BASE_REQUIRED', 'A base limit is required when limit updates are present.'));
    }
    if (rule.requirement == null && rule.limit == null) errors.push(issue('rule.requirement', 'REQUIREMENT_OR_LIMIT_REQUIRED', 'At least one of requirement or limit is required.'));
    for (const field of ['requirement', 'limit']) {
      if (rule[field] != null) {
        if (typeof rule[field] !== 'object' || Array.isArray(rule[field])) errors.push(issue(`rule.${field}`, 'DECISION_TABLE_INVALID', `${field} must be null or a decision table with default and items.`));
        else {
          if ((Object.hasOwn(rule[field], 'items') && !Array.isArray(rule[field].items)) || !Object.hasOwn(rule[field], 'default')) errors.push(issue(`rule.${field}`, 'DECISION_TABLE_INVALID', `${field} must be null or a decision table with a default and optional items array.`));
          if (!Object.hasOwn(rule[field], 'items') || Array.isArray(rule[field].items)) validateTable(rule[field], `rule.${field}`, errors, 'calculation');
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

function isObject(value) {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function validateTable(table, path, errors, valueType) {
  if (!isObject(table) || (Object.hasOwn(table, 'items') && !Array.isArray(table.items))) return;
  if (Object.hasOwn(table, 'default')) validateValue(table.default, `${path}.default`, errors, valueType);
  (table.items ?? []).forEach((item, index) => {
    const itemPath = `${path}.items[${index}]`;
    if (!item || typeof item !== 'object' || !Array.isArray(item.condition) || !Object.hasOwn(item, 'value')) {
      errors.push(issue(itemPath, 'TABLE_ITEM_INVALID', 'Each table item requires a condition array and value.'));
      if (isObject(item) && Object.hasOwn(item, 'value')) validateValue(item.value, `${itemPath}.value`, errors, valueType);
      return;
    }
    item.condition.forEach((condition, conditionIndex) => {
      if (!condition || typeof condition !== 'object' || typeof condition.field !== 'string' || !condition.field
        || !isObject(condition.comparison) || !COMPARISON_KINDS.has(condition.comparison.kind)) {
        errors.push(issue(`${itemPath}.condition[${conditionIndex}]`, 'CONDITION_INVALID', 'Each condition requires a field and comparison kind.'));
      } else {
        if (Object.hasOwn(condition, 'reverse_match') && typeof condition.reverse_match !== 'boolean') errors.push(issue(`${itemPath}.condition[${conditionIndex}].reverse_match`, 'CONDITION_FIELD_TYPE_INVALID', 'reverse_match must be a boolean.'));
        for (const field of COMPARISON_FIELDS[condition.comparison.kind]) {
          if (!Object.hasOwn(condition.comparison, field)) errors.push(issue(`${itemPath}.condition[${conditionIndex}].comparison.${field}`, 'COMPARISON_FIELD_REQUIRED', `${field} is required for ${condition.comparison.kind}.`));
        }
        for (const [field, expected] of Object.entries(COMPARISON_TYPES[condition.comparison.kind])) {
          validateFieldType(condition.comparison[field], expected, `${itemPath}.condition[${conditionIndex}].comparison.${field}`, errors);
        }
      }
    });
    validateValue(item.value, `${itemPath}.value`, errors, valueType);
  });
}

function validateValue(value, path, errors, valueType) {
  if (!isObject(value) || typeof value.kind !== 'string') {
    errors.push(issue(path, 'VALUE_INVALID', 'Value must be a tagged AnyRule value object.'));
    return;
  }
  const allowed = valueType === 'applicable'
    ? new Set(['applicable_value'])
    : valueType === 'nullable_calculation'
      ? new Set([...Object.keys(VALUE_FIELDS).filter((kind) => kind !== 'applicable_value')])
      : new Set(Object.keys(VALUE_FIELDS).filter((kind) => kind !== 'applicable_value' && kind !== 'none_value'));
  if (!allowed.has(value.kind)) {
    errors.push(issue(`${path}.kind`, 'VALUE_KIND_INVALID', `Value kind ${value.kind} is not valid for this decision table.`));
    return;
  }
  for (const field of VALUE_FIELDS[value.kind]) {
    if (!Object.hasOwn(value, field)) errors.push(issue(`${path}.${field}`, 'VALUE_FIELD_REQUIRED', `${field} is required for ${value.kind}.`));
  }
  if (Object.hasOwn(value, 'phrase') && typeof value.phrase !== 'string') errors.push(issue(`${path}.phrase`, 'VALUE_FIELD_TYPE_INVALID', 'phrase must be a string.'));
  for (const [field, expected] of Object.entries(VALUE_TYPES[value.kind])) validateFieldType(value[field], expected, `${path}.${field}`, errors);
}

function isUuid(value) {
  return typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

function validateFieldType(value, expected, path, errors) {
  const optional = expected.endsWith('?');
  const nullable = expected.includes('null');
  const kind = expected.replace(/[?]/g, '').replace('|null', '');
  if (optional && value === undefined) return;
  if (nullable && value === null) return;
  const numeric = (candidate) => typeof candidate === 'number' && Number.isFinite(candidate)
    || typeof candidate === 'string' && candidate.trim() !== '' && Number.isFinite(Number(candidate));
  const valid = kind === 'number' ? numeric(value)
    : kind === 'string' ? typeof value === 'string'
      : kind === 'boolean' ? typeof value === 'boolean'
        : kind === 'duration' ? typeof value === 'number' && Number.isFinite(value) || typeof value === 'string' && (numeric(value) || /^-?P(?=.*\d)(?:\d+(?:[.,]\d+)?Y)?(?:\d+(?:[.,]\d+)?M)?(?:\d+(?:[.,]\d+)?W)?(?:\d+(?:[.,]\d+)?D)?(?:T(?:\d+(?:[.,]\d+)?H)?(?:\d+(?:[.,]\d+)?M)?(?:\d+(?:[.,]\d+)?S)?)?$/i.test(value))
          : kind === 'array' ? Array.isArray(value)
            : kind === 'lookup_array' ? Array.isArray(value) && value.every((item) => isObject(item) && typeof item.name === 'string' && typeof item.field === 'string')
              : kind === 'projected_element' ? ['start', 'end', 'aggregate'].includes(value)
                : true;
  if (!valid) errors.push(issue(path, 'VALUE_FIELD_TYPE_INVALID', `${path.split('.').at(-1)} must have the AnyRule ${kind} type.`));
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

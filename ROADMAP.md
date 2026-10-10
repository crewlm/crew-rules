# Tiny roadmap

Goal: let nontechnical people edit, understand, and trace documentary rule
schemas without writing code. The schemas describe source-backed rule meaning
and relationships; they do not require Python-shaped facts or provide an
evaluator.

1. **Document semantics:** describe values, units, symbolic field paths,
   source meanings, represented clauses, and explicit schema gaps.
2. **Validate declarations:** check model structure, local references, source
   coverage, table transcription, units, circular references, overlapping
   conditions, and missing cases. These checks validate declarations, not
   regulatory outcomes.
3. **Illustrate schemas:** maintain source-backed examples that show what the
   existing model can express and where it cannot yet represent shared
   definitions, relationships, temporal collections, source bindings, and
   qualitative obligations.
4. **Enable authoring:** a simple web editor with business labels, Mermaid
   views, agent-assisted imports and edits, source traceability, and shared
   definition impact views.
5. **Package rule sets:** versioned collections of rules and shared
   definitions, linked by stable IDs.

Evaluation semantics and execution belong to a separate external engine. This
repository may publish illustrative schemas for such an engine, but its
documentary validation must not be presented as calculation or compliance
verification.

First milestone: one realistic source-backed rule set whose schema, represented
meaning, and known gaps a nontechnical user can inspect and trace.

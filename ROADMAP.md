# Tiny roadmap

Goal: let nontechnical people edit, understand and verify rules without writing code.

1. **Trace sources:** metadata on every rule and definition linking to source versions and sections, with interpretations recorded separately.
2. **Validate:** check references, fields, types, units, circular dependencies, overlapping conditions and missing cases.
3. **Complete evaluation:** define operation semantics independently of Python; finish calculations and rule evaluation. Verify with scenarios imported from existing implementations or generated with agent assistance.
4. **Enable authoring:** a simple web editor with business labels, Mermaid views, agent-assisted imports and edits, explanations, and shared-definition impact checks.
5. **Package rulesets:** versioned collections of rules and shared definitions, linked by stable IDs. This can proceed independently and does not block the other work.

First milestone: one realistic ruleset that a nontechnical user can edit, trace to its sources and verify against examples.

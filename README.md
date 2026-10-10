# Open Ontology for Airline Crew Rules

This repository explores a vendor-neutral, source-backed way to describe
airline crew rules as declarative constraints, including their meaning,
relationships, and provenance. The EASA FTL examples are documentary schemas:
they show what the current model can express and record known schema gaps.
Evaluation and compliance checks are delegated to a separate external engine.

For the motivation and intended scope, see the [concept note](concept-note.md).
For the current EASA assessment, see the [model gap analysis](references/ftl/easa-model-gap-analysis.md)
and [documentary schema catalog](examples/easa_ftl/README.md).

# Hierarchy

The hierarchy for setting up rules is:
- Entities: The base objects on which rules can apply
- Tags: Tags to apply to objects (e.g. Early Start Duty, Night Flight, etc)
- Tables: Named tables to support lookups (e.g. Max FDP); can be 1-/2-/N-dimensional; think of like a mapping which accepts some set of parameters and returns a result
- Projections: Use for aggregating volumes from entities onto a timeline (use for FDP, Duty Time, Flight Time, etc);
- Payroll items: "Rules" for payroll purposes (should it just be called 'Calculations'?)
- Rules: Declarative constraints that describe required conditions on entities

# To do

We should also have:
- References: Some list of items from EBA / Regulatory Docs / Email / Company SOP (maybe add property to the Value model which is called "references", so you can source where things come from)
- Rulesets: Collect rules together into logical groups (Pilots ruleset, or Management Pilots ruleset)
- Effectivity (of rules / payroll / rulesets)
- Versioned entities: So we can do things like get the version of the duty assigned to the person at roster publish, or the night before, or get the rostered block hours. Alternatively skip those items and instead expect them to come in as properties.

# Next

We should convert a couple of different rulesets to our format. See what breaks and update accordingly.

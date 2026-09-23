# rules
Rules management framework

# Hierarchy

The hierarchy for setting up rules is:
- Entities: The base objects on which rules can apply
- Definitions: Named definitions to apply to objects (e.g. Early Start Duty, Night Flight, etc)
- Tables: Named tables to support lookups (e.g. Max FDP); can be 1-/2-/N-dimensional; think of like a mapping
- Projections: Use for aggregating volumes from entities onto a timeline (use for FDP, Duty Time, Flight Time, etc);
- Payroll items: "Rules" for payroll purposes (should it just be called 'Calculations'?)
- Rules: Rules for validation of entities

We should also have:
- References: Some list of items from EBA / Regulatory Docs / Email / Company SOP
- Rulesets: Collect rules together into logical groups (Pilots ruleset, or Management Pilots ruleset)
- Effectivity (of rules / payroll / rulesets)
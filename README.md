# rules
Rules management framework

## Browser explorer

The React interface browses the pinned EASA FTL source and its five draft model examples. It includes 74 topics, 1,137 source paragraphs, and 9 tables. Passages without a linked model are shown as unlinked. The models are declarative drafts with visible limitations; they do not evaluate operational compliance.

From the repository root, regenerate the static catalogue and start the interface:

```bash
.venv/bin/python -m catalogue.export
cd web
npm ci
npm run dev
```

Vite serves the app at `http://localhost:5173`. Build a static production bundle with `npm run build`. The catalogue exporter reads the checked EASA XML and writes `web/public/catalogue.json`; edit `catalogue/seeds.py` to change the draft models and source links.

Run the focused catalogue checks from the repository root with `.venv/bin/python -m pytest -q tests/catalogue`.

# Hierarchy

The hierarchy for setting up rules is:
- Entities: The base objects on which rules can apply
- Tags: Tags to apply to objects (e.g. Early Start Duty, Night Flight, etc)
- Tables: Named tables to support lookups (e.g. Max FDP); can be 1-/2-/N-dimensional; think of like a mapping which accepts some set of parameters and returns a result
- Projections: Use for aggregating volumes from entities onto a timeline (use for FDP, Duty Time, Flight Time, etc);
- Payroll items: "Rules" for payroll purposes (should it just be called 'Calculations'?)
- Rules: Rules for validation of entities

# To do

We should also have:
- References: Some list of items from EBA / Regulatory Docs / Email / Company SOP (maybe add property to the Value model which is called "references", so you can source where things come from)
- Rulesets: Collect rules together into logical groups (Pilots ruleset, or Management Pilots ruleset)
- Effectivity (of rules / payroll / rulesets)
- Versioned entities: So we can do things like get the version of the duty assigned to the person at roster publish, or the night before, or get the rostered block hours. Alternatively skip those items and instead expect them to come in as properties.

# Next

We should convert a couple of different rulesets to our format. See what breaks and update accordingly.

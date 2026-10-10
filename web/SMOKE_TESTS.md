# Rule Workshop browser smoke checks

The smoke script runs the real Vite app against the checked-in
`web/public/catalogue.json` fixture (relative to the repository root). It uses a
fresh browser context per run, so local draft storage starts empty and the
persistence checks are repeatable. The Browser plugin is unavailable in this
environment; these checks use regular Playwright as the browser-testing fallback.

## Setup

Use Node.js 20.19 or later (or a newer supported LTS release). From `web/`,
install the locked project dependencies and Playwright's Chromium browser once:

```bash
npm ci
npx playwright install chromium
```

On Linux, Playwright may also use an installed system Chromium. Set
`CHROMIUM_PATH=/path/to/chromium` to select a particular binary. In a clean
Linux environment, install the OS libraries required by Playwright Chromium as
documented by Playwright.

## Run

```bash
npm run test:browser
```

The script starts its own Vite server on port 5178 and shuts it down when done.
Set `SMOKE_PORT` if that port is occupied. It checks malformed JSON separately
from structurally invalid data and valid non-executable drafts, confirms invalid
drafts cannot be saved or exported, verifies malformed update tables do not
crash the React root, and checks stale-storage rejection. It also checks
per-definition and workspace-tab edit retention, automatic revision persistence
before export, the revision high-water mark across source resets, stale writes
and resets from a second tab, stable identity across repeated exports, source
provenance, and page reload restoration. The AirSpec unit and catalogue Python
tests also share 67 numeric, duration, time, datetime, and hashable-set cases;
Python's `AnyRule` parser is the acceptance oracle for the browser validator.

The existing fast AirSpec unit checks remain available with `npm test`.

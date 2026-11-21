# OptiFreight AI: frontend

React, TypeScript and Vite. It runs on its own: with `VITE_API_MODE=mock` (the default) it uses a
built-in demonstration data layer, so no backend is needed.

## What is real and what is demonstration

| Part | Status |
|---|---|
| Screens, forms, validation, accessibility, theme, print sheet | Real interface code |
| Listings | Invented demonstration data (30 listings across the 4 corridors) |
| Rules (40 km, caps, budget, capacity, compatibility) | Simplified **demo evaluator** in `src/api/mock/demoEngine.ts`. It is NOT the production rules engine |
| Route lines and distances | Drawn through rough waypoints; not measured on roads |
| Ranking | A simple demo score. No trained model is connected (`model_score` is null) |
| Accounts and shipments | Stored in this browser only; hashing is for show, not real security |
| `src/api/httpApi.ts` | Proposed API paths for the future backend. Never run against a real server |

Every screen says so. The interface never presents demo output as verified.

## Run it

Needs Node.js 20 or newer.

```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Other commands:

```powershell
npm run typecheck    # TypeScript, no output
npm test             # unit and component tests (Vitest)
npm run build        # type check, then production build
npm run e2e          # Playwright end-to-end test (first run: npx playwright install)
```

Copy `.env.example` to `.env.local` to change the data mode or add a Google Maps Embed key.
With no key, the Shipment minimap uses the free Leaflet map.

## How the screens map to the rules

| Screen | What it shows |
|---|---|
| Workspace | Truck, route, the off-route checkbox (off by default), map, results grouped Eligible / Unverified / Rejected, trip limits |
| Match details | Every check as pass, fail or unknown with its claim type, explanation, timing, load chart, money, Accept |
| Compare | Two or three jobs side by side |
| Shipment | Simulated status steps, minimap, "Open in Google Maps", frozen figures, cancel |
| Trip sheet | Printable page with a QR code for the Google Maps link |
| Shipments | History and filter |
| Settings | What-if costs, theme, reset demo data |

## Design rules followed

- A verdict is always a symbol and a word, never colour alone.
- Unknown is shown as unknown ("—" or "Unverified"), never as zero or as a pass.
- Net earnings are labelled as estimates and never shown as profit.
- A route change marks earlier results out of date and disables Accept.
- No live GPS. Progress is moved step by step by the driver.

## Folder layout

```
src/api        types, client, HTTP adapter, mock/ (demonstration data and evaluator)
src/auth       sign-in state and route guard
src/state      workspace and theme state
src/hooks      data hooks (TanStack Query)
src/lib        formatting, validation, geo helpers, Google Maps links, reference tables
src/components feature components; map/ and ui/ inside
src/pages      one file per screen
src/styles     design tokens and styles
src/__tests__  Vitest tests
e2e            Playwright test
```

## Known limits

- Not yet installed, built, or run in a browser. Run `npm install`, `npm run typecheck` and
  `npm test`, then fix anything they report.
- Map tiles come from OpenStreetMap, which expects light use. Use a tile provider before any public launch.
- The PWA manifest uses an SVG icon. Add PNG icons (192 and 512 px) for installability on all devices.
- No ESLint or Prettier configuration yet.

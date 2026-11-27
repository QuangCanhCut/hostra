# HOSTRA AI — Heritage Luxury UI/UX Handoff
**v0.5 concept · 25/11/2026 · visual redesign, not product/architecture change**

## 1. Open this package
1. Extract the whole ZIP into your existing repository, e.g. `docs/ui/hostra-heritage-handoff/`. Keep relative folder structure.
2. Open `index.html` in a browser to review all screen references. If your browser blocks local assets, serve this folder locally with `python -m http.server 8080` then open `http://localhost:8080/index.html`.
3. Read `PROMPT_FOR_CODING_AGENT.md`; paste it into Antigravity or Codex while the existing HOSTRA repository is open. The agent must work on the existing frontend, not create a parallel demo application.
4. Read `specs/DESIGN_SYSTEM.md`, `specs/IMPLEMENTATION_CONTRACT.md`, and `specs/screen-inventory.json`.
5. Inspect the user-selected dashboard in `references/selected-dashboard.png` as the highest visual reference. `references/refined-dashboard.png` is a second concept. `references/redesign/` contains HTML render screenshots. `references/original/` has all 65 images extracted from the User Guide with an index linking captions to filenames.

## 2. What this package contains
- 62 HTML screen/state references using one shared `theme.css`; index gallery. These are visual references, not a production frontend. HTML links demonstrate navigation only, controls generally do not mutate state, tabs and forms are examples.
- 62 desktop dark screenshots (1440 × 1000 viewport, full-page height may exceed 1000), 15 mobile screenshots (390 × 844 viewport, full-page), 6 desktop light samples. Total 83 renders.
- 65 original screenshots from HOSTRA_AI_User_Guide(2).docx, mapped to the redesigned screen IDs. Some original captures are grouped into the same layout; states with separate designs are explicit in the index.
- Local WebP assets and a draft SVG logo. Cropped from the chosen generated mockup and from original demo screenshots, not original layered art, not licensed product proof or approved presenter assets. Some cropping artifacts are possible. Replace with clean licensed/generated source assets before public release. Never use a complete screenshot as UI or interactive controls.
- Design tokens (CSS + JSON), typography and component rules, implementation constraints, test checklist, coding prompt, source blueprint copy.

## 3. Source priority
Visual only: selected Heritage Luxury dashboard > new shared tokens + HTML references > old v0.4 visuals.
Behavior: existing tested repository behavior and latest approved product decisions > module design packages v0.2 (Dashboard v0.4) > Frontend Blueprint v1.0 DRAFT and User Guide (demo behavior) > concept imagery. Never infer functionality from pictures. Escalate conflicts before changing a business rule. See implementation contract.

## 4. Limitations
No access to your actual code repository or Figma source. Route names are suggested mapping keys, not verified paths. No real media/QR generation/authentication or API wired; live/OCOP/claim labels and metrics are illustrative. Some rare error/empty/permission states are described in the contract instead of rendered as separate screenshots. Source User Guide has screenshot-only observations and occasional mismatch in captions; the mapping is a best-effort visual index, not a proof of functional equivalence. Fonts use system fallbacks if Be Vietnam Pro/Inter are unavailable; source fonts are not included. The new light palette and emblem are proposals pending owner confirmation, and should not replace approved brand identity automatically.

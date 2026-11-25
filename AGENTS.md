# HOSTRA AI — Coding Agent Instructions

## 1. Project Context

HOSTRA AI is an autonomous AI-powered livestream commerce platform.

The system follows a modular monolith architecture with asynchronous AI and media workers.

The repository contains:
- `apps/api/` — Backend application.
- `apps/web/` — Frontend web application.
- `experiments/` — Technical research and PoCs.
- `docs/` — Architecture, product design, research, and implementation documentation.

**MVP scope:** HOSTRA private livestream room for validating autonomous AI livestream capabilities.

TikTok/Shopee integration and OBS-based broadcasting are future development goals, not current MVP functionality.

## 2. General Coding Principles

- Think before coding.
- Prefer simple solutions over unnecessary abstractions.
- Make minimal, targeted changes.
- Do not introduce unrequested features.
- Do not modify unrelated modules without justification.
- Reuse existing patterns and components when appropriate.
- Preserve backward compatibility unless a change is explicitly approved.
- Do not invent missing requirements or assume unvalidated technology works.

## 3. Architecture Rules

- Maintain a single speech/playout authority.
- Verify claims, rights, and SKU eligibility before publication.
- Never treat TTS completion as playback completion.
- Preserve module boundaries and versioned contracts.
- Do not mark PoC technologies as validated without evidence.
- Preserve backend authority over business-critical state.
- Handle concurrent commands and stale revisions explicitly.

## 4. Frontend Documentation

Frontend specifications are located at:

`docs/product/frontend/`

Before implementing frontend features, read:

1. `docs/product/frontend/README.md`
2. `docs/product/frontend/DECISIONS.md`
3. The relevant design package in `docs/product/frontend/modules/`
4. The design system and visual references in `docs/product/frontend/design/`
5. The implementation blueprint in `docs/product/frontend/blueprint/`

Also consult the relevant system architecture documents in `docs/` whenever backend contracts, security, state transitions, or media behavior are involved.

### Documentation Priority

Use the following precedence when documents disagree:

1. Explicit, approved product decisions.
2. Approved module specifications for the affected feature.
3. Approved HOSTRA visual design baseline v0.4.
4. System architecture and verified technical contracts.
5. Frontend Blueprint draft and implementation recommendations.

This precedence does not permit overriding security or safety requirements.

Documents marked `DRAFT`, `PROPOSED`, or `OPEN` are not automatically approved.

If two authoritative documents conflict, report the conflict instead of silently choosing an interpretation.

## 5. Frontend Development Rules

Frontend application directory:

`apps/web/`

Preferred frontend stack:
- React
- TypeScript
- Vite
- React Router
- TanStack Query
- Reusable UI components
- Mock Service Worker for development mocks
- Vitest and Playwright for testing

Before adding dependencies, inspect the existing project configuration.

### Development Approach

- Implement frontend features using mock APIs before real backend integration.
- Keep business logic separate from presentation components.
- Use typed interfaces for domain entities and API responses.
- Use shared design tokens and reusable components.
- Design for both Light Mode and Dark Mode.
- Support desktop Merchant Studio and mobile-first Viewer Live Room.
- Implement loading, empty, error, permission, and reconnect states.
- Do not hardcode mock business data directly into reusable components.
- Do not claim that mocked interactions are connected to real backend services.

## 6. Approved Visual Design

Visual baseline: **HOSTRA UI Redesign v0.4 — APPROVED**.

Brand and interface guidelines:

- Navy: `#0F172A`
- Primary Amber CTA: `#F5C430`
- Soft Yellow: `#FBE580`
- White: `#FFFFFF`
- Cool Gray: `#E2E8F0`
- Primary font: Be Vietnam Pro
- Fallback font: Inter
- Light and Dark Mode required
- Premium SaaS styling with restrained animations

Follow the approved Figma visual references and module specifications.

The imported SVG screens are visual references, not automatically responsive native components.

Do not redesign approved interfaces without explicit authorization.

Use Vietnamese for merchant-facing and viewer-facing UI labels unless otherwise specified.

## 7. Critical Product and Permission Rules

### Livestream

- Only Workspace Owner can START a livestream.
- Assigned Operators may control their authorized sessions.
- Multiple Operators may be assigned to the same session.
- Runtime commands require backend authorization and conflict handling.
- `ACCEPTED` does not mean `APPLIED`.
- `STARTING` does not mean `LIVE`.
- `PAUSE_AI` does not mean STOP livestream.
- Active SKU changes only after authoritative confirmation.
- Playback completion must rely on playback acknowledgment.

### Presenter and Rights

- Presenter assets require valid usage rights.
- Rights Subject consent is independent of merchant approval.
- Revoked or expired consent must invalidate affected usage.
- Newly generated presenter versions do not automatically replace approved versions.

### Products and Knowledge

- OCOP verification is separate from Owner approval.
- Missing evidence must not automatically be classified as fraud.
- Approved knowledge does not bypass publication verification.
- Changes to live facts, price, or story content require versioned revisions and applicable approval.
- A product is session-ready only when all required gates pass.

### Viewer

- Viewer joins through invitation link and nickname.
- Viewer must not receive merchant control permissions.
- Viewer media access is subscribe-only.
- Invitation expiry, usage limits, and revocation must be enforced by the backend.
- A successfully submitted comment does not guarantee an AI response.

## 8. Git and Repository Safety

- Inspect the current Git branch and working tree before editing.
- Never overwrite unrelated work-in-progress changes.
- Keep frontend development changes scoped to the intended feature.
- Do not modify research PoCs or backend modules unless explicitly requested.
- Do not commit credentials, private keys, environment secrets, or sensitive datasets.
- Do not automatically merge or push changes without authorization.
- Never delete project documentation without approval.

## 9. Implementation Workflow

For each development task:

1. Read the relevant documentation.
2. Identify affected screens, components, modules, and contracts.
3. Summarize the implementation plan.
4. Implement the smallest correct solution.
5. Run relevant tests and quality checks.
6. Check responsive behavior and Light/Dark Mode.
7. Verify role-based permissions and important UI states.
8. Report changed files, test results, assumptions, and unresolved risks.

## 10. Definition of Done

A frontend feature is complete only when:

- It matches the approved product requirements.
- It follows the approved HOSTRA visual design.
- It works with the configured mock data/API.
- Required loading, error, and permission states are handled.
- Relevant unit/component tests pass.
- Critical user interactions are verified.
- No unrelated functionality is broken.
- Remaining backend dependencies are clearly documented.

Do not claim production readiness based solely on a working mock frontend.

## 11. Frontend Agent Skills

For tasks involving `apps/web/`, use relevant skills
from `.agents/skills/` when available:

- vercel-react-best-practices:
  React performance, architecture and component patterns.

- web-design-guidelines:
  Accessibility, responsive design and UI quality review.

- frontend-design:
  Implement approved Figma designs faithfully.
  Do not redesign HOSTRA UI v0.4 without approval.

- webapp-testing:
  Browser verification and end-to-end UI testing.

Project requirements in `docs/product/frontend/` and
approved decisions take precedence over generic skill suggestions.

Do not run unreviewed third-party scripts.
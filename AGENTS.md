# HOSTRA AI — Coding Agent Instructions

## Project Context

HOSTRA AI is an autonomous livestream commerce platform.

The architecture follows a modular monolith approach
with asynchronous AI/media workers.

## Coding Principles

- Think before coding.
- Prefer simple solutions over unnecessary abstractions.
- Make minimal, targeted changes.
- Do not introduce unrequested features.
- Do not modify unrelated modules without justification.

## Architecture Rules

- Maintain a single speech/playout authority.
- Verify claims, rights, and SKU eligibility before publication.
- Never treat TTS completion as playback completion.
- Preserve module boundaries and versioned contracts.
- Do not mark PoC technologies as validated without evidence.

## Workflow

1. Read relevant architecture documentation.
2. Identify affected modules and contracts.
3. Implement the smallest correct solution.
4. Run relevant tests and quality checks.
5. Report changes, tests, and unresolved risks.
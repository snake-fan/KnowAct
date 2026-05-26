# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

This is a single-context repo:

- `CONTEXT.md` at the repo root defines the project glossary and domain language.
- `docs/adr/` contains architectural decisions for the repo.
- `CONTEXT-MAP.md` is not used.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root.
- **`docs/adr/`** ADRs that touch the area you're about to work in.

If any of these files don't exist, proceed silently. Don't flag their absence and don't suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

## Use the glossary's vocabulary

When your output names a domain concept in an issue title, refactor proposal, hypothesis, test name, or implementation note, use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use, or there's a real gap to note for `/grill-with-docs`.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because..._

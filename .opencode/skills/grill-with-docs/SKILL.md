---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, which also creates docs (ADRs and glossary) as we go. Use when the user wants to stress-test a plan before building, or says 'grill' or 'grill with docs'.
---

# Grill With Docs

Interview the user relentlessly about every aspect of their plan or design until every branch of the decision tree is resolved. While doing so, capture resolved terminology and architectural decisions as permanent documentation.

## Interview protocol

Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask questions one at a time, waiting for feedback on each before continuing. Asking multiple questions at once is bewildering.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Domain modeling (during the interview)

As the interview progresses, apply domain-modeling discipline:

### Challenge against the glossary

When the user uses a term that conflicts with existing language in `CONTEXT.md`, call it out immediately. "Your glossary defines X as Y, but you seem to mean Z — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it.

## Documentation output

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch — capture as they happen. Use the format in [CONTEXT-FORMAT.md](../domain-modeling/CONTEXT-FORMAT.md).

`CONTEXT.md` should be devoid of implementation details. It is a glossary, not a spec or scratch pad.

Create `CONTEXT.md` at the repo root lazily — only when the first term is resolved.

### Offer ADRs sparingly

Only create an ADR when all three are true:
1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](../domain-modeling/ADR-FORMAT.md).

ADRs live in `docs/adr/` with sequential numbering: `0001-slug.md`.

## File structure

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-some-decision.md
│       └── 0002-another-decision.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. Read it to find which context is relevant.

## Multi-context repos

If `CONTEXT-MAP.md` exists, read it to find contexts. Infer which context the current topic relates to. If unclear, ask.

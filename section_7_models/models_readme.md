# Models Registry — Human Door

The machine-readable registry lives in `models_registry.yaml`.

That file is the source of truth. The mind reads it. Every organ
manifest cites it. Every routing decision is grounded in it.

This file is for humans: a short explanation of what is in the
registry and why.

---

## What the Registry Declares

1. **LLMs** — every LLM Central Mind knows about, as its own
   top-level entry. Not grouped by family. Each LLM is described
   with:
   - Identity (origin, lineage, kind, version, size, context)
   - Problem-solving profile (reasoning style, quality scores)
   - Language coverage
   - Context behavior (effective window, forgetting pattern)
   - Failure modes
   - Strengths and weaknesses
   - Best tasks and avoid tasks
   - Output guard
   - Hardware footprint
   - Recommended role

2. **Domain assignments** — for each domain + capability, which
   LLMs may serve it, in priority order.

3. **Output guards** — how to clean LLM output before it enters
   the system (e.g. strip reasoning from a thinking model).

4. **Routing rules** — how the mind tries LLMs, what to do on
   failure, when to prefer memory over LLMs, when to reorder
   the roster based on evidence.

5. **Source schema** — the shape of the `source` field that
   every memory entry carries.

---

## Why This Exists

Without a registry:

- Each organ manifest invents its own model list.
- No organ knows what other organs use.
- An LLM that leaks reasoning gets used for translation.
- No record of which LLM produced which memory.
- Adding an LLM requires updating every manifest by hand.

With the registry:

- Every manifest **cites** the registry.
- Every routing decision is **grounded** in declared capabilities.
- Output guards are **attached to LLMs**, not scattered.
- Every memory entry carries **source** with the LLM name.
- Adding an LLM is: add to registry → update manifest → restart.

---

## Who Reads What

| Reader | Reads | Purpose |
|--------|-------|---------|
| The mind (`model_router.py`) | `models_registry.yaml` | Routing decisions |
| The trainer | `models_readme.md` | Understand the strategy |
| Organ manifests | cite the registry | Declare rosters |
| Memory entries | schema in registry | Store source tag |

---

## How to Add an LLM

1. Pull it via Ollama.
2. Add it as a new top-level entry in `models_registry.yaml`.
3. Set `installed: true` and fill in `ollama_tag`.
4. Fill in the problem-solving profile, language coverage,
   context behavior, failure modes, best tasks, avoid tasks.
5. Add it to a `domain_assignments` priority list if it should
   be considered for a domain.
6. Restart the backend.

The registry is the source of truth. Manifests cite it.

---

## How to Change a Domain's Models

1. Edit the `domain_assignments` block in the registry.
2. Update the organ manifest roster to match.
3. Restart.

Never edit a manifest without updating the registry. Never edit
the registry without updating the manifests. They must agree.

---

## Maintenance

- The registry is maintained by the trainer.
- The mind may **propose** registry changes but never applies them
  without approval.
- The registry is versioned via `schema_version`.
- When the schema changes, the version increments.

---

*Last updated: 2026-10-11*
*Maintained by: trainer*
*Consumed by: mind.model_router, organ manifests*

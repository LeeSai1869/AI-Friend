# AI Friend V1 — Living Development Objectives

This is the canonical living development agenda for AI Friend V1.

It is not a historical design document.

Update this file whenever:
- a new objective is defined;
- priority changes;
- a defect is discovered;
- an architectural decision affects future work;
- an objective is completed;
- the immediate next milestone changes.

The historical/technical checkpoint remains:
`.central_mind/development/central_mind_v1_followup.md`

---

## Immediate execution order

### 1. Desktop application launcher — OPERATIONAL / FOLLOW-UP DEFECT

Goal:
AI Friend must launch as a normal macOS application without requiring
the Trainer to type Terminal commands.

Required:
- macOS `.app` bundle;
- product name `AI Friend`;
- application icon;
- convenient Desktop access;
- preserve existing authentication/security architecture.

Completion condition:
Trainer can open AI Friend from the Desktop like a normal application.

Launcher implementation result:
- release `AI Friend.app` bundle generated;
- Desktop `AI Friend.app` launcher created;
- Desktop launcher resolves to the release application bundle;
- bundle verification reported PASS at directory level;
- follow-up defect: expected `Contents/Info.plist` was not found by
  PlistBuddy and must be investigated later;
- this follow-up does NOT block Coding V1 bootstrap.

---

### 2. Coding V1 — IN PROGRESS / HIGHEST DEVELOPMENT PRIORITY

Goal:
Make AI Friend capable of performing useful coding work on its own
project through the governed Central Mind lifecycle.

Target lifecycle:

Trainer instruction
→ Central Mind
→ Reasoner
→ Coding domain
→ inspect actual project
→ plan when necessary
→ generate implementation
→ guarded filesystem modification
→ constrained test execution
→ verification
→ Self-Appraisal
→ Learner
→ report result

Required properties:
- Coding LLMs/resources remain subordinate to Central Mind.
- No model becomes authority.
- Actual project state must be inspected before modification.
- Filesystem mutations go through governed tools.
- Process execution remains Guard-controlled.
- Verification occurs after implementation.
- Self-Appraisal receives the result.
- Reusable verified experience can reach Learner/Derived Memory.
- Fail closed when authority or verification is unavailable.

First major proof:
Give AI Friend a real defect or small feature in AI Friend V1 and have
AI Friend inspect, implement, test, verify, appraise, and report it.

---

### 3. Chat Memory — IMMEDIATE FOLLOW-UP

Goal:
Chat/project continuity must survive closing and reopening AI Friend.

Current known foundation:
- Chat State exists.
- Chat IDs persist.
- conversations can be saved/reloaded.
- recent model context and summaries exist.

Still required:
- verify UI restoration end-to-end;
- verify project/conversation continuity after application restart;
- distinguish Chat State from permanent Section 3 Memory;
- retain useful finalized context/decisions/unresolved work;
- avoid treating the entire transcript as permanent knowledge.

---

### 4. Memory Intake — IMMEDIATE FOLLOW-UP

Goal:
Trainer must be able to deliberately provide permanent knowledge to
AI Friend from multiple supported resource types.

Important:
Memory Intake is NOT Chat.

Target:
Trainer
→ Memory Intake
→ resource ingestion/extraction
→ provenance
→ review/validation
→ Raw Memory under Trainer authority

Required eventually:
- text;
- files/documents;
- images where extraction is available;
- audio where transcription is available;
- multiple resources in one intake workflow;
- clear provenance for each supplied source.

Raw Memory remains Trainer-controlled.

---

## Core cognitive lifecycle

Target permanent cycle:

Input
→ Understand
→ Recall
→ Reason
→ identify uncertainty
→ Plan
→ select capabilities/resources
→ Act
→ Verify
→ Self-Appraise
→ Learn
→ Communicate

The architecture should close the lifecycle, not close future intelligence.

---

## Capability Expansion

Current implementation can create capability-gap proposals.

Target behavior:

demonstrated missing capability
→ Self-Appraisal identifies gap
→ Capability Expansion proposes requirement
→ Coding designs implementation
→ Coding writes implementation
→ tests
→ verification
→ trusted registration
→ capability becomes discoverable
→ AI Friend can subsequently use it

Capability Expansion must never grant its own authority.

This becomes a major live test after Coding V1 works.

---

## Model/resource intelligence — preserve, improve later

Do not block Coding V1 on perfect model selection.

Permanent architectural direction:

- No LLM identity should be hardcoded as Central Mind intelligence.
- `models_registry.yaml` describes model/resource facts.
- Registry contains technical characteristics, strengths, weaknesses,
  failure modes, capabilities, hardware requirements and bootstrap guidance.
- Central Mind should eventually choose resources according to task needs.
- Learned contextual performance should improve future selection.
- One user response does not imply one LLM.
- Different cognitive subtasks may use different resources.
- Central Mind may consult multiple sources when uncertainty/evidence requires it.
- Do not expose artificial Chat/Analyze/Research modes merely to force
  resource selection.
- External models remain subordinate cognitive resources.
- Central Mind owns final coordination and authority.

Known current issue:
`chat/reason` bootstrap priority and domain eligibility conflict can cause
an unintended resource to become the first candidate.

Known current issue:
semantic routing models may return Markdown-fenced JSON.

These are real defects but are NOT allowed to block Coding V1 bootstrap.

---

## Memory architecture

Section 3 is the sole permanent knowledge/experience system.

Permanent classes:

1. Raw Memory
   - supplied only through authenticated Trainer Memory Intake.

2. Tested Memory
   - information that passed appropriate verification.

3. Derived Memory
   - reusable system-learned concepts, strategies, patterns and experience.

All permanent-memory access goes through the Memory Service.

No component may directly mutate permanent memory storage.

Deletion remains authorization-controlled.

Separate from permanent memory:

- Chat State Memory;
- Coding Workspace/Project Memory;
- bounded temporary cognitive evidence.

---

## Security invariants

- Human/Constitution remain top authority.
- Central Mind coordinates; it does not bypass Guard.
- Guard authorizes protected action before execution.
- Verifier checks correctness after action.
- Protected Central Mind/Constitution/security surfaces remain guarded.
- Permanent Memory cannot be directly mutated by domains/models/tools.
- Terminal/process execution remains high-risk and constrained.
- Model output cannot grant permissions.
- Component manifests describe capabilities; they do not grant authority.
- Fail closed on missing trusted execution context.

---

## Current known defects / incomplete behavior

- Semantic routing output contract needs stronger structured-output handling.
- Model bootstrap ranking can conflict with eligibility metadata.
- Learned source scoring is not yet demonstrated end-to-end.
- Multi-resource cognition is not yet demonstrated.
- Self-Appraisal exists but has not yet been demonstrated through the
  complete useful live lifecycle.
- Capability Expansion proposes gaps but has not yet demonstrated
  autonomous implementation of a new capability.
- Chat tool-status `Thinking (...)` lifecycle/race remains unresolved.
- Restored historical chat turns do not necessarily retain full resource
  provenance.
- Memory Intake multi-resource UX is incomplete.
- Coding V1 has not yet been proven end-to-end.
- Normal macOS application launching is being established now.

---

## Completed / established foundations

- Central Mind V1 bounded cognitive architecture.
- Guard / authenticated principal architecture.
- Tool Broker with trusted component identity.
- Effect classification before protected execution.
- Verifier boundary.
- Self-Appraiser V1.
- Learner V1.
- Capability Expansion V1 proposal mechanism.
- Section 3 Memory Service boundary.
- Model/provider-neutral execution interface.
- Model registry.
- Ollama/local provider support.
- Additional provider plugs.
- Semantic capability descriptions in Inventory.
- Reasoner semantic routing structure.
- Chat State persistence foundation.
- Secure cross-window authenticated session handling.
- Tauri Chat UI foundation.
- Coding domain manifest exposes inspect/plan/write/test/debug/verify.
- Coding engine already references guarded filesystem and terminal tools.

---

## Development operating rule

Do not spend long periods perfecting isolated subsystems before the
organism can perform useful work.

Current strategy:

1. Make application directly launchable.
2. Make Coding V1 operational.
3. Give AI Friend real development work.
4. Use observed failures to improve reasoning, memory, appraisal,
   learning and capability expansion.
5. Let AI Friend increasingly implement ordinary improvements itself.

The Trainer should progressively stop acting as a manual code-transfer
layer.

---

## Immediate next milestone

**Coding V1 end-to-end bootstrap.**

As soon as the desktop launcher is operational, inspect the existing
coding engine and connect the minimum missing links required for one
real governed self-development task.

Do not divert into model-ranking optimization before this milestone
unless model execution completely prevents Coding V1 from functioning.

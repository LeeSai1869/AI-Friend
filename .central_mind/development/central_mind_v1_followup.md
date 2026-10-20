# AI Friend V1 — Central Mind Development Follow-Up

Status: ACTIVE DEVELOPMENT CHECKPOINT
Purpose: Temporary development continuity file for building and stabilizing Central Mind V1.
Authority: This file records development state. It is NOT Constitution, NOT permanent AI memory, and NOT an authority source.
Canonical intended architecture remains: section_2_constitution/design.md

---

# 1. CURRENT DEVELOPMENT OBJECTIVE

Complete Central Mind V1 as one connected cognitive system, then move immediately to real authenticated server/chat testing.

The four cognitive systems are to be implemented and connected together in one integration milestone:

1. Reasoner V1
2. Learner V1
3. Self-Appraiser V1
4. Capability Expansion V1

After integration, test them through the real server/chat path and then improve behavior from actual evidence rather than continuing prolonged theoretical development.

---

# 2. ARCHITECTURE LOCK

The major Central Mind architecture is now considered structurally locked.

Human Authority / Constitution
        |
    Central Mind
        |
        +-- Reasoner
        +-- Learner
        +-- Self-Appraiser
        +-- Capability Expansion
        +-- Questioning
        +-- Memory Service
        +-- Domains / Capabilities
        +-- Models / LLM Providers
        +-- Tools
        |
      Verifier
        |
  Evidence / Outcome
        |
  Self-Appraiser
        |
      Learner
        |
   Memory Service

Do not rearrange these layers merely to make implementation easier.

A structural change is permitted only when genuinely necessary or essential.

Every structural change must record:

- what changed
- why it was necessary
- alternatives considered
- components affected
- authority/security impact
- memory impact
- compatibility impact
- tests required
- migration/cleanup required

Architecture principle:

CLOSE THE ARCHITECTURE, NOT THE INTELLIGENCE.

Reasoner/Learner/Appraiser implementations may improve through V2/V3/V4 without redesigning the stable Central Mind sockets.

---

# 3. CENTRAL MIND INTELLIGENCE OWNERSHIP

Central Mind owns intelligence.

External LLMs are subordinate cognitive providers.

LLMs are NOT:

- Central Mind
- the Reasoner
- authority over Central Mind
- final truth
- permanent owners of particular domains

LLMs may:

- propose
- reason
- explain
- critique
- generate candidates
- provide alternative approaches
- assist communication

Central Mind evaluates their output using:

- memory
- evidence
- verification
- experience
- Constitution
- Guard
- domain knowledge
- provider reliability

Long-term objective:

AI Friend becomes progressively less dependent on external LLMs as its own verified knowledge, concepts, strategies and experience increase.

---

# 4. SHARED MODEL PROVIDER POLICY

The current fixed-duty model arrangement is transitional and must be removed from cognitive selection.

All compatible LLM providers should be available to Central Mind and domains through the provider/model layer.

Selection should eventually use:

1. relevant existing Memory
2. prior provider/domain/task experience
3. capability requirements
4. model availability
5. cost/resource constraints
6. verification requirements

Early system behavior may consult multiple suitable models because provider reliability history is sparse.

Over time, learned provider performance should improve selection.

Provider reliability must be contextual rather than one universal score.

Example dimensions:

provider
domain
task family
success/failure history
verification history
reliability
cost
latency

No model gains authority from a high score.

---

# 5. PERMANENT MEMORY — SECTION 3

Section 3 remains the canonical permanent reusable memory system.

There must NOT be a second competing permanent memory inside Central Mind.

Permanent memory has three conceptual classes/layers:

## Raw

Raw permanent memory is supplied ONLY through Trainer-authorized Memory Intake.

System experience must not silently create Raw memory.

## Tested / Verified

Knowledge that has passed appropriate verification/testing.

## Derived / Learned

Reusable knowledge derived from memories and/or verified experience.

Examples:

- concepts
- relationships
- patterns
- trends
- strategies
- abstractions
- reusable failure knowledge
- provider/task reliability
- learned decision knowledge

Derived knowledge must retain provenance sufficient to understand where it came from.

---

# 6. MEMORY SELECTION PRINCIPLE

Permanent Memory stores reusable intelligence, not everything encountered.

A candidate is valuable when retaining it prevents meaningful future effort, preserves unique experience, or provides reusable intelligence.

Do NOT permanently store information merely because it was observed.

Examples of generally low-value permanent memory:

- easily retrievable trivial public facts
- disposable intermediate model text
- duplicated prompts
- full temporary context
- routine transient execution data

Examples of valuable permanent memory:

- AI Friend architecture decisions
- project-specific reusable knowledge
- verified coding strategies
- recurring failure conditions
- learned provider reliability
- image concepts
- language concepts
- trading patterns after appropriate validation
- difficult-to-reconstruct knowledge
- reusable abstractions

Storage constraint:

Physical storage is limited to approximately 850 GB.

Preserve intelligence value, not every byte used to produce it.

---

# 7. MEMORY ID PRINCIPLE

Permanent memories have canonical unique IDs.

Desired conceptual identity:

<DOMAIN><12-digit sequence>

Example sequence:

000000000001
000000000002
000000000003

Do NOT create a second ID authority if Section 3 already implements canonical ID generation.

Existing Section 3 implementation must be reused/adapted.

Other components should reference permanent knowledge by Memory ID instead of copying the knowledge into multiple stores.

Examples:

Chat Memory -> Memory IDs
Project Memory -> Memory IDs
Reasoner -> Memory IDs
Learner -> Memory IDs
Domains -> Memory IDs

Supersession/version relationships remain governed centrally by Memory Service.

---

# 8. MEMORY ACCESS RULE

Every Central Mind component/domain accesses permanent memory through the Memory Service interface.

No component may directly read or mutate Section 3 storage.

Central Mind may read authorized memory through Memory Service.

Domains may read authorized relevant memory through Memory Service.

Agents may propose memory changes.

Memory Service owns persistence and lifecycle enforcement.

Deletion/retirement/supersession follows established authority rules.

---

# 9. TEMPORARY EVIDENCE VS PERMANENT MEMORY

Operational evidence is NOT a second permanent memory.

Intended flow:

Action / Reasoning / Provider / Domain
        |
     Result
        |
    Verifier
        |
Temporary Evidence / Outcome
        |
 Self-Appraiser
        |
   +----+-------------------+
   |                        |
No reusable value      Reusable insight
   |                        |
discard/expire             Learner
                            |
                     Memory Proposal
                            |
                      Memory Service
                            |
                  Derived/Tested Memory
                    as appropriate

Evidence retained permanently should be only what is necessary for provenance, testing, retesting, reliability or learned knowledge.

The recently implemented Scorer/Evidence V1 is NOT yet blessed as the permanent evidence-storage architecture.

It was implemented but has NOT yet been validated by tests.

Its current permanent JSONL assumption must be reconciled with this bounded-memory architecture during the four-system integration.

---

# 10. OUTCOME DIMENSIONS

Do not collapse all result states into one field.

At minimum distinguish conceptually:

Objective outcome:
- success
- failure
- partial
- unknown

Verification state:
- passed
- failed
- insufficient
- not_applicable
- not_performed

Central Mind disposition:
- accept
- reject
- retry
- investigate
- clarify
- escalate/request_decision

Failure/blocking classification may include:
- timeout
- wrong_output
- missing_dependency
- import_error
- syntax_error
- runtime_error
- logic_error
- context_mismatch
- resource_limit
- missing_capability
- authorization_denied
- verification_failed
- insufficient_evidence
- unknown

Memory reliability/status is separate again.

Do not equate verification success with objective success.

---

# 11. CHAT MEMORY — FUTURE CHAT ENGINE

Chat memory is contextual conversation state, not Section 3 permanent knowledge.

Initial policy:

- default maximum persistent chats per user: 5
- Administrator may configure this limit
- user may delete own chat memory

Chat memory should maintain useful state such as:

- objective
- current topic
- finalized decisions
- agreed constraints
- important corrections
- unresolved questions
- pending work
- relevant recent context
- referenced Memory IDs
- active project/workspace references

Do not require permanent storage of every full transcript merely to maintain continuity.

Before answering inside an existing chat:

1. identify active chat
2. load chat state
3. resolve relevant Memory IDs
4. understand current objective/context
5. reason
6. answer/update state

---

# 12. CODING PROJECT / WORKSPACE MEMORY — FUTURE CODING ENGINE

Coding should eventually maintain contextual project/workspace state.

Workspace Memory answers:

"What environment/workspace am I operating in?"

Project Memory answers:

"What do I know about this particular project?"

Possible state includes:

- workspace identity
- project identity/root
- architecture summary
- current objective
- finalized project decisions
- known components
- current implementation stage
- relevant tests
- pending work
- referenced permanent Memory IDs

Important:

Project/Workspace Memory is orientation, NOT proof of current filesystem state.

Before modifying code, Coding must inspect/verify relevant current files.

---

# 13. COGNITIVE OPERATING CYCLE

Target Central Mind cycle:

Input
  -> Understand
  -> Recall
  -> Reason
  -> Identify uncertainty
  -> Plan
  -> Select capabilities/providers
  -> Execute
  -> Verify
  -> Appraise
  -> Learn
  -> Communicate

Stable conceptual sockets:

Perceive
  -> Recall
  -> Reason
  -> Plan
  -> Act
  -> Verify
  -> Appraise
  -> Learn

Conditional branches:

Need information -> Question

Demonstrated missing capability -> Capability Expansion proposal

No uncontrolled reasoning/action loops.

Iteration must have:

- budget
- progress condition
- stop condition
- retry reason
- escalation/clarification path

---

# 14. REASONER V1 TARGET

Reasoner belongs to Central Mind.

It should determine:

- what the user/objective requires
- what is already known
- what information is missing
- whether clarification is required
- what strategy should be attempted
- which capabilities/domains/providers are relevant
- what evidence would establish success
- when to stop/retry/escalate

External reasoner LLMs are providers to Reasoner, not Reasoner itself.

Reasoner V1 may initially rely heavily on providers.

Its stable contract must permit later internal reasoning improvements without changing Central Mind architecture.

---

# 15. SELF-APPRAISER V1 TARGET

Self-Appraiser belongs to Central Mind.

It compares:

objective
approach/strategy
expected result
actual result
verification
available evidence

It should identify:

- success
- partial success
- failure
- uncertainty
- strategy weakness
- provider weakness
- missing information
- missing capability
- verification insufficiency
- reusable insight

LLMs may provide appraisal suggestions but cannot declare themselves or Central Mind correct.

---

# 16. LEARNER V1 TARGET

Learner converts worthwhile verified/appraised experience into structured learning candidates.

It must NOT permanently store every event.

It asks:

- Is this reusable?
- Is it non-trivial?
- Would retaining it save meaningful future work?
- Is evidence sufficient?
- Does equivalent knowledge already exist?
- Is this a correction/supersession?
- What provenance must be retained?
- What Memory IDs support it?

System-generated learning normally targets Derived/Learned knowledge.

Trainer Intake remains the source of Raw permanent memory.

Memory Service remains persistence authority.

---

# 17. CAPABILITY EXPANSION V1 TARGET

Capability Expansion handles demonstrated missing ability.

Flow:

demonstrated gap
  -> define requirement
  -> inspect Inventory/current capabilities
  -> determine whether capability genuinely absent
  -> create structured capability proposal
  -> authorization
  -> later Coding implementation
  -> tests
  -> verification
  -> Inventory discovery
  -> Guard default deny until authority granted

Capability Expansion may propose a plug.

It may NOT invent new kernel sockets or grant itself authority.

New capability != new authority.

---

# 18. GUARD / VERIFIER BOUNDARY

Guard:
pre-action authorization.

Verifier:
post-action correctness/evidence.

Do not merge them.

Tool execution remains through Broker + Guard.

Verification does not grant authorization.

Authorization does not prove correctness.

---

# 19. INVENTORY

Inventory remains authoritative component discovery.

Do not create a second component ownership registry.

New domains/tools/models/capabilities should integrate through generic discovery/contracts rather than hardcoded Central Mind lists wherever possible.

---

# 20. CURRENT IMPLEMENTATION STATE

Already established:

- Central Mind orchestration
- Inventory
- Broker
- Guard
- production capability/effect policies
- authenticated server path
- Memory Service
- governed memory proposal lifecycle
- Verifier separation
- Questioner
- model/provider registry
- domains/tools
- canonical intended design
- mechanically observed design system
- full suite previously passed 375 tests before new cognitive changes

Recent unvalidated change:

Scorer/Evidence V1 was implemented.

Changes included:

- Central Mind-owned evidence recorder
- JSONL evidence ledger
- removal of Organ.score_event ownership
- CentralMind Scorer(project_root)
- focused scorer tests added

Static checks passed.

Tests have NOT yet been run.

This implementation must now be reconciled with bounded temporary evidence and Section 3 permanent Memory ownership before being treated as final.

---

# 21. LEGACY EVOLUTION COMPONENT DECISION

Previous decision:

Observer -> transform into evidence/appraisal support
Proposer -> transform into Capability Expansion
Reviewer -> delete
Applicator -> delete
Scorer -> transform into evidence/outcome support
Questioner -> keep
_maybe_evolve() -> delete
CapabilityManager -> replace/reconcile later

Do not restore autonomous Reviewer/Applicator authority.

---

# 22. CLEANUP RULE

When a new canonical implementation is validated, remove obsolete duplicate implementation promptly.

Do not retain competing authority/execution paths merely "for later."

Security defense-in-depth may remain only when it has a concrete active purpose.

---

# 23. DEVELOPMENT METHOD FROM THIS POINT

Do not continue prolonged isolated theoretical development.

Next milestone:

IMPLEMENT AND CONNECT IN ONE INTEGRATION:

- Reasoner V1
- Self-Appraiser V1
- Learner V1
- Capability Expansion V1

Also reconcile:

- Scorer/evidence lifecycle
- shared LLM/provider availability
- legacy evolution removal
- CentralMind.process cognitive flow

Then:

1. focused integration tests
2. final Central Mind tests
3. regenerate design_actual.md
4. run full suite
5. start authenticated real server
6. connect real chat/UI path
7. test actual conversations/tasks
8. improve from observed behavior

After Central Mind V1 is operational:

- Coding becomes first major real working domain
- Chat/Languages become primary communication layer
- UI/UX evolves concurrently
- Trading and other domains follow
- actual experience drives Reasoner/Learner/Appraiser V2+

---

# 24. SERVER / LIVE TEST TARGET

The intended next phase is real application operation rather than only unit-test simulation.

User intends application/server work around port 8001.

Before changing the existing server binding, inspect the actual current app/server configuration and integrate deliberately rather than assuming port ownership.

Real testing should exercise:

authenticated user
  -> chat
  -> Central Mind
  -> Reasoner
  -> Memory recall
  -> provider/domain/tool selection
  -> Guard
  -> execution
  -> Verifier
  -> Self-Appraiser
  -> Learner
  -> response
  -> chat-state update

---

# 25. ECONOMIC / RESOURCE CONSTRAINT

Development should prioritize reaching useful operational capability.

Physical storage ceiling is approximately 850 GB.

Heavy permanent retention is not acceptable by default.

The system should become useful for building real projects and later trading/indicator/bot or other revenue-producing work before expensive intelligence/storage expansion.

V1 should therefore be:

- structurally complete
- safe
- testable
- extensible
- resource-conscious
- operational

not maximally elaborate.

---

# 26. NEXT EXACT OBJECTIVE

Do NOT continue isolated Scorer work.

Next development operation:

Build Reasoner V1 + Self-Appraiser V1 + Learner V1 + Capability Expansion V1 as one connected Central Mind integration.

During that implementation:

- reconcile temporary evidence
- preserve Section 3 as permanent memory authority
- remove obsolete evolution path
- make compatible LLM providers generally available for cognitive selection
- preserve Guard/Verifier boundaries
- preserve Memory Service boundary
- preserve Inventory authority
- preserve architecture lock
- record structural deviations here if any become essential

After implementation, test the integrated cognitive path rather than testing each subsystem as an unrelated project.

---

# 27. CHANGE LOG

## Central Mind architecture lock

Decision:
Major Central Mind layers are now frozen except for essential structural corrections.

Reason:
Repeated architectural drift and rediscovery were slowing development and causing loops.

Impact:
Future work should improve implementations behind stable contracts rather than repeatedly redesigning the kernel.

## Development continuity file introduced

Decision:
Maintain this temporary follow-up file throughout Central Mind V1 stabilization.

Reason:
Avoid repeatedly rediscovering prior decisions, implementation state and next objectives.

Impact:
Consult this file first when development context is uncertain. Inspect source again only when implementation truth is needed or a discrepancy/problem is suspected.



---

# COGNITIVE V1 INTEGRATION PATCH — 2026-10-16T17:02:10

The first integration attempt stopped safely because it expected a route
object while the actual Router returns a list of organs.

The exact CentralMind.process implementation was inspected.

The corrected integration was then applied against the real process shape.

Changes now present:

- Reasoner V1 connected to each Central Mind turn.
- Memory recall occurs through Central Mind's MemoryClient.
- Self-Appraiser evaluates each routed result after Verifier.
- Learner receives appraised experience and only submits explicit reusable
  knowledge candidates.
- Learner requests Derived memory, never Raw.
- Capability Expansion records demonstrated missing-capability proposals.
- Scorer is bounded temporary operational experience, not permanent Memory.
- Objective outcome, verification state and disposition are separate.
- Old autonomous evolution path is disconnected from Central Mind.
- The old undefined `text` objective reference was removed.
- Domain Memory injection now preserves the already-bound ToolBroker.
- Legacy Observer/Proposer/Reviewer/Applicator files remain physically present
  only until Cognitive V1 validation succeeds; they are no longer connected
  to canonical execution.

No test-suite success is claimed by this checkpoint.

Static check failures: []
Compile errors: []

---

# 28. CENTRAL MIND V1 IMPLEMENTATION CLOSURE — 2026-10-16

Status:

CENTRAL MIND V1 IMPLEMENTATION REGRESSION GATE CLOSED.

Final complete regression:

- test files: 40
- tests run: 383
- failures: 0
- errors: 0
- skipped: 0
- success: true

Validated implementation:

- Reasoner V1 is connected to the real CentralMind.process() cycle.
- Self-Appraiser V1 evaluates routed results after verification.
- Learner V1 receives appraised experience and proposes explicit reusable
  system learning as Derived knowledge.
- Capability Expansion V1 represents demonstrated missing-capability gaps but
  cannot grant authority.
- Scorer is bounded temporary in-memory operational evidence.
- The previous JSONL/permanent evidence-ledger direction is superseded.
- Section 3 remains the sole permanent reusable knowledge/experience system.
- Raw Memory is reserved for authenticated Trainer Intake.
- Central Mind proposal approval cannot create Raw Memory.
- Untestable system proposals are rejected rather than downgraded to Raw.
- Tested and Derived remain governed system-learning classes.
- Objective outcome, verification state and Central Mind disposition remain
  semantically separate.
- Installed generative models participate in a shared candidate pool.
- Registry domain assignments are bootstrap ranking/guidance, not permanent
  ownership.
- Learned contextual provider evidence may reorder model candidates when
  sufficient evidence exists.
- Embedding models remain outside the generative candidate pool.
- Inventory remains discovery authority.
- Guard remains pre-action authorization.
- Verifier remains post-action correctness/evidence evaluation.
- Memory Service remains permanent-memory authority.
- Legacy Observer, Proposer, Reviewer and Applicator implementation files were
  removed after Cognitive V1 validation.
- The old `_maybe_evolve()` execution path is removed.

Superseded checkpoint statements:

Earlier entries saying:

- Scorer/Evidence V1 was unvalidated;
- Scorer used a JSONL permanent evidence ledger;
- Cognitive V1 had not yet passed tests;
- legacy Observer/Proposer/Reviewer/Applicator files remained pending removal;

are historical intermediate states and are no longer current implementation
truth.

Architecture lock:

The Central Mind V1 structural layers are now considered closed.

Do not redesign finalized Central Mind layers merely to improve intelligence.

Future improvements should normally occur behind the stable contracts as
Reasoner/Learner/Appraiser/provider-selection/capability-expansion V2+.

Any essential structural deviation must be recorded here with:

1. what changed;
2. why the existing contract was insufficient;
3. security/authority impact;
4. compatibility impact;
5. migration impact.

Next operational milestone:

1. mechanically regenerate `design_actual.md` from the real implementation;
2. compare intended design against observed implementation;
3. start authenticated live server/chat;
4. exercise Central Mind through real requests;
5. move into Coding capability/domain development;
6. develop Chat + Languages and UI/UX concurrently;
7. begin accumulating real governed experience;
8. add Trading and other useful domains incrementally;
9. use actual experience to drive Cognitive V2+ rather than reopening V1
   theoretically.

Do not assume a new server port from planning notes.

The last known implemented server endpoint remains the endpoint defined by the
actual server configuration and must be read mechanically before launch.

---


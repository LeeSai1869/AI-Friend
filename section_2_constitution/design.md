# AI Friend V1 — Canonical Architecture and Design

Status: CANONICAL INTENDED DESIGN
Updated: 2026-10-16

This document defines what AI Friend V1 is intended to become and the
architectural rules that all implementation work must preserve.

It is a specification, not a mechanical description of the current code.

For the mechanically observed implementation state, see:

    section_2_constitution/design_actual.md

When implementation and this document disagree, the disagreement must be
identified explicitly. Code must not silently redefine the architecture.

===============================================================================
1. PURPOSE
===============================================================================

## 1.1 What AI Friend V1 is

AI Friend V1 is a persistent, extensible, model-independent AI system.

It is not one LLM wrapped in a chat interface.

It is a governed system composed of:

- a Central Mind that coordinates;
- discoverable organs that provide capabilities;
- domains that own domain-specific intelligence;
- tools that perform actions;
- models that provide reasoning/generation capabilities;
- a Memory Service that owns persistent learned information;
- a Constitution that defines permanent authority and behavioral rules;
- Guards that authorize actions before execution;
- Verifiers that determine correctness after work is performed;
- authenticated human principals that provide real authority;
- an audit trail that records security and learning decisions;
- a chat/application layer through which humans interact with the system.

The system must be able to grow without repeatedly redesigning the Central Mind.

A new domain, tool, model, source, renderer, or future organ should normally be
introduced by adding a component with a manifest that satisfies an existing
contract.

The kernel coordinates plugs.

It must not be rewritten every time a new plug is added.


## 1.2 Primary objective

The primary objective is to create an AI system that can:

1. receive a human request;
2. understand what capabilities are required;
3. discover appropriate components;
4. ask for missing information when necessary;
5. retrieve relevant memory and evidence;
6. reason and plan;
7. delegate work;
8. authorize every consequential action;
9. execute through constrained tools;
10. verify the result;
11. learn from evidence;
12. preserve provenance and history;
13. improve without silently granting itself new authority.


## 1.3 Local-first, hybrid by design

The architecture must not depend on one model vendor or one machine.

It must support:

- local models;
- remote models;
- OpenAI-compatible providers;
- Ollama;
- future providers;
- local tools;
- network tools;
- additional computers acting as subordinate workers;
- future mobile or lightweight clients.

Models are replaceable workers.

They are not the architecture.


## 1.4 The long-term principle

AI Friend should become more capable by adding knowledge, components,
behaviors, models, tools, evidence and tested capabilities.

Capability growth must not require authority growth.

Learning something new does not automatically grant permission to act on it.


===============================================================================
2. NON-NEGOTIABLE ARCHITECTURAL LAWS
===============================================================================

These laws apply across the entire project.

## 2.1 Central Mind is coordinator, not universal implementation

Central Mind owns coordination.

It may:

- inspect the trusted inventory;
- route requests;
- coordinate organs;
- request memory through the Memory Service;
- request tools through the Broker;
- request models by capability;
- ask questions;
- combine results;
- initiate verification;
- initiate learning workflows;
- create proposals;
- coordinate authorized work.

It must not become a collection of hard-coded implementations for individual
domains, tools, models or future capabilities.


## 2.1.1 Three independent Central Mind loops

Central Mind separates its activity into three bounded loops:

- **Regular operation** receives requests, coordinates domains, verifies
  results and returns a response.
- **Self-assessment** reviews operational evidence and may submit audited
  proposals for Administrator review; it cannot modify itself.
- **Feature expansion** evaluates demonstrated capability gaps and submits
  proposals; it cannot install capabilities or grant authority.

Each loop owns its implementation in a separate package. Regular operation
may dispatch work to the other loops through their public interfaces, but
does not contain their decision logic. Questionnaire is an intentionally
shared service; other shared services are explicit dependencies, not shared
activity ownership.


## 2.2 Components are discovered, not hard-coded

The system must discover organs from trusted component roots and manifests.

Central Mind must not require code such as:

    if tool == "filesystem"
    if domain == "coding"
    if model == "qwen"
    if capability == "some_future_capability"

unless the distinction is itself a true kernel-level architectural rule.

Component-specific behavior belongs to the component.


## 2.3 Manifests describe plugs

A manifest declares what a component is capable of providing and what
authority its operations require.

The manifest does not grant authority.

Discovery answers:

    "What exists?"

The manifest answers:

    "What does this component claim to provide or require?"

The Guard answers:

    "May this authenticated principal, through this execution chain,
     perform this operation with these effects?"

These are separate questions.


## 2.4 Generic does not mean permissive

Unknown components, capabilities, effects, scopes, identities or malformed
requests fail closed.

Adding a folder must never automatically create authority.

A newly discovered component may exist in inventory while still being unable
to perform protected actions until trusted policy explicitly permits them.


## 2.5 Authority comes from authenticated humans

Authority originates from trusted backend authentication.

A model, domain, tool, client message, manifest or Central Mind cannot invent
human authority.

Client-supplied fields such as:

    role
    actor
    approved_by
    administrator
    trainer

are not trusted authority.

The backend-authenticated account is the authority source.


## 2.6 Identity and authority are different

The system records both:

1. WHO authorized the request;
2. WHAT components executed it.

The execution chain may look like:

    authenticated human
        -> Central Mind
        -> domain/model
        -> tool
        -> operation
        -> effects

The human principal provides authority.

The component chain provides execution provenance.

A component appearing in the chain does not make it a human authority.


## 2.7 Guard before execution

Every consequential tool action must be authorized before execution.

The Guard evaluates declared requirements and actual classified effects before
the tool is allowed to act.

A denied operation must not execute partially.


## 2.8 Verification after work

Authorization and correctness are different.

Guard asks:

    "Is this operation permitted?"

Verifier asks:

    "Did the work produce an acceptable result?"

Verifier must not be used as an authorization mechanism.

Guard must not be used as a substitute for result verification.


## 2.9 Effects, not tool names, determine resource authority

Security policy must not depend on knowing every present or future tool name.

Tools declare deterministic effects.

Effects are classified into trusted resource/effect categories.

Guard policy evaluates those effects.

Therefore a future tool cannot bypass protection merely because its name was
not known when the Guard was written.


## 2.10 Fail closed

When security-relevant information is missing, malformed, ambiguous or
untrusted, execution is denied.

Examples include:

- missing trusted principal;
- missing Guard;
- missing security requirement;
- unknown capability;
- malformed effect;
- empty effect set for guarded execution;
- unknown resource;
- unsupported scope;
- missing effect policy;
- untrusted component identity.


## 2.11 No hidden second authority system

There must be one canonical authorization path.

Tools may contain neutral mechanical protections such as path containment,
syntax validation or operation semantics.

They must not maintain a second independent authorization policy that competes
with the Guard.

Duplicate legacy authorization systems must be removed once their replacement
is validated.


## 2.12 No duplicate canonical implementations

When a new implementation becomes canonical and is validated, obsolete
duplicate implementations must be removed.

Do not keep stale authority paths, execution paths, registries or alternative
implementations "just in case."

Backups belong outside the active runtime architecture.


## 2.13 Memory has one service boundary

Every organ, domain, model, tool and Central Mind component accesses persistent
AI memory through the standard Memory Service interface.

No component may directly mutate Memory Service storage.

Direct filesystem access to protected memory storage is not a substitute for
Memory Service access.


## 2.14 Learning is not direct memory writing

Components propose knowledge.

Memory Service persists proposals.

Central Mind coordinates evaluation.

Domain-specific evaluators test knowledge when possible.

Memory Service alone performs the final memory state transition.

A component cannot make its own claim authoritative merely by writing a file.


## 2.15 Provenance is permanent

Important decisions must retain provenance.

The system should be able to answer:

- who initiated this?
- which authenticated account authorized it?
- which components handled it?
- what evidence supported it?
- what verification occurred?
- what changed?
- what existed before?
- why was it accepted, rejected, superseded or retired?


## 2.16 Protected Core remains protected

Central Mind, authentication, authorization, Guard infrastructure and the
Constitution are protected architecture.

Ordinary application operations must not be able to rewrite them merely
because a generic filesystem tool can technically address their paths.


## 2.17 Process execution is high risk

Terminal/process execution is a distinct high-risk capability.

The existence of a terminal tool does not imply permission to execute
processes.

Process execution remains denied until an explicit constrained execution
policy is designed and granted.


===============================================================================
3. HUMAN AUTHORITY MODEL
===============================================================================

AI Friend distinguishes human authority from internal execution components.

The principal human roles are:

- Administrator
- Trainer
- User


## 3.1 Administrator

The Administrator governs the application and its human access.

The Administrator may, through authorized workflows:

- authenticate;
- inspect permitted system state;
- inspect/search memory read-only;
- manage ordinary accounts;
- manage registration settings;
- create the designated Trainer account;
- inspect security/audit information;
- review proposals where policy permits;
- approve or reject permitted governed operations.

The Administrator does not gain arbitrary direct filesystem mutation of
protected architecture merely by being Administrator.

Administrative authority is still mediated by capabilities, effects and
Guard policy.


## 3.2 Trainer

The Trainer is the primary human knowledge authority.

The Trainer may, through authorized workflows:

- submit knowledge;
- correct knowledge;
- provide training material;
- review learning proposals;
- authorize permitted memory lifecycle changes;
- provide high-value evidence;
- participate in retirement, supersession or deletion workflows where policy
  explicitly allows them.

Trainer claims remain evidence with provenance.

"Trainer said it" is not a reason to destroy contradictory evidence or bypass
verification.


## 3.3 Ordinary User

An ordinary User may use enabled application features.

A User receives only the capabilities explicitly granted to that role.

A User cannot promote themselves by sending a role string from the UI.


## 3.4 Designated privileged identities

The architecture currently requires:

- exactly one designated Administrator account;
- exactly one designated Trainer account.

Privileged identities are created and enforced by the backend authentication
service.


## 3.5 Session authority

Authority is session-based and backend validated.

A session must be revalidated for protected requests.

A newer login may invalidate an older active session according to authentication
policy.

A stale open connection does not retain authority after its session has been
revoked.


===============================================================================
4. TRUST AND EXECUTION CHAIN
===============================================================================

A protected action is understood as a chain, not as an isolated function call.

Conceptually:

    Human Principal
        |
        v
    Central Mind
        |
        +--> Domain / Model / Other Organ
        |
        v
    Bound Tool Broker
        |
        v
    Tool Operation
        |
        v
    Declared Effects
        |
        v
    Effect Classification
        |
        v
    Guard Authorization
        |
        v
    Execution
        |
        v
    Verification
        |
        v
    Result / Learning / Audit


## 4.1 Trusted principal

The trusted principal contains authenticated backend identity information.

It is not constructed from arbitrary model or client arguments.


## 4.2 Trusted component chain

Central Mind and delegated components are represented as trusted component
identities.

The chain is constructed by infrastructure.

Model/tool arguments cannot forge or shorten it.


## 4.3 Bound Broker views

The master ToolBroker is coordination/security infrastructure.

It is not a raw execution API.

Execution occurs through a bound Broker view representing the trusted requester
chain.

Examples:

    Central Mind -> Tool

or:

    Central Mind -> Coding Domain -> Tool


## 4.4 Tool ownership

Tool operation ownership comes from the authoritative Inventory identity.

A manifest cannot steal another component's already registered operation.

A fabricated lookalike component cannot impersonate an authoritative
Inventory object.


===============================================================================
5. CENTRAL MIND
===============================================================================

Central Mind is the orchestration kernel.

It should remain small enough that its responsibilities can be understood and
audited.

Its major concerns are logically separated.


## 5.1 Inventory

Inventory discovers trusted components.

Current trusted component roots include:

- section_5_domains
- section_7_models
- section_8_tools

Inventory establishes trusted component identity from the discovery root.

A manifest may provide metadata, but it cannot redefine its trusted component
kind.


## 5.2 Router

Router decides which discovered organs are relevant to a request.

Routing should increasingly use:

- declared capabilities;
- keywords;
- request shape;
- domain context;
- confidence;
- future learned routing evidence.

Routing should not require Central Mind to know every organ by name.


## 5.3 Questioner

Questioner obtains missing information.

The system should ask rather than invent required facts.

Questions should be:

- specific;
- minimal;
- contextual;
- one decision at a time when practical;
- reusable by the requesting organ.

A clarification should resume the same trusted delegation context rather than
silently becoming a new authority chain.


## 5.4 Composer

Composer combines compatible organ outputs.

Composition is structural.

It should not erase provenance or make an unverified component result appear
verified.


## 5.5 Verifier

Verifier performs post-work correctness checks.

Each domain may implement domain-specific verification.

A result that claims success without required evidence must not automatically
be accepted as success.


## 5.6 Scorer

Scoring records evidence about performance and beliefs.

Long term, scores represent confidence derived from evidence, not immutable
truth.


## 5.7 Observer

Observer detects signals such as:

- repeated failures;
- repeated corrections;
- unhandled requests;
- stale knowledge;
- low-confidence behavior;
- missing capabilities;
- contradictory evidence.


## 5.8 Proposer

Proposer converts observed signals into structured proposals.

A proposal is not authority.

A proposal may request:

- new knowledge;
- new behavior;
- refinement;
- capability development;
- supersession;
- retirement;
- governed architecture work.


## 5.9 Reviewer

Review is a decision stage, not a bypass around Guard or Memory Service.

Future autonomous review may classify proposals by evidence, risk and authority
requirements.

Any final action still passes through the appropriate authoritative service
and Guard path.


## 5.10 Applicator

Legacy architecture treated a single Applicator as the universal writer.

That is no longer the governing design.

Mutation authority belongs to the appropriate service/tool boundary:

- filesystem mutation through guarded filesystem tools;
- memory mutation through Memory Service;
- account mutation through AuthService;
- future specialized state through its owning service.

No universal "magic writer" should bypass those boundaries.


## 5.11 Tool loop

The ToolLoop coordinates model-driven tool use.

It must use bound Broker execution.

The model may choose among exposed operations, but the model does not decide
whether those operations are authorized.


===============================================================================
6. THE ORGAN MODEL
===============================================================================

An organ is a discoverable component implementing a defined system contract.

Possible organ kinds include:

- domains;
- models;
- tools;
- future sources;
- future renderers;
- future specialized workers.

The list is extensible.


## 6.1 Plug and socket principle

Central Mind defines stable sockets.

Organs provide plugs.

A new plug must conform to the socket.

Adding a plug must not require redesigning the socket.


## 6.2 Manifest

An organ manifest may declare information such as:

- identity metadata;
- entry module;
- entry object;
- capabilities;
- keywords;
- exported operations;
- security requirements;
- memory domain;
- future service metadata.

The trusted discovery system determines security-sensitive ownership/kind.


## 6.3 Adding an organ

The normal pattern is:

1. create the component folder under a trusted component root;
2. provide its manifest;
3. implement the expected interface;
4. provide deterministic security/effect declarations where required;
5. add tests;
6. restart/rescan Inventory.

Central Mind should not need a new component-specific branch.


===============================================================================
7. DOMAINS
===============================================================================

Domains own domain-specific intelligence.

They are not merely routing labels.

A domain may own:

- domain rules;
- domain knowledge interpretation;
- domain-specific verification;
- domain-specific planning;
- domain-specific testing;
- learned behaviors;
- scoring logic;
- specialized model selection;
- domain memory classification.


## 7.1 Coding

Coding is the first major implementation domain.

Its intended responsibilities include:

- inspect;
- understand;
- plan;
- write;
- test;
- debug;
- verify;
- learn from coding evidence.

Coding work must eventually be capable of operating through the same Guard,
Broker and verification architecture as every other domain.


## 7.2 Languages

Languages handles natural and technical language knowledge and translation.

It must not become an unverified direct memory writer.

Learned language knowledge follows the standard proposal/evaluation/Memory
Service lifecycle.


## 7.3 Trading

Trading is a specialized analytical domain.

Intended capabilities include:

- market analysis;
- feature interpretation;
- backtesting;
- forecasting;
- strategy evaluation;
- evidence/scoring.

Live trade execution is outside the current intended authority.


## 7.4 Image

Image will combine structured concepts, image models and rendering tools.

Long-term image generation should support composition-driven generation rather
than relying only on unconstrained prompts.


## 7.5 Video

Video follows the same component philosophy as Image, extended across time.

It may use specialized generation/rendering models and tools without changing
Central Mind.


## 7.6 General

General provides fallback/general handling where no specialized domain is a
better match.

It must not become a dumping ground for functionality that belongs in a
dedicated organ.


===============================================================================
8. TOOLS
===============================================================================

Tools perform actions.

They do not receive authority merely because they exist.

A tool should:

1. expose a focused operation;
2. validate mechanical inputs;
3. resolve resources neutrally;
4. declare deterministic effects before execution;
5. execute only after Broker/Guard authorization;
6. return structured results.


## 8.1 Tools do not own persistent conceptual memory

A filesystem tool knows how to manipulate files.

It does not decide what knowledge means.

A web tool retrieves network information.

It does not decide whether that information becomes learned truth.

A terminal tool executes processes.

It does not decide whether process execution is authorized.


## 8.2 Current tool families

Current tool components include:

- filesystem;
- folders;
- intake;
- scaffold;
- terminal;
- vision;
- web.

This list is not architectural law.


## 8.3 Deterministic effects

Before execution, a tool describes what it intends to affect.

Examples:

- read exact file;
- read children;
- read tree;
- create directory;
- create file;
- write file;
- network access;
- service invocation;
- process execution;
- semantic memory proposal.

Effects must cover the actual mutations the tool may perform.


## 8.4 Path containment

Neutral path containment is infrastructure, not authorization.

A tool may reject a path that escapes its workspace.

That does not mean the remaining path is authorized.

Authorization still belongs to Guard.


===============================================================================
9. MODELS
===============================================================================

Models are replaceable reasoning/generation workers.

They are not trusted authorities.


## 9.1 Model independence

Domains and Central Mind should request models by capability and suitability,
not permanently bind architecture to one model name.


## 9.2 Providers

The architecture supports provider abstraction.

Current provider direction includes:

- Ollama;
- OpenAI-compatible endpoints;
- local fallback/test providers;
- future providers.


## 9.3 Model roles

Potential model capabilities include:

- chat;
- coding;
- translation;
- reasoning;
- vision;
- forecasting;
- image generation;
- video generation.

These are capabilities, not permanent hard-coded model identities.


## 9.4 Model output is untrusted input

A model cannot:

- grant itself permissions;
- fabricate a principal;
- override manifest security requirements;
- forge the execution chain;
- directly mutate protected memory;
- bypass verification.


===============================================================================
10. TOOL BROKER
===============================================================================

ToolBroker is the controlled execution gateway between coordinating components
and tools.


## 10.1 Responsibilities

Broker:

- discovers/loads authorized tool implementations from Inventory;
- registers operations;
- preserves authoritative operation ownership;
- exposes bound execution views;
- obtains deterministic tool effects;
- classifies effects;
- constructs Guard requests;
- calls Guard before execution;
- enforces fail-closed behavior;
- records tool execution results.


## 10.2 No raw master execution

The master Broker must not expose an unrestricted execution path.

Execution is through trusted bound views.


## 10.3 Guardless execution

A Broker may exist without Guard/principal for discovery or structural
purposes.

Actual bound tool execution without both trusted Guard and trusted principal
must fail closed before tool control.


===============================================================================
11. GUARD SYSTEM
===============================================================================

Guard is the pre-action authorization system.

It is deliberately separate from domain correctness verification.


## 11.1 Two authorization gates

The current architecture evaluates:

1. capability authorization;
2. effect/resource authorization.

Both must pass.


## 11.2 Capability policy

Capability policy answers whether the authenticated principal possesses every
required capability.

Capability names are extensible strings.

The architecture must not be limited to today's vocabulary.


## 11.3 Effect policy

Effect policy evaluates what the operation will actually affect.

It considers:

- action;
- scope;
- classified resource;
- crossed protected boundaries;
- trusted execution chain;
- semantic target.


## 11.4 Resource classification

Filesystem resources are classified semantically.

Current categories include concepts such as:

- kernel;
- constitution;
- memory;
- component;
- workspace;
- data;
- runtime state;
- external.

The classification system may evolve, but unknown resources fail closed.


## 11.5 Boundary-aware authorization

A broad filesystem operation may cross protected semantic boundaries.

Authorization must account for those crossed boundaries rather than approving
only the starting path.

For example, permission to recursively read a workspace root must not silently
grant recursive access to protected memory merely because memory exists under
that root.


## 11.6 Hard protections

Some restrictions are architectural hard boundaries and cannot be enabled
merely by adding an ordinary rule-table entry.

Current examples include:

- external filesystem access through ordinary workspace effects;
- direct filesystem mutation of Memory Service storage;
- protected kernel mutation;
- Constitution mutation through ordinary application operations.


## 11.7 Production capability posture

Current production policy is intentionally conservative.

Examples:

Administrator currently receives ordinary workspace/network capabilities
required by enabled workflows.

Trainer additionally receives explicitly permitted knowledge/workspace
capabilities.

Ordinary User receives only enabled user capabilities.

Process execution is not implicitly granted to any human role.

Future capabilities default to denied until explicitly granted.


===============================================================================
12. AUTHENTICATION
===============================================================================

Authentication is a backend security service.

It is not a UI convention.


## 12.1 Responsibilities

AuthService owns:

- account identity;
- password verification;
- role assignment;
- privileged-account uniqueness;
- registration policy;
- sessions;
- session revocation;
- authentication audit.


## 12.2 Passwords

Passwords are stored using a password-derived cryptographic hash.

Plaintext passwords are not persistent account state.


## 12.3 Sessions

Session tokens are security credentials.

The server revalidates them before protected operations.

A client cannot preserve authority by retaining stale role information after a
session has been revoked.


===============================================================================
13. MEMORY SERVICE
===============================================================================

Memory is a protected service, not a shared directory API.


## 13.1 Purpose

Memory Service owns persistent AI knowledge state.

It provides controlled interfaces for:

- recall;
- proposal;
- review;
- commitment;
- rejection;
- lifecycle/history;
- provenance.


## 13.2 Single memory boundary

Components receive Memory clients/interfaces.

They do not receive raw storage authority.


## 13.3 Domain ownership and shared recall

Knowledge may be associated with domains while still being recallable through
the shared Memory Service according to service policy.

A domain may contribute knowledge relevant to another domain through the
proposal mechanism.


## 13.4 Proposal first

Knowledge submission creates a proposal.

A pending proposal is not committed memory.


## 13.5 Central Mind evaluation

Central Mind receives the proposal and identifies the appropriate domain
evaluator using trusted manifest metadata.

Central Mind coordinates evaluation.

It does not bypass Memory Service by writing the resulting entry itself.


## 13.6 Testable knowledge

If knowledge is testable and a unique appropriate evaluator exists, the domain
may evaluate it.

Passing evaluation may classify the knowledge as tested.

Failing evaluation rejects the proposal.

Absence of a valid evaluator must never falsely promote knowledge to tested.


## 13.7 Untestable knowledge

Knowledge that cannot currently be operationally tested may be retained as raw
knowledge with appropriate provenance rather than falsely marked tested.


## 13.8 Lifecycle

Long-term memory lifecycle should distinguish evidence states such as:

- proposed;
- raw;
- diagnostically checked;
- source verified;
- operationally tested;
- contradicted;
- superseded;
- retired;
- rejected.

The exact schema belongs to Memory Service and may evolve without requiring
Central Mind to own storage implementation.


## 13.9 Deletion

Deletion is a governed lifecycle operation.

Internal agents and Central Mind cannot authorize deletion.

They may propose deletion/retirement/supersession where the service contract
allows it.

Any destructive lifecycle action requires explicit trusted human authority
according to Constitution and Memory Service policy.

History/provenance must be preserved.

Where retirement or supersession can satisfy the requirement, preservation is
preferred over physical destruction.


===============================================================================
14. INTAKE AND LEARNING
===============================================================================

Intake is the deliberate entrance for new knowledge and source material.


## 14.1 Intake is not approval

Intake may:

- inspect submitted material;
- structure it;
- identify a target domain;
- ask the Trainer what the material is, how it should be interpreted, and
  what scope, assumptions or limitations matter;
- store the source and Trainer context as Raw Memory.

Raw Memory is unverified source material, not an assertion that the material
is true. Central Mind owns its recall and decides when to route it for analysis
or testing. Domains do not own the shared Raw Memory collection.


## 14.2 Canonical learning flow

The Trainer Intake flow is:

    source/material
        -> Intake
        -> Central Mind presents relevant Trainer questions
        -> authenticated Trainer supplies context
        -> Memory Service stores source and context as Raw Memory
        -> Central Mind recalls relevant Raw Memory
        -> assigned domain analyzes or tests it
        -> any reusable Tested/Derived learning follows its separate
           governed proposal and verification lifecycle


## 14.3 Memory is not learning

Recording information alone is not sufficient.

Learning means future behavior, reasoning, recall, scoring or decisions can
change because validated information became available.

Raw Intake makes unverified material available for Central Mind reasoning,
analysis and testing. It does not automatically promote the material to Tested
or Derived Memory.


## 14.4 Behavioral learning

Future learned behaviors must be governed executable artifacts.

A learned behavior must not become arbitrary self-modifying code with implicit
authority.

Creation, testing, activation, disabling and supersession require explicit
lifecycle rules.


## 14.5 Failed attempts are evidence

A failed tested behavior or hypothesis may itself be useful evidence.

Failure should be preserved with context so the system can avoid blindly
repeating the same failed approach under equivalent conditions.


===============================================================================
15. EVIDENCE, BELIEFS AND SCORING
===============================================================================

AI Friend should distinguish information from confidence.


## 15.1 Belief is not truth

A belief represents a claim plus evidence and confidence.

Confidence may rise or fall as evidence changes.


## 15.2 Evidence provenance

Evidence should identify:

- source;
- time;
- domain;
- relevant context;
- verification method;
- result;
- relationship to the belief.


## 15.3 Sources

Possible evidence sources include:

- persistent memory;
- authenticated Trainer input;
- user input;
- models;
- tests;
- tools;
- files;
- internet sources;
- observed outcomes.

Source type influences interpretation but must not erase contradictory
evidence.


## 15.4 Trainer evidence

Trainer evidence may begin with a strong prior.

The Trainer is still a source, not an infallible oracle.


===============================================================================
16. QUESTIONING AND REASONING
===============================================================================

The system must not compensate for missing information by confidently
inventing it.


## 16.1 Question-first when required

When a required decision cannot be made from available evidence, the system
asks.


## 16.2 No questioning loops

Questioning must make measurable progress.

The same unresolved question must not be repeatedly asked without new reason.

The requesting component should declare what information is missing and why it
is needed.


## 16.3 Planning

Planning converts goals into explicit steps, dependencies and verification
criteria.

Plans do not grant authority.

Every planned action still passes through the normal execution controls.


## 16.4 Reasoning

Reasoning may use one or more models and domain knowledge.

Reasoning output is evidence/work product, not privileged instruction.


===============================================================================
17. VERIFICATION
===============================================================================

Verification is mandatory wherever a meaningful correctness test exists.


## 17.1 Domain verification

Domains own specialized correctness knowledge.

Examples:

Coding may verify:

- writes succeeded;
- syntax checks passed;
- tests passed;
- claimed files actually changed;
- requested behavior exists.

Languages may verify:

- structure;
- grammar rules;
- translation constraints;
- source/target consistency.

Trading may verify:

- calculations;
- data alignment;
- backtest methodology;
- leakage constraints.

Image/video may verify:

- requested structural properties;
- render completion;
- artifact validity.


## 17.2 No evidence, no success claim

A component must not claim verified success when required verification evidence
is missing.


## 17.3 Verification does not authorize

A perfectly correct action can still be forbidden.

A permitted action can still produce an incorrect result.

Both systems are required.


===============================================================================
18. CONSTITUTION
===============================================================================

The Constitution defines governing rules.

Current constitutional concerns include:

- core principles;
- authority;
- coding;
- trading;
- image;
- video;
- future domain rules.


## 18.1 Constitution is not ordinary content

Constitutional files belong to protected architecture.

They cannot be rewritten by ordinary tool authority.


## 18.2 Policy interpretation

Guard enforcement should encode enforceable security rules in deterministic
policy.

Do not depend on an LLM reading prose at execution time to decide whether a
security-critical write is allowed.


## 18.3 Constitution and implementation

Prose rules and executable enforcement should agree.

When they diverge, the discrepancy must be visible and corrected deliberately.


===============================================================================
19. CHATBOX
===============================================================================

Chatbox is the human-facing conversational interface.

It is more than transport, but it is not an authority source.


## 19.1 Responsibilities

Chatbox may manage:

- conversation presentation;
- questions;
- notifications;
- tool status;
- conversational state;
- language rendering of a response draft requested by Central Mind;
- future lexicon;
- future topic continuity;
- future learned associations.

Chat receives the user's message and Chat ID from the application path. The
application supplies current-turn UI observations separately; Chat transports
them without selecting a domain or deciding how the task is executed. A
Chat-rendered draft is returned to Central Mind for review before presentation.

Chat and Coding remain separate components and responsibilities. The Coding
window may present an independent Chat pane beside the editor, while Chat also
remains available as its own window. Their current project context is shared
through Central Mind: Coding reports project selection to Central Mind, which
exposes that session context to Chat and includes it when reasoning about a new
turn. Chat does not query or control Coding, and sharing context does not merge
their interfaces or responsibilities.


## 19.2 Authority separation

Chatbox presents authenticated application state.

It does not decide the user's backend role.

It cannot make a request privileged by inserting authority fields.


## 19.3 Conversation memory

Conversation state and persistent learned Memory Service knowledge are
different concepts.

Chat history should not silently become permanent learned knowledge.


===============================================================================
20. APPLICATION / UI
===============================================================================

The intended desktop shell is Tauri-based.

The user should ultimately interact with AI Friend as an application rather
than as a collection of Terminal commands.


## 20.1 Intended major surfaces

The application may provide:

- conversation panel;
- code/editor panel;
- file tree;
- terminal/process panel;
- Intake interface;
- authentication;
- question dialogs;
- learning/review UI;
- Memory inspection;
- Guard/audit inspection;
- domain selection;
- model status;
- distributed-worker status.


## 20.2 UI is not trusted backend authority

Buttons and panels request operations.

They do not enforce the final security decision.

Backend services remain authoritative.


## 20.3 Question windows

Missing information should be requested through small contextual questions.

The UI should support:

- choices;
- defaults;
- free-form answers;
- redefine;
- cancel;
- provenance back to the requesting organ.


===============================================================================
21. DISTRIBUTED EXECUTION
===============================================================================

AI Friend is intended to support additional machines without splitting its
identity or memory authority.


## 21.1 Central brain, subordinate compute

The primary system may remain the authoritative coordinator while subordinate
machines provide compute/resources.


## 21.2 Workers are components, not independent authorities

A remote worker may:

- run a model;
- process data;
- execute a permitted task;
- return results.

It does not automatically receive authority over Memory Service, Constitution,
authentication or Guard policy.


## 21.3 Shared memory through service

Remote machines must not synchronize memory by directly editing the memory
storage directory.

They use the same governed Memory Service contract.


## 21.4 Future worker trust

Distributed workers will require explicit:

- authentication;
- component identity;
- capability declarations;
- transport security;
- effect declarations;
- resource constraints;
- audit provenance.

This must be designed before remote execution is trusted.


===============================================================================
22. COMPOSITION SYSTEM
===============================================================================

Composition remains a long-term architectural concept, especially for image,
video and structured artifact generation.


## 22.1 Composition

A composition is a structured tree of concepts and values.

It is a specification, not merely generated prose.


## 22.2 Concepts

A concept may contain:

- identity;
- definition;
- attributes;
- allowed values;
- defaults;
- references;
- evidence;
- renderer association.


## 22.3 Renderers

A renderer converts a structured concept/composition into a concrete artifact
or model instruction.

Renderers should be modular.

Adding a concept-specific renderer should not require rewriting the entire
image/video system.


## 22.4 Why structured composition matters

It provides:

- reuse;
- controllability;
- inspectability;
- smaller reusable units;
- deterministic editing;
- composability;
- model independence.


===============================================================================
23. SECURITY RESOURCE MODEL
===============================================================================

Security decisions are based on semantic resources and effects.


## 23.1 Filesystem resources

Paths are classified by architectural meaning, not only string prefix.


## 23.2 Semantic effects

Not every action is a filesystem operation.

Examples include:

- network access;
- service access;
- process execution;
- semantic memory operation.

These remain distinct effect classes.


## 23.3 Exact, children and tree scopes

Filesystem effects distinguish reach.

Conceptually:

    exact
        only the specified resource

    children
        immediate descendants

    tree
        recursive descendants

Broader scope requires broader authority.


## 23.4 Symlinks and escapes

Mechanical path resolution must prevent path traversal and symlink escape from
turning an apparently safe path into an external resource.

Guard classification then decides whether the resolved resource is authorized.


===============================================================================
24. CURRENT PRODUCTION SECURITY POSTURE
===============================================================================

The current security posture intentionally enables less than the eventual
product will require.


## 24.1 Enabled categories

Current production policy supports explicitly authorized operations such as:

- ordinary workspace reads;
- selected workspace writes;
- selected workspace creation;
- selected component reads;
- protected read visibility where explicitly allowed;
- network/service operations where granted;
- semantic Memory Service access.


## 24.2 Intentionally blocked categories

Current architecture intentionally blocks or restricts:

- process execution;
- ordinary direct memory filesystem access;
- kernel mutation;
- Constitution mutation;
- external filesystem access;
- unknown future capabilities without policy;
- guardless tool execution.


## 24.3 Security expansion rule

A blocked capability is not enabled merely because a feature needs it.

Before enabling it we define:

1. capability;
2. effect model;
3. resource boundaries;
4. permitted principals;
5. permitted component chains;
6. scopes;
7. failure behavior;
8. tests;
9. audit requirements.

Only then is production policy expanded.


===============================================================================
25. CURRENT LEARNING POSTURE
===============================================================================

The system currently has the foundation for controlled learning, not unlimited
self-modification.


## 25.1 What the architecture supports

The architecture supports:

- knowledge proposals;
- persistent pending proposals;
- domain evaluation;
- tested/raw/rejected outcomes;
- Memory Service commitment;
- provenance;
- guarded Intake.


## 25.2 What remains future work

Future work includes richer:

- belief scoring;
- evidence weighting;
- contradiction handling;
- operational validation;
- behavior learning;
- supersession;
- retirement;
- trainer review UI;
- autonomous proposal generation;
- evolution scheduling.


===============================================================================
26. EVOLUTION LOOP
===============================================================================

The long-term system should improve from observed evidence.

The evolution loop must remain governed.


## 26.1 Observer

Detects opportunities/problems.


## 26.2 Proposer

Creates explicit proposed changes.


## 26.3 Evidence evaluation

Determines whether the proposal is supported and testable.


## 26.4 Authority evaluation

Determines who, if anyone, may authorize the proposed effect.


## 26.5 Application

Uses the owning guarded service/tool.

Central Mind does not bypass the service boundary.


## 26.6 Verification

Confirms whether the applied change actually improved the intended behavior.


## 26.7 Learning from outcome

Success and failure both become evidence.

Autonomous evolution must never mean autonomous privilege escalation.


===============================================================================
27. SELF-CREATED CAPABILITIES
===============================================================================

AI Friend may eventually create new capabilities.

This is one of the system's major goals.

It is also one of its highest-risk features.


## 27.1 What self-creation may do

A capable system may propose or construct:

- a new domain;
- a new tool;
- a new model wrapper;
- a new renderer;
- a new behavior;
- a new test;
- a new capability implementation.


## 27.2 What self-creation may not do

Self-created code cannot:

- grant itself a human role;
- alter trusted authentication;
- bypass Guard;
- silently change Constitution;
- grant itself new capabilities;
- redefine protected resource classification;
- write directly to Memory Service storage;
- declare itself verified merely because it generated itself.


## 27.3 Plug, not socket

Self-created capabilities may create new plugs.

They must not silently rewrite the trusted sockets or authority system that
decides whether plugs may execute.


===============================================================================
28. SECTION RESPONSIBILITIES
===============================================================================

The numbered sections are architectural ownership boundaries.

## section_0_app

Desktop application shell and UI.


## section_1_central_mind

Coordination kernel and trusted runtime infrastructure, including:

- Central Mind;
- authentication integration;
- Broker;
- Inventory;
- routing;
- questioning;
- composition;
- verification orchestration;
- learning orchestration;
- Guard infrastructure;
- server/runtime coordination.


## section_2_constitution

Canonical governing documentation and domain constitutions.


## section_3_memory

Memory Service, persistent memory schema/storage, proposal lifecycle,
provenance and memory APIs.


## section_4_chatbox

Chatbox-facing package boundary.

This section may evolve as chat responsibilities are separated from Central
Mind runtime code.


## section_5_domains

Domain organs and their domain-specific intelligence.


## section_6_capabilities

Capability-related infrastructure that is genuinely independent of specific
domains/tools.

This section must not become a second Guard or second Inventory.


## section_7_models

Model organs, provider abstraction and model registry.


## section_8_tools

Action-performing tool organs and shared neutral tool infrastructure.


## section_9_data

Reserved/data-oriented architecture where appropriate.


## section_10_workspace

Ordinary working area and reusable workspace artifacts/scaffolds.

Scaffolds are templates, not parallel runtime implementations.


===============================================================================
29. CURRENT COMPONENT MAP
===============================================================================

Current discoverable domain direction:

- coding
- general
- languages
- trading
- image
- video

Current model direction:

- chat
- coder
- translator
- provider abstraction

Current tool direction:

- filesystem
- folders
- intake
- scaffold
- terminal
- vision
- web

These lists describe the current system.

They are not closed architectural enumerations.


===============================================================================
30. LEGACY CODE AND MIGRATION RULE
===============================================================================

The project has evolved through multiple architectures.

Old code must not silently remain active after replacement.


## 30.1 Canonical replacement rule

When replacement code:

1. implements the intended contract;
2. has appropriate focused tests;
3. passes integration testing;

the superseded runtime implementation should be removed.


## 30.2 Backup files

Files such as:

    *.bak
    *.before_*
    *.pre_*

are not runtime architecture.

They should not participate in discovery, imports or execution.

Long-term historical backups should live outside active component directories
or be removed once no longer needed.


## 30.3 No permanent migration compatibility without reason

Temporary compatibility may exist during a migration.

Once migration is complete and validated, compatibility paths should be
removed unless a concrete supported compatibility requirement remains.


===============================================================================
31. TESTING PHILOSOPHY
===============================================================================

Tests protect architectural contracts, not implementation accidents.


## 31.1 Security tests

Security tests should prove both:

- permitted work succeeds;
- forbidden work does not execute.


## 31.2 Integration tests

Critical security paths should use real production-equivalent components where
practical.

Mock-only tests are insufficient for proving the final execution chain.


## 31.3 Fail-before-execution tests

For denied actions, tests should verify the underlying tool/action was never
called.


## 31.4 Test isolation

Temporary component packages and Python module caches must not contaminate
later tests.

Tests must restore process-global state they modify.


## 31.5 Full suite

Focused tests validate individual changes.

The full suite validates an integration milestone.

Repeated full-suite execution without a meaningful change is unnecessary.


===============================================================================
32. DEVELOPMENT RULES
===============================================================================

These rules guide continued construction of AI Friend V1.


## 32.1 Inspect before changing

Do not guess the current implementation.

Inspect actual code and contracts first.


## 32.2 One canonical path

Before adding a new manager, registry, policy, writer or service, determine
whether an authoritative one already exists.


## 32.3 No hard-coded future

Do not encode today's finite list of domains, tools, models or capabilities as
a permanent kernel enum unless the concept truly is closed by architecture.


## 32.4 Separate mechanism from policy

Examples:

Path resolution is mechanism.

Permission to write that path is policy.

Effect classification is mechanism.

Permission for that effect is policy.

Password hashing is mechanism.

Which role may create an account is policy.


## 32.5 Separate identity, capability and effect

These are different questions:

    Who is requesting?
    What capability is required?
    What will actually be affected?

All three matter.


## 32.6 Preserve evidence

Do not erase information merely because newer information exists.

Prefer explicit supersession/history.


## 32.7 Ask when information is required

Missing information is not permission to invent.


## 32.8 Verify meaningful work

Where an objective test exists, use it.


## 32.9 Do not weaken architecture to make a test pass

If a test fails because the test fixture is wrong, repair the fixture.

Do not weaken production security semantics merely to satisfy the test.


===============================================================================
33. CURRENT VALIDATED FOUNDATION
===============================================================================

As of this design update, the validated foundation includes:

- backend authentication;
- Administrator / Trainer / User role enforcement;
- privileged-account uniqueness;
- session validation and revocation;
- trusted principal propagation;
- authoritative Inventory identity;
- bound Broker execution;
- operation ownership isolation;
- capability requirements from manifests;
- deterministic tool-effect contracts;
- semantic resource classification;
- boundary-aware effect classification;
- production capability policy;
- production effect policy;
- pre-execution Guard enforcement;
- fail-closed guardless execution;
- kernel/Constitution/memory filesystem protection;
- Memory Service boundary;
- persistent knowledge proposals;
- controlled Intake;
- domain learning evaluation;
- tested/raw/rejected learning outcomes;
- post-response verification;
- real guarded filesystem integration tests;
- neutral path containment helpers;
- removal of obsolete duplicate tool authorization;
- authenticated server integration.

The current full automated suite validates this milestone with:

    375 tests passed
    FULL-SUITE EXIT=0

This number is historical evidence for this milestone, not a permanent design
constant.


===============================================================================
34. NEXT ARCHITECTURAL PRIORITIES
===============================================================================

With the authority/security foundation established, development should proceed
upward into intelligence and product behavior rather than repeatedly
redesigning the security substrate.

Priority areas are:

1. reasoning architecture;
2. planning architecture;
3. questioning behavior;
4. capability-based model selection;
5. complete Coding domain workflow;
6. richer evidence and belief scoring;
7. trainer review workflow;
8. richer Memory lifecycle;
9. governed behavior learning;
10. evolution loop;
11. Chatbox conversational intelligence;
12. desktop application integration;
13. constrained process execution;
14. distributed worker architecture;
15. Trading/Image/Video expansion.


===============================================================================
35. DESIGN DECISION REGISTER
===============================================================================

Important decisions must be preserved so discarded designs are not repeatedly
reintroduced.


## D001 — Central Mind remains generic

Decision:
Central Mind coordinates discoverable components.

Reason:
Hard-coding every new component would make capability growth require kernel
rewrites.


## D002 — Inventory is authoritative component identity

Decision:
Trusted discovery roots establish component identity/kind.

Reason:
A component-controlled manifest must not be able to redefine its security
identity.


## D003 — Broker uses bound execution views

Decision:
Execution is performed through a Broker view bound to the trusted requester
chain.

Reason:
Models and components must not fabricate execution provenance.


## D004 — No raw master Broker execution API

Decision:
The master Broker coordinates security state but is not an unrestricted
runtime execution interface.

Reason:
A raw execution path would bypass the provenance model.


## D005 — Guard and Verifier are separate

Decision:
Guard authorizes before action. Verifier checks correctness after work.

Reason:
Permission and correctness are independent properties.


## D006 — Authorization is effect-based

Decision:
Guard reasons about declared/classified effects rather than maintaining a list
of trusted tool names.

Reason:
Future tools must inherit the same security model automatically.


## D007 — Memory Service is the only memory mutation authority

Decision:
Persistent memory changes occur through Memory Service.

Reason:
Direct storage access would bypass validation, provenance, lifecycle and
authorization.


## D008 — Intake creates proposals, not truth

Decision:
Intake submission enters the learning lifecycle as a proposal.

Reason:
The source of information cannot also be the final judge of its validity.


## D009 — Models are workers, not authorities

Decision:
Models provide reasoning/generation but no security authority.

Reason:
Model output is probabilistic and potentially adversarial/untrusted.


## D010 — Unknown future capabilities default deny

Decision:
Capabilities remain extensible but ungranted until trusted policy explicitly
allows them.

Reason:
Extensibility must not become privilege escalation.


## D011 — Process execution remains disabled until separately designed

Decision:
Terminal existence does not enable process.execute.

Reason:
Arbitrary process execution has substantially broader effects than ordinary
workspace operations.


## D012 — Duplicate authorization paths are removed

Decision:
Once Guard became canonical, obsolete per-tool authorization policy was
removed while neutral path mechanics were retained.

Reason:
Two security authorities inevitably drift and create bypasses.


## D013 — Learning and memory are different

Decision:
Memory records information; learning requires validated information to affect
future system behavior.

Reason:
Storage alone does not create intelligence.


## D014 — Self-created capabilities may create plugs, not authority

Decision:
Future self-development can create components that fit trusted contracts but
cannot rewrite its own security authority.

Reason:
Self-improvement must not equal self-privileging.


## D015 — Human authority is backend authenticated

Decision:
Administrator/Trainer/User identity originates from AuthService.

Reason:
Client fields, models and internal components are not trusted identity
providers.


## D016 — No fabricated local Administrator for CLI

Decision:
A guardless CLI does not receive fake privileged identity for convenience.

Reason:
Development convenience must not redefine the authority model.


## D017 — Test failures do not justify security weakening

Decision:
When integration tests expose fixture contamination or test-environment
problems, repair the test environment rather than changing correct production
security semantics.

Reason:
Tests validate architecture; they do not define permission by accident.


===============================================================================
36. GLOSSARY
===============================================================================

AI Friend
    The complete governed AI system.

Central Mind
    The generic coordination kernel.

Organ
    A discoverable component implementing a system contract.

Domain
    An organ owning domain-specific intelligence and verification.

Tool
    An organ that performs a focused external or state-changing action.

Model
    A replaceable reasoning/generation worker.

Provider
    Backend through which a model is executed.

Inventory
    Authoritative discovered component registry.

Manifest
    Component metadata and declared contracts. It does not itself grant
    authority.

Principal
    Trusted authenticated authority identity.

Component chain
    Trusted provenance of internal components participating in execution.

Capability
    Named permission requirement for an operation.

Effect
    Deterministic description of what an operation intends to affect.

Resource
    Semantically classified target of an effect.

Boundary
    Protected semantic resource crossed by a broader filesystem scope.

Guard
    Pre-execution authorization system.

Verifier
    Post-work correctness system.

Broker
    Controlled gateway for tool discovery and execution.

Bound Broker
    Restricted Broker view carrying trusted requester provenance.

Memory Service
    Sole governed interface to persistent learned AI memory.

Memory Client
    Restricted interface provided to a component for Memory Service access.

Proposal
    Requested knowledge or system change awaiting governed evaluation.

Intake
    Controlled entrance for deliberate knowledge/source submission.

Evidence
    Information supporting or contradicting a claim or result.

Belief
    Claim with confidence and evidence rather than immutable truth.

Provenance
    Record of origin, actors, evidence, operations and decisions.

Raw knowledge
    Retained knowledge not falsely claimed to have passed operational testing.

Tested knowledge
    Knowledge that passed the applicable evaluator/test.

Composition
    Structured tree of concepts used to construct an artifact or result.

Renderer
    Component/function translating a structured concept into concrete output.

Protected Core
    Authentication, authorization, Guard, Constitution and other architecture
    that ordinary operations cannot rewrite.

Fail closed
    Deny when required trusted security information is absent or invalid.

Plug
    Extensible component implementation.

Socket
    Stable trusted contract into which components connect.

===============================================================================
CENTRAL MIND COGNITIVE ARCHITECTURE
===============================================================================

## CM.1 Foundational principle: Central Mind owns intelligence

Central Mind is not an LLM router.

Central Mind is the system-level owner of:

- understanding;
- reasoning;
- planning;
- questioning;
- decision formation;
- self-appraisal;
- learning coordination;
- capability-gap detection;
- capability expansion;
- communication intent;
- orchestration of subordinate intelligence providers.

External and local LLMs are not the Central Mind.

They are subordinate providers available to the Central Mind.

An LLM may:

- generate a candidate explanation;
- propose a plan;
- analyze a problem;
- translate language;
- inspect code;
- suggest hypotheses;
- summarize information;
- provide specialist reasoning;
- propose alternatives.

An LLM may not become the authority that determines:

- what Central Mind is;
- what Central Mind is allowed to do;
- whether Central Mind may modify protected architecture;
- whether a learned belief becomes trusted;
- whether a capability receives authority;
- whether verification may be bypassed;
- whether human authority may be overridden.

The intended long-term direction is:

    Central Mind intelligence
        grows from
    governed experience + verified knowledge + learned relationships
        while
    dependence on external LLM reasoning decreases where justified by evidence.

LLMs bootstrap intelligence.

They do not permanently define it.


## CM.2 Concepts must be separable from language

Knowledge should, where practical, be represented independently from the
language used to communicate it.

For example, the concept of Python inheritance is not inherently English,
Urdu, Arabic, or any other natural language.

Central Mind should be able to reason about the underlying concept and then
request an appropriate communication capability to render that concept for:

- a programmer;
- a beginner;
- a child or layperson where appropriate;
- an English speaker;
- an Urdu speaker;
- another supported audience or language.

Therefore:

    concept / meaning
        is not the same thing as
    linguistic representation.

Language models and language domains may help interpret and render concepts,
but they do not own the concepts themselves.

This distinction is a long-term architectural requirement even when V1 must
temporarily use LLM-generated text as part of the representation process.


## CM.3 Permanent cognitive sockets

Central Mind V1 establishes four permanent cognitive sockets:

1. Reasoner
2. Learner
3. Self-Appraiser
4. Capability Expansion

These are architectural contracts.

Their internal intelligence may improve substantially over time without
requiring redesign of Central Mind's fundamental control structure.

The existence of a socket does not require its V1 implementation to be
sophisticated.

V1 establishes ownership, boundaries, inputs, outputs, evidence requirements,
authority constraints, and integration points.

Later versions improve the implementation behind those contracts.


-------------------------------------------------------------------------------
CM.3.1 Reasoner
-------------------------------------------------------------------------------

The Reasoner is Central Mind's problem-solving facility.

Central Mind owns the reasoning process.

A reasoning LLM is a provider to the Reasoner, not the Reasoner itself.

The Reasoner must be able to work toward questions such as:

- What is being requested?
- What is the actual objective?
- What is already known?
- What evidence is available?
- What is uncertain?
- What information is missing?
- Should a question be asked?
- Can the objective be decomposed?
- Which capabilities may help?
- Which domain should participate?
- Which tool may be appropriate?
- Which model or external provider may be useful?
- What constraints apply?
- What should happen first?
- What result would count as success?
- Did the previous step make progress?
- Should the plan continue, change, stop, or escalate?

The Reasoner must support bounded deliberation.

It must not perform blind or infinite loops.

A reasoning cycle must have:

- an objective;
- state;
- evidence;
- known constraints;
- unresolved questions;
- candidate actions;
- progress information;
- a bounded budget;
- stop conditions;
- escalation conditions;
- a final structured decision or status.

The Reasoner may consult:

- Memory;
- Inventory;
- domains;
- models;
- LLM reasoners;
- tools through authorized execution paths;
- previous verified experience;
- current observations.

But consultation does not transfer ownership of the reasoning process.

V1 may rely heavily on Qwen, DeepSeek, or other reasoner models.

Later versions should increasingly reuse verified internal experience,
strategies, concepts and relationships when they are sufficient.


-------------------------------------------------------------------------------
CM.3.2 Learner
-------------------------------------------------------------------------------

The Learner turns experience into reusable learning.

Memory persistence alone is not learning.

Storing a transcript, model output, tool result or file does not by itself
mean that Central Mind learned from it.

The learning process is conceptually:

    experience
        ->
    observation
        ->
    evidence
        ->
    evaluation
        ->
    candidate lesson / relationship / strategy
        ->
    verification where applicable
        ->
    governed Memory Service proposal
        ->
    reusable knowledge.

The Learner should eventually learn from:

- successful solutions;
- failed solutions;
- verifier results;
- test results;
- tool outcomes;
- corrections;
- Trainer instruction;
- repeated patterns;
- source reliability;
- model performance;
- domain performance;
- strategy performance;
- environmental context;
- superseded beliefs;
- contradictions;
- capability gaps.

Learned information should preserve, where applicable:

- provenance;
- evidence;
- circumstances;
- confidence;
- verification state;
- timestamps;
- relationships;
- previous versions;
- failure history;
- success history;
- applicability conditions.

The Learner never writes around the Memory Service.

The Memory Service remains the sole persistence authority for governed memory.

The Learner may propose learning.

It does not grant itself authority to make arbitrary information trusted.


-------------------------------------------------------------------------------
CM.3.3 Self-Appraiser
-------------------------------------------------------------------------------

The Self-Appraiser allows Central Mind to evaluate its own performance and
capability using observable evidence.

The Self-Appraiser belongs to Central Mind.

No LLM is the authority that appraises Central Mind.

An LLM may provide a critique or suggestion as one evidence source.

Such a suggestion remains a provider result until Central Mind evaluates it.

Self-appraisal should compare, where applicable:

    objective
        ->
    chosen strategy
        ->
    expected outcome
        ->
    performed actions
        ->
    actual outcome
        ->
    verification result
        ->
    previous comparable experience
        ->
    appraisal.

The Self-Appraiser should be able to identify:

- successful completion;
- partial completion;
- failure;
- repeated failure;
- missing information;
- missing capability;
- unsuitable capability;
- poor strategy;
- poor provider selection;
- inadequate knowledge;
- stale knowledge;
- contradictory evidence;
- low confidence;
- verification weakness;
- unnecessary work;
- lack of progress;
- possible architectural deficiency.

Self-appraisal must be evidence-backed.

Central Mind must not manufacture deficiencies or improvements merely because
an LLM suggested them.

The output of Self-Appraisal may feed:

- learning;
- replanning;
- questioning;
- provider selection;
- capability-gap detection;
- human escalation;
- future improvement proposals.


-------------------------------------------------------------------------------
CM.3.4 Capability Expansion
-------------------------------------------------------------------------------

Capability Expansion converts a demonstrated capability gap into a governed
proposal for new or improved capability.

Central Mind may identify what it needs.

That does not mean Central Mind automatically receives permission to create,
install, execute or authorize it.

The conceptual flow is:

    objective
        ->
    capability required
        ->
    Inventory search
        ->
    existing capability evaluation
        ->
    proven gap
        ->
    capability requirement
        ->
    architecture proposal
        ->
    authorized implementation path
        ->
    tests
        ->
    verification
        ->
    Inventory discovery
        ->
    governed activation
        ->
    experience and learning.

Capability Expansion may eventually propose:

- a new domain;
- a new tool;
- a new model adapter;
- a new provider;
- a new renderer;
- a new source;
- a new capability inside an existing organ;
- an improvement to an existing component.

A newly created component receives no automatic authority.

Discovery is not authorization.

Creation is not authorization.

Successful testing is not authorization.

Authority continues to come from trusted human policy and the Guard system.

Once the Coding capability is mature, Coding may become the primary
implementation arm for approved capability-expansion work.


## CM.4 Cognitive operating cycle

The intended high-level cognitive cycle is:

    RECEIVE OBJECTIVE
          |
          v
      UNDERSTAND
          |
          v
        RECALL
          |
          v
        REASON
          |
          +------ missing information ------> QUESTION
          |                                      |
          |<-------------------------------------+
          v
         PLAN
          |
          v
    SELECT CAPABILITIES
          |
          v
         ACT
          |
          v
       VERIFY
          |
          v
       APPRAISE
          |
          +------ incomplete / failed ------> REASON / REPLAN
          |
          +------ capability gap -----------> CAPABILITY EXPANSION PROPOSAL
          |
          v
        LEARN
          |
          v
     COMMUNICATE

Not every request requires every stage.

Simple requests should remain simple.

Central Mind must not perform expensive reasoning merely because the Reasoner
exists.

The cycle is therefore adaptive rather than mandatory in full for every input.


## CM.5 Communication belongs to Central Mind

Central Mind owns communication intent.

It determines, where possible:

- what needs to be communicated;
- to whom;
- why;
- at what technical level;
- with what degree of detail;
- in what structure;
- with what uncertainty;
- using which language capability.

Language organs and LLMs may perform linguistic realization.

They are subordinate to the communication objective.

Chat may render the response draft through its language-model capability.
Central Mind reviews that draft against the task and verified evidence and
withholds it from the UI unless the review approves it.

This allows the same underlying concept to be expressed differently without
requiring separate conceptual knowledge for every language or audience.


## CM.6 Models are cognitive providers, not the cognitive authority

The model registry describes available providers.

A provider may have capabilities such as:

- reason;
- plan;
- code;
- translate;
- summarize;
- inspect;
- classify;
- generate;
- embed;
- perceive.

Central Mind should request capabilities.

It should not structurally depend on a particular model name.

For example:

    Reasoner requests capability: reason

ModelRouter may currently choose:

    qwen3_30b

or:

    deepseek-r1_14b

or a future model.

Later, the Reasoner may determine that verified internal knowledge and
experience are sufficient and require no LLM consultation at all.

Therefore:

    capability != provider
    Reasoner != reasoning LLM
    Central Mind != model
    knowledge != model output


## CM.7 Experience-driven independence

AI Friend is intended to become progressively less dependent on external
general-purpose LLM intelligence where its own verified experience is
sufficient.

This does not require eliminating LLMs.

The goal is selective dependence rather than permanent dependence.

A mature Central Mind may still consult an LLM because:

- the problem is novel;
- external perspective is useful;
- language generation is needed;
- specialist knowledge is missing;
- comparison improves confidence;
- the task benefits from a powerful external provider.

But repeated solved problems should not require complete rediscovery forever.

Verified experience should become reusable system intelligence.


## CM.8 Versioned cognitive development

The cognitive architecture evolves by version.

### V1 — Bootstrap Mind

V1 establishes all four cognitive sockets.

It may rely heavily on LLMs.

It must already:

- own the cognitive control cycle;
- preserve evidence;
- ask when important information is missing;
- use Memory through the Memory Service;
- use Inventory to discover capabilities;
- use models as subordinate providers;
- use tools only through Broker + Guard;
- verify important work;
- appraise outcomes;
- propose learning;
- identify basic capability gaps;
- produce governed capability proposals;
- stop bounded reasoning when progress is exhausted.

V1 does not need human-level autonomous reasoning.

Correct architecture is more important than sophistication.


### V2 — Experience-Aware Mind

V2 should improve reasoning using accumulated experience.

Possible improvements include:

- strategy retrieval;
- concept relationships;
- previous-solution retrieval;
- failure avoidance;
- context-sensitive provider selection;
- stronger confidence calibration;
- richer self-appraisal;
- reusable planning patterns;
- improved learning consolidation.

V2 should be implemented behind the existing cognitive contracts whenever
possible.


### V3 — Learned Reasoning Mind

V3 may introduce substantially stronger internally learned reasoning.

Possible directions include:

- learned strategy selection;
- richer concept graphs;
- causal relationships;
- outcome prediction;
- internally trained classifiers;
- learned planning heuristics;
- learned capability selection;
- experience-derived reasoning policies;
- specialized local models trained from governed experience.

These are future implementation choices.

They must not require external providers to become architectural authorities.


### V4 and later

Future cognitive systems may become considerably more sophisticated.

They may replace major V1 implementations.

They must continue to respect:

- Constitution;
- human authority;
- Guard;
- Memory Service ownership;
- provenance;
- verification;
- audit;
- protected-core boundaries.


## CM.8A Evidence, Outcome and Scoring Contract

Evidence is a first-class input to future intelligence.

AI Friend must not learn merely from generated answers, subjective model
confidence, or a single accumulated numerical score.

The canonical progression is:

    EVENT
      ->
    EVIDENCE RECORD
      ->
    OUTCOME ASSESSMENT
      ->
    SELF-APPRAISAL
      ->
    LEARNING CANDIDATE
      ->
    GOVERNED MEMORY

These stages are related but are not interchangeable.


### CM.8A.1 Evidence is not a conclusion

Evidence records what was observed.

Examples include:

- a test process returned exit code 0;
- a verifier accepted or rejected an output;
- a file was successfully written;
- a tool failed with a timeout;
- a model produced a particular candidate;
- a user corrected an answer;
- a retrieved memory was used;
- a requested capability was unavailable;
- an artifact was created;
- an expected file was missing;
- a strategy required three attempts;
- an external source contradicted an existing belief.

Evidence should preserve the original observable fact as faithfully as
practical.

Later components may interpret evidence.

They must not rewrite the historical observation merely because their
interpretation changes.


### CM.8A.2 Outcome is not the same thing as evidence

An outcome assessment answers questions such as:

- Did the objective succeed?
- Did it fail?
- Was it partially successful?
- Is the outcome still unknown?
- Was verification sufficient?
- What was actually produced?
- What expected result did not occur?

For example:

    Evidence:
        Python syntax process returned exit code 0.

    Outcome:
        Syntax validity was established.

This does not automatically mean:

        The program is functionally correct.

The system must preserve this distinction.


### CM.8A.3 Appraisal is interpretation

Self-Appraisal consumes evidence and outcomes.

It may conclude:

- the selected strategy worked;
- the selected strategy failed;
- the provider was unsuitable;
- more evidence is required;
- verification was too weak;
- a previous belief may be stale;
- a capability appears missing;
- the system repeated a known failure;
- a successful pattern may deserve reuse.

An appraisal is a derived interpretation.

It must retain links to the evidence from which it was derived.


### CM.8A.4 Learning is a governed consequence

A learning candidate is produced only after evidence and appraisal justify
something potentially reusable.

Examples:

- this strategy works under these circumstances;
- this approach repeatedly fails under these circumstances;
- this provider performs well for this capability;
- this concept is related to another concept;
- this correction supersedes an earlier belief;
- this capability is genuinely missing.

A learning candidate still does not directly become trusted memory.

It enters the governed Memory Service lifecycle.


### CM.8A.5 Scorer V1 responsibility

Scorer V1 is Central Mind's bounded temporary operational evidence recorder.

It is not a second permanent memory system.

It is not a permanent evidence ledger.

It does not own learned knowledge.

It does not grant truth, authority or memory status merely because an event was
recorded.

Scorer V1 keeps a bounded in-memory working history of compact structured
runtime experience so the current cognitive cycle can inspect recent evidence.

It may accept structured records containing, where applicable:

- event identity;
- timestamp;
- turn/request identity;
- objective;
- originating component;
- domain;
- capability;
- provider/model;
- selected strategy or action;
- relevant context;
- expected outcome;
- actual outcome;
- verification result;
- success/failure/partial/unknown state;
- confidence when meaningful;
- failure classification;
- artifacts;
- duration;
- resource/cost information when available;
- memory references used;
- source/provenance information;
- supporting evidence.

Not every event must contain every field.

Missing information must remain missing rather than being fabricated.

The canonical V1 flow is:

    ACTION / RESULT
        ->
    VERIFICATION
        ->
    BOUNDED TEMPORARY EVIDENCE
        ->
    SELF-APPRAISER
        ->
    +---------------------------+
    |                           |
    v                           v
NO REUSABLE VALUE         REUSABLE INSIGHT
    |                           |
discard / expire              LEARNER
                                |
                                v
                         MEMORY PROPOSAL
                                |
                                v
                         MEMORY SERVICE
                                |
                                v
                   TESTED / DERIVED AS GOVERNED

Section 3 Memory remains the sole permanent reusable knowledge and experience
authority.

Reusable system-generated learning is proposed as Derived knowledge unless a
separate governed lifecycle establishes another permitted class.

Raw Memory is not a downgrade target for uncertain system knowledge.

Raw Memory is reserved for authenticated Trainer Intake.


### CM.8A.6 Evidence preservation

Temporary operational evidence and permanent reusable memory are different
storage responsibilities.

Scorer's bounded operational evidence may expire when it no longer has current
cognitive value.

Evidence must not be retained permanently merely because it existed.

When evidence supports reusable learning, the Learner should preserve only the
material required to justify, test, retest, interpret or trace that learning.

Permanent retention should therefore favor compact intelligence value over raw
execution volume.

Where a learned memory entry requires supporting provenance, the Memory Service
may retain compact evidence, references, source information, parent Memory IDs,
verification information or other material necessary for future review.

Large transient payloads, duplicated prompts, complete model conversations,
routine execution traces and other disposable working material must not be
copied into permanent Memory merely for completeness.

If a separate bounded audit/debug record is retained elsewhere for operational
or security purposes, it remains distinct from permanent knowledge Memory.

Historical observations that are retained must not be silently rewritten to
make a later interpretation appear historically true.

Self-Appraiser and Learner may reinterpret retained evidence.

They may not mutate provenance to manufacture support for a conclusion.


### CM.8A.7 Scoring dimensions

AI Friend must not collapse all intelligence quality into one universal
number.

Different scores may represent different concepts, including:

- memory-entry reliability;
- verification strength;
- strategy success rate;
- provider performance;
- confidence;
- retrieval usefulness;
- capability effectiveness;
- repeated failure frequency.

These dimensions must remain semantically distinct.

A numerical value without a defined meaning, source and scale must not be
treated as authoritative intelligence.


### CM.8A.8 Existing Memory scores

Memory's existing success/failure counts, failure records, computed score and
derived state remain Memory-level reliability information.

They do not become the universal Central Mind score.

For example:

    memory reliability score

is not automatically equivalent to:

    reasoning confidence
    provider quality
    task success probability
    verification strength.

Central Mind may use these signals together, but it must preserve their
meaning.


### CM.8A.9 Scorer and organs

An organ may contribute domain-specific evidence.

It does not own the canonical Central Mind evidence interpretation.

Scorer may accept evidence from:

- domains;
- models;
- tools;
- Broker;
- Verifier;
- Reasoner;
- Questioner;
- Memory;
- Self-Appraiser;
- other trusted system components.

Component-provided evidence must retain its provenance.

Central Mind may subsequently appraise that evidence independently.


### CM.8A.10 Failures are valuable experience

Failure evidence must not be discarded merely because an operation failed.

Useful failure information includes:

- attempted strategy;
- circumstances;
- failure type;
- verifier result;
- provider/tool involved;
- relevant context;
- whether the failure had occurred before;
- whether retry changed anything;
- eventual successful alternative.

Repeated failures are particularly valuable inputs to:

- Reasoner;
- Self-Appraiser;
- Learner;
- Capability Expansion.

The goal is not merely to remember that something failed.

The goal is eventually to understand when and why it fails and avoid repeating
the same ineffective strategy.


### CM.8A.11 Success also requires context

A successful action must not automatically become a universal rule.

The system should preserve enough context to determine:

- what succeeded;
- under which conditions;
- using which strategy;
- using which capability/provider;
- what verification established;
- what verification did not establish.

This allows later learning to distinguish reusable patterns from accidental or
context-specific success.


### CM.8A.12 Relationship to the Reasoner

The Reasoner may consume prior evidence and appraisal when deciding what to do.

It should eventually be able to prefer strategies supported by relevant
historical outcomes and avoid strategies associated with repeated comparable
failures.

V1 may perform this only minimally.

The contract must nevertheless support richer experience-driven reasoning in
later versions.


### CM.8A.13 Relationship to the Learner

The Learner consumes evidence and appraisal to construct learning candidates.

The Learner must not infer that an event is reusable knowledge merely because
Scorer recorded it.

Scorer records.

Self-Appraiser interprets.

Learner proposes reusable knowledge.

Memory Service governs persistence.


### CM.8A.14 Relationship to Capability Expansion

Capability Expansion may use evidence of:

- repeated unhandled objectives;
- repeated tool insufficiency;
- repeated provider insufficiency;
- missing Inventory capabilities;
- verification failures caused by absent functionality;
- repeated manual work that should become a capability.

A capability proposal should therefore cite concrete evidence rather than
merely state that Central Mind "feels" a new capability would be useful.


### CM.8A.15 Long-term importance

The evidence contract is part of AI Friend's path away from permanent
dependence on general-purpose LLMs.

LLMs can provide candidate intelligence.

Experience provides system-specific evidence.

Over time, verified evidence, outcomes, appraisals and learned relationships
become the material from which AI Friend develops its own reusable reasoning
and behavior.

For this reason, evidence quality and provenance are architectural concerns,
not logging conveniences.


## CM.8B Central Mind V1 implementation status

Central Mind V1 reached its implementation regression closure gate on
2026-10-16.

The validated V1 implementation includes:

- Reasoner V1 in the real `CentralMind.process()` request path;
- Self-Appraiser V1 after verification;
- Learner V1 for explicit reusable learning candidates;
- Capability Expansion V1 for demonstrated capability-gap proposals;
- bounded temporary Scorer evidence rather than a permanent evidence ledger;
- Section 3 Memory as the sole permanent reusable knowledge/experience system;
- authenticated Trainer Intake as the sole permitted origin of Raw Memory;
- Trainer context stored with Raw Intake and Central Mind prioritizing relevant
  Raw Memory for recall and passing it to assigned domains as unverified evidence;
- explicit denial of Central Mind proposal approval creating Raw Memory;
- rejection of untestable system proposals rather than downgrading them to Raw;
- Tested and Derived governed system-learning paths;
- shared availability of installed generative model providers;
- registry assignments used as bootstrap ranking and compatibility guidance,
  not permanent model ownership;
- learned contextual provider evidence as a candidate-routing signal;
- embedding models excluded from the generative candidate pool;
- Inventory retained as component-discovery authority;
- Guard retained as pre-action authorization;
- Verifier retained as post-action correctness/evidence evaluation;
- legacy Observer/Proposer/Reviewer/Applicator evolution execution removed.

The complete regression gate executed 383 tests with:

- 383 passed;
- 0 failures;
- 0 errors;
- 0 skipped.

This closes the Central Mind V1 implementation regression gate.

It does not freeze intelligence quality.

Future Reasoner, Learner, Self-Appraiser, provider-selection and capability
expansion improvements should be implemented as versioned upgrades behind the
stable V1 contracts whenever possible.

Structural changes to the finalized Central Mind layers require an essential
architectural reason and must be explicitly recorded with rationale and impact.


## CM.9 Central Mind closure principle

"Central Mind closed" does not mean:

- intelligence is finished;
- reasoning can never improve;
- learning can never improve;
- new cognitive algorithms cannot be introduced.

It means:

- the kernel ownership model is stable;
- the cognitive sockets are stable;
- component contracts are stable enough for downstream development;
- future improvements can normally occur behind those contracts;
- domains/tools/models do not require redesign of Central Mind;
- Coding, Chat, UI, Trading and other capabilities can now be developed
  against a stable brain architecture.

This distinction allows AI Friend to become useful while its intelligence
continues to evolve.


## CM.10 Central Mind V1 closure gate

Central Mind V1 may be declared CLOSED only when all of the following are true:

1. Central Mind remains the system coordinator and cognitive owner.

2. A Reasoner contract exists and participates in the real request path.

3. Reasoning is bounded by explicit budgets, progress checks and stop
   conditions.

4. The Reasoner can consult subordinate model providers without transferring
   cognitive authority to them.

5. A Learner contract exists and can convert verified experience into governed
   learning proposals.

6. All persistent learned information still passes through Memory Service.

7. A Self-Appraiser contract exists and can evaluate at least objective,
   outcome and verification evidence.

8. A Capability Expansion contract exists and can represent a demonstrated
   capability gap as a structured proposal.

9. Capability Expansion cannot grant itself authority.

10. Inventory remains the authoritative discovery mechanism.

11. Tool execution remains Broker + Guard controlled.

12. Verification remains separate from authorization.

13. Questioning is available when required information is missing.

14. Communication intent remains owned by Central Mind even when a language
    model performs final linguistic rendering.

15. Existing obsolete Central Mind evolution paths are either migrated into
    the canonical cognitive architecture or removed.

16. No duplicate reasoning/learning/evolution authority remains active.

17. The real authenticated server path can construct and use the closed
    Central Mind.

18. Focused cognitive tests pass.

19. The final project test suite passes.

20. design_actual.md is regenerated from the final implementation.

Once these conditions are satisfied, Section 1 Central Mind V1 is frozen as
the stable kernel architecture.

Further intelligence work becomes versioned cognitive development rather than
ad-hoc redesign of the kernel.


## CM.11 Post-closure development sequence

After Central Mind V1 closes, development priority is:

    1. Coding capability/domain
    2. Chat + Languages
    3. Application UI/UX
    4. Additional useful domains such as Trading
    5. Continued real-world experience accumulation
    6. Reasoner/Learner/Appraiser improvements as versioned cognitive upgrades

Coding is prioritized because it becomes the implementation arm through which
approved future capability expansion can eventually build and test system
improvements.

Chat and Languages are prioritized because they form the primary human
communication surface.

UI/UX follows so the system becomes practically usable without relying on
Terminal interaction.

Other domains can then grow against the closed Central Mind contracts.


## CM.12 Development while later cognitive versions are being built

Central Mind V1 and later cognitive research may coexist.

The active stable version may continue:

- chatting;
- coding;
- learning;
- accumulating verified experience;
- using tools;
- serving the UI;
- working with domains.

A V2 Reasoner or Learner may be developed separately against the same
contracts.

It must not silently replace the active implementation.

Promotion of a new cognitive version requires:

- explicit version identity;
- tests;
- compatibility checks;
- verification;
- authorization where required;
- controlled activation;
- rollback capability.

This permits continuous system use while stronger intelligence is developed.


## CM.13 Long-term learning objective

The purpose of early LLM dependence is to bootstrap useful experience.

During V1 operation, AI Friend should accumulate governed evidence from real
work so later cognitive versions can be designed from actual system history
rather than speculation.

Useful experience includes:

- coding projects;
- successful implementations;
- failed implementations;
- debugging histories;
- user corrections;
- Trainer corrections;
- conversations;
- explanation strategies;
- language transformations;
- tool outcomes;
- verification outcomes;
- capability gaps;
- planning successes and failures;
- provider performance;
- later domain experience such as Trading.

The system must not treat quantity of stored data as intelligence.

Growth requires increasingly useful structure, relationships, verification,
retrieval and application of experience.


## CM.14 Final cognitive hierarchy

The intended hierarchy is:

    HUMAN AUTHORITY
          |
          v
      CONSTITUTION
          |
          v
      CENTRAL MIND
          |
          +-------------------------------+
          |                               |
          v                               v
      REASONER                         LEARNER
          |                               |
          v                               v
       PLANNING                     MEMORY SERVICE
          |
          +------------+
          |            |
          v            v
      QUESTIONING   SELF-APPRAISAL
          |
          v
    CAPABILITY SELECTION
          |
          +-------------------------------+
          |               |               |
          v               v               v
       DOMAINS           MODELS           TOOLS
                          |                |
                          |                v
                          |          BROKER + GUARD
                          |                |
                          +----------------+
                                   |
                                   v
                                ACTION
                                   |
                                   v
                              VERIFICATION
                                   |
                                   v
                                EVIDENCE

Capability Expansion operates from demonstrated gaps identified through this
cycle and remains subject to human authority and Guard policy.

The hierarchy must never be inverted merely because a provider is more
powerful than the current Central Mind implementation.

A powerful LLM remains a provider.

It does not become the authority above Central Mind.

===============================================================================
37. FINAL ARCHITECTURAL STATEMENT
===============================================================================

AI Friend V1 is not designed around a single LLM.

It is designed around controlled cooperation between replaceable intelligence,
persistent governed memory, deterministic tools, authenticated human
authority, explicit effects, verification and evidence.

The Central Mind coordinates.

Domains understand.

Models reason and generate.

Tools act.

Memory remembers.

The Guard authorizes.

The Verifier checks.

The Constitution governs.

Humans provide authority.

Evidence drives learning.

New capability may expand what the system can do.

It must never silently expand what the system is allowed to do.

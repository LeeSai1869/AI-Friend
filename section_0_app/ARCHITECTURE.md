# AI Friend — Section 0 App Architecture

Status: Canonical intended architecture for Section 0
Scope: section_0_app
Authority: Human/Trainer-controlled
Purpose: Define the intended structure, boundaries, composition rules, and lifecycle of the AI Friend application.

---

# 1. Core Principle

BOUNDARIES FIRST. COMPOSITION SECOND.

Section 0 is the application and UI layer of AI Friend.

Section 0 is an assembler of independently owned UI modules.

It must not become a collection of large shared HTML, JavaScript, or CSS files containing unrelated feature behavior.

The practical architectural test is:

Can this feature be changed, tested, replaced, or removed without unnecessarily affecting unrelated features?

If not, the boundary should be examined before more implementation is added.

---

# 2. Independent Feature Rule

Every independently changeable feature should have an independently owned folder/module.

Examples include:

- Chat left panel
- Chat top bar
- Chat conversation
- Chat input
- Memory Intake
- Authentication UI
- Coding project panel
- Coding file tree
- Coding editor
- Coding terminal
- Coding test results
- Trading chart
- Trading scanner
- Trading market panel
- Trading controls
- Individual Trading chart layers

A feature should own, where practical:

- markup
- behavior
- styling
- state
- requirements
- configuration
- tests
- adapters
- internal subcomponents

Parent modules compose features.

Parents should not absorb the internal implementation of their children.

---

# 3. Recursive Modularity

The same rule applies at every level.

A module may itself be composed from independently owned submodules.

Example conceptual structure:

Trading
  Chart
    Base Chart
    Candles
    Indicators
    Drawings
    Signals
    Overlays

The Chart is one Trading component.

But the Chart itself is also an assembler of independent layers.

The same principle applies to Chat and Coding.

---

# 4. Development Sequence

Normal development sequence:

1. Define boundary.
2. Define requirements.
3. Define interface/contract.
4. Implement independently.
5. Run focused validation.
6. Compose into parent.
7. Run integration validation.

We do not begin by placing new feature behavior directly into a large parent file.

---

# 5. Isolation Contract

Changing one bounded component should normally affect only that component.

Example:

Chat
  Left Panel
  Conversation
  Input

Changing Left Panel behavior should not require rewriting Conversation or Input.

Sibling components should communicate only through explicit contracts.

Incidental coupling is an architectural defect.

---

# 6. Composition Contract

A parent module may:

- instantiate children
- position children
- provide approved inputs
- receive defined outputs/events
- coordinate layout
- route explicit interactions

A parent should not duplicate child implementation.

The shell composes components.

The shell does not become the storage location for all component behavior and styling.

---

# 7. Primary Product Surfaces

AI Friend currently has three principal UI surfaces.

## Chat

Chat is the primary interface to Central Mind.

Most functionality remains accessible through Chat unless a workflow genuinely requires a specialist workspace.

Examples include:

- general conversation
- reasoning
- questioning
- planning
- Languages
- memory interaction
- general tools
- ordinary domains and capabilities
- image/video requests
- system communication

## Coding

Coding has its own specialist workspace because project navigation, files, editing, testing, terminal interaction, and development workflows require specialized UI.

## Trading

Trading has its own specialist workspace because charts, market information, scanners, signals, and authorized trading controls require specialized visual interfaces.

Other domains should remain Chat-driven unless a concrete requirement justifies another specialist workspace.

---

# 8. Chat Architecture

Intended conceptual structure:

section_0_app/
  ui/
    chat/
      shell/
      left_panel/
      top_bar/
      conversation/
      input/
      memory_intake/
      auth/
      right_panel/        optional, only when required

These are ownership boundaries.

We do not need to create empty folders before their features exist.

## Chat Shell

The shell composes Chat modules and should remain thin.

## Left Panel

The Chat left panel is independently owned.

Its navigation, chat lists, domain/workspace launch controls, layout, and panel-specific behavior belong inside its boundary.

Changing it should not require changes to Conversation or Input.

## Top Bar

The top bar owns top-level Chat controls.

Possible future examples include:

- model/provider presentation
- status indicators
- context controls
- account controls

These must not be mixed into unrelated Chat features.

## Conversation

Conversation rendering and conversation-specific interactions belong here.

## Input

Message composition belongs here.

Future features such as attachments, voice input, send behavior, and input expansion should remain inside this boundary where appropriate.

## Memory Intake

Memory Intake is a distinct workflow and therefore a distinct component.

## Authentication

Authentication presentation is independently bounded.

Authentication authority itself remains in the backend.

## Right Panel

A right panel is added only if a real requirement exists.

Do not create UI merely for symmetry.

---

# 9. Coding Architecture

Intended conceptual structure:

section_0_app/
  ui/
    coding/
      shell/
      project_panel/
      file_tree/
      editor/
      coding_chat/
      terminal/
      test_results/
      top_bar/

Coding owns its specialist UI.

The Coding left/project panel is NOT the Chat left panel.

They may look similar while having completely different requirements.

## Coding Shell

Composes the Coding workspace.

## Project Panel

Owns Coding project/workspace navigation.

## File Tree

Owns filesystem/project-tree presentation and interaction.

## Editor

Owns file/code viewing and editing presentation.

## Coding Chat

Owns communication with Central Mind in Coding context.

## Terminal

The Coding terminal is a Coding component.

Its UI, controls, output presentation, and terminal-specific state belong inside Coding.

Actual process authority remains controlled by backend authorization and Guard.

## Test Results

Test and verification presentation remains separately maintainable.

## Top Bar

Coding-specific top-level controls belong to Coding rather than Chat.

---

# 10. Trading Architecture

Intended conceptual structure:

section_0_app/
  ui/
    trading/
      shell/
      chart/
        base_chart/
        candles/
        indicators/
        drawings/
        signals/
        overlays/
      scanner/
      market_panel/
      trading_chat/
      controls/

Trading is expected to grow significantly.

Its components must therefore remain strongly isolated.

---

# 11. Trading Chart Layer Architecture

The Trading chart is a layered system.

If AI Friend buys, licenses, embeds, or integrates a chart from another provider, that chart becomes a replaceable base component.

AI Friend-specific behavior must not be unnecessarily fused into the third-party chart.

Conceptual layers:

- Base Chart
- Candle / Market Data Layer
- Indicator Layer
- Drawing Layer
- Signal Layer
- Additional Overlay Layers

Examples include:

- base chart rendering
- candles
- EMA/VWAP indicators
- support/resistance drawings
- AI Friend buy/sell markers
- liquidity overlays
- future market visualizations

Each layer owns its responsibility.

Replacing one layer should, where practical, not require rebuilding the others.

---

# 12. External Component Rule

Third-party components must be wrapped behind AI Friend-owned boundaries where practical.

Examples:

- chart libraries
- editors
- terminal renderers
- visualization libraries
- future media components

Vendor-specific assumptions should not be scattered throughout Section 0.

This allows external components to be upgraded or replaced without redesigning the application.

---

# 13. Shared Infrastructure

Only genuinely cross-surface mechanisms belong in shared infrastructure.

Intended conceptual structure:

section_0_app/
  ui/
    shared/
      transport/
      auth_session/
      tauri_bridge/
      design_tokens/
      generic_primitives/

Examples of legitimate shared infrastructure:

- WebSocket transport
- authentication/session client
- Tauri communication bridge
- universal design tokens
- truly generic UI primitives

SHARED DOES NOT MEAN CONVENIENT.

Feature-specific behavior must not be moved into shared merely because two modules currently use similar code.

The shared area must never become a dumping ground.

---

# 14. Reuse Without Coupling

Two components may look similar without being the same feature.

Examples:

- Chat may have a left panel.
- Coding may have a project/left panel.
- Trading may have a market panel.

These should not automatically share feature implementation.

They may share genuinely universal primitives such as:

- generic resize behavior
- generic button primitive
- generic panel frame
- typography/design tokens

Their feature behavior remains independently owned.

---

# 15. UI Is Not Authority

Frontend visibility does not grant system authority.

Authority remains:

Authenticated account/session
  Central Mind
    Guard authorization
      Domain / capability / tool / operation

Hiding Coding from a Trading-only UI is not the security boundary.

Backend authentication and Guard remain authoritative.

A person must not gain Coding authority merely by modifying frontend code.

---

# 16. Product Distribution

The modular structure should allow future specialized distributions.

Possible full application:

AI Friend Full
  Chat
  Coding
  Trading

Possible specialized application:

Trading Product
  Trading UX

Possible Coding-oriented application:

Coding Product
  Coding UX

Different UI distributions may expose different surfaces while sharing Central Mind where authorized.

Packaging never replaces backend authorization.

---

# 17. App Runtime Lifecycle

Section 0 owns the desktop application lifecycle.

Startup sequence:

AI Friend App
  Start Central Mind backend
  Establish backend readiness
  Connect UI
  Authenticate/session
  Authorized application becomes operational

Full application exit:

AI Friend App exits
  Terminate backend owned by this app
  Wait briefly
  Force terminate owned child only if necessary
  Clean explicitly approved ephemeral caches

The application must never indiscriminately terminate unrelated processes.

---

# 18. Durable State Must Survive Closure

Hard application closure must preserve durable AI Friend state.

Never automatically erase:

- Section 3 Permanent Memory
- authentication database
- Chat state
- Project/Workspace state
- audit/history
- Constitution
- model registry
- user project data
- durable configuration

Application closure terminates runtime, not intelligence/history.

---

# 19. Cache Cleanup Rule

Cache cleanup must use an explicit allowlist.

Potentially safe examples after confirmation:

- __pycache__
- .pyc
- .pytest_cache
- .mypy_cache
- explicitly classified temporary runtime files

Unknown folders must not be deleted merely because their names contain cache, temp, or runtime.

Persistent state always wins over aggressive cleanup.

---

# 20. Component Documentation

A significant component may maintain its own design/requirements document inside its boundary.

Example:

chat/
  left_panel/
    README.md

Another example:

trading/
  chart/
    ARCHITECTURE.md

This Section 0 document defines parent architectural rules.

Component documents define component-specific requirements.

---

# 21. Folder Names vs Boundaries

Exact directory names may evolve.

The architectural requirement is the ownership boundary, not the spelling of the folder.

A folder can be renamed or reorganized when justified if:

- ownership remains clear
- coupling is not increased
- sibling isolation remains intact
- composition remains explicit

---

# 22. No Premature Empty Architecture

Do not create dozens of empty directories simply because they appear in conceptual diagrams.

Create a boundary when implementing or migrating that feature.

The filesystem should remain useful and understandable.

---

# 23. Cleanup and Migration Rule

When replacing an existing flat implementation:

1. Create or migrate the bounded replacement.
2. Validate the component independently.
3. Integrate it through the parent contract.
4. Validate integration.
5. Remove the obsolete duplicate implementation.

Do not leave old and new implementations active indefinitely.

There should be one canonical implementation of each feature.

---

# 24. Change Rule

Before modifying UI behavior, identify the owning boundary.

Correct pattern:

Need to change Chat Left Panel
  Work inside chat/left_panel
  Validate Left Panel
  Validate Chat composition

Incorrect pattern:

Need to change Chat Left Panel
  Edit large global UI files
  Accidentally alter Coding or Trading

Cross-boundary changes require an explicit interface reason.

---

# 25. Structural Change Rule

Once these boundaries are established, ordinary feature development should occur inside them.

Do not repeatedly redesign Section 0 structure.

A meaningful structural change must record:

- what changed
- why it changed
- affected boundaries
- migration impact
- compatibility impact

Structure changes only when the existing architecture is genuinely inadequate.

---

# 26. Testing Principle

Testing follows ownership boundaries.

Preferred sequence:

Component-focused validation
  Parent composition validation
    Surface integration validation
      Full application validation when warranted

A small Chat Left Panel change should not automatically require rebuilding every unrelated Trading feature.

Broader testing belongs at meaningful integration milestones.

---

# 27. Relationship With Central Mind

Section 0 is the interface layer.

It must not become another Central Mind.

UI modules may:

- present information
- collect user intent
- maintain presentation state
- request authorized operations
- render results

Central Mind remains responsible for cognitive coordination.

Guard remains responsible for authorization.

Verifier remains responsible for post-action correctness.

Section 3 remains permanent reusable-memory authority.

The UI must not duplicate these responsibilities.

---

# 28. Existing Flat UI Is Migration Source

The current Section 0 implementation contains useful working functionality but grew in a flatter structure.

Current examples include:

- bridge.js
- chat.js
- code.js
- sidebar.js
- intake.js
- shared styles.css
- window-level HTML files

These files are migration sources, not the desired final ownership model.

Working behavior should be preserved while its ownership is moved into the canonical boundaries defined here.

After a modular replacement is validated, obsolete flat duplicates must be removed.

---

# 29. Current Surface Decision

Current product decision:

- Chat is the primary Central Mind interface.
- Coding is a dedicated specialist workspace.
- Trading is a dedicated specialist workspace.
- Other domains remain Chat-driven unless a concrete future workflow justifies a specialist UI.

Do not create a dedicated window for every domain by default.

---

# 30. Implementation Direction

Implementation proceeds from this document.

Order:

1. Preserve useful existing behavior.
2. Establish shared infrastructure boundary.
3. Establish Chat boundaries.
4. Migrate Chat components one at a time.
5. Validate Chat composition.
6. Remove obsolete Chat flat implementation.
7. Establish Coding boundaries.
8. Migrate Coding components one at a time.
9. Validate Coding composition.
10. Remove obsolete Coding flat implementation.
11. Establish Trading boundaries.
12. Build Trading components independently.
13. Compose Trading workspace.
14. Validate application lifecycle.
15. Build the distributable macOS application.
16. Validate startup, authentication, windows, shutdown, and state preservation.

---

# 31. Governing Rule

The permanent Section 0 rule is:

EVERY INDEPENDENTLY CHANGEABLE FEATURE IS INDEPENDENTLY BOUNDED.

And:

BOUNDARIES FIRST. COMPOSITION SECOND.

When future Section 0 work becomes unclear, consult this document before changing structure.

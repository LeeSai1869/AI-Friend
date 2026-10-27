# Actual Design - AI Friend V1

Generated: 2026-10-21 17:27:49
Source: mechanical analysis of code (no model)

This document describes the actual current state of the code.
It regenerates automatically when architecture changes.
It is not a specification. For requirements, see each
section's requirements.md.

## section_0_app

Total files: 41  (.py: 0, .js/.ts: 26, .rs: 2, .md: 1, other: 12)

### JavaScript modules

- `section_0_app/src/chat.js`
- `section_0_app/src/intake.js`
- `section_0_app/src/intents.js`
- `section_0_app/src/sidebar.js`
- `section_0_app/src/trading.js`
- `section_0_app/src/ui/chat/auth/login_overlay.js`
- `section_0_app/src/ui/chat/conversation/conversation.js`
- `section_0_app/src/ui/chat/input/input.js`
- `section_0_app/src/ui/chat/intent/intent.js`
- `section_0_app/src/ui/chat/left_panel/left_panel.js`
- `section_0_app/src/ui/chat/memory_intake/memory_intake.js`
- `section_0_app/src/ui/chat/shell/shell.js`
- `section_0_app/src/ui/chat/top_bar/top_bar.js`
- `section_0_app/src/ui/coding/conversation/conversation.js`
- `section_0_app/src/ui/coding/editor/editor.js`
- `section_0_app/src/ui/coding/explorer/explorer.js`
- `section_0_app/src/ui/coding/input/input.js`
- `section_0_app/src/ui/coding/left_panel/left_panel.js`
- `section_0_app/src/ui/coding/project/project.js`
- `section_0_app/src/ui/coding/settings/settings.js`
- `section_0_app/src/ui/coding/shell/shell.js`
- `section_0_app/src/ui/coding/terminal/terminal.js`
- `section_0_app/src/ui/shared/auth_session/session.js`
- `section_0_app/src/ui/shared/build.js`
- `section_0_app/src/ui/shared/chat_history/chat_history.js`
- `section_0_app/src/ui/shared/transport/backend.js`

### Rust modules

- `section_0_app/src-tauri/build.rs`
- `section_0_app/src-tauri/src/main.rs`

### Documentation

- `section_0_app/ARCHITECTURE.md`

### Other files

- `section_0_app/package-lock.json`
- `section_0_app/package.json`
- `section_0_app/src/styles.css`
- `section_0_app/src/window-chat.html`
- `section_0_app/src/window-code.html`
- `section_0_app/src/window-trading.html`
- `section_0_app/src-tauri/capabilities/desktop.json`
- `section_0_app/src-tauri/gen/schemas/acl-manifests.json`
- `section_0_app/src-tauri/gen/schemas/capabilities.json`
- `section_0_app/src-tauri/gen/schemas/desktop-schema.json`
- `section_0_app/src-tauri/gen/schemas/macOS-schema.json`
- `section_0_app/src-tauri/tauri.conf.json`

## section_10_workspace

Total files: 8  (.py: 6, .js/.ts: 0, .rs: 0, .md: 1, other: 1)

### Python modules

- `section_10_workspace/scaffolds/memory_section/sources/__init__.py` (9 lines)
  - imports: api, entry
- `section_10_workspace/scaffolds/memory_section/sources/api.py` (272 lines)
  - imports: __future__, json, time, pathlib, typing, , entry, store
  - class `Memory`: __init__, _load_sequences, _save_sequences, _next_seq, record, get, exists, count
- `section_10_workspace/scaffolds/memory_section/sources/config.py` (93 lines)
  - imports: __future__, pathlib
  - functions: compute_score, compute_state
- `section_10_workspace/scaffolds/memory_section/sources/entry.py` (182 lines)
  - imports: __future__, time, dataclasses, typing, 
  - class `Originator`: as_dict
  - class `Failure`: as_dict
  - class `CrossRef`: as_dict
  - class `Entry`: recompute_score, state, record_success, record_failure, as_dict, from_dict
  - functions: make_id, parse_id
- `section_10_workspace/scaffolds/memory_section/sources/index.py` (65 lines)
  - imports: __future__, typing, store
  - class `Index`: __init__, build, _add, _ensure, by_domain, by_tag, by_kind, by_class
- `section_10_workspace/scaffolds/memory_section/sources/store.py` (60 lines)
  - imports: __future__, json, threading, pathlib, typing, , entry
  - class `Store`: __init__, _path_for, write, read, exists, list_ids, iter_entries, count

### Documentation

- `section_10_workspace/scaffolds/memory_section/sources/readme.md`

### Other files

- `section_10_workspace/scaffolds/memory_section/scaffold.json`

## section_1_central_mind

### Central Mind activity boundaries

- `mind/regular_operation/` owns regular request orchestration.
- `mind/self_assessment/` owns self-assessment and its Administrator-review proposals.
- `mind/feature_expansion/` owns capability-gap expansion proposals.
- `mind/shared/` owns the shared questionnaire interface.
Legacy module paths re-export these implementations for compatibility.

Total files: 48  (.py: 40, .js/.ts: 0, .rs: 0, .md: 7, other: 1)

### Python modules

- `section_1_central_mind/auth_service.py` (415 lines)
  - imports: __future__, hashlib, hmac, json, contextlib, os, re, secrets
  - class `AuthenticationError`: 
  - class `AuthService`: __init__, _connect, _initialize, _password_material, _check_credentials_input, _token_hash, _audit, _audit_committed
- `section_1_central_mind/bootstrap.py` (35 lines)
  - imports: __future__, sys, pathlib
  - functions: add_sections_to_path
- `section_1_central_mind/config.py` (35 lines)
  - imports: __future__, json, pathlib
  - functions: load_config, save_default_config
- `section_1_central_mind/guard/__init__.py` (3 lines)
  - imports: layer
- `section_1_central_mind/guard/contract.py` (493 lines)
  - imports: __future__, dataclasses, time, uuid, typing, resources
  - class `ToolEffect`: __post_init__, to_dict
  - class `ResourceBoundary`: __post_init__, to_dict
  - class `ClassifiedEffect`: __post_init__, to_dict
  - class `GuardPrincipal`: __post_init__
  - class `GuardComponent`: __post_init__
  - class `GuardRequest`: __post_init__, to_audit_dict
- `section_1_central_mind/guard/effect_policy.py` (531 lines)
  - imports: __future__, dataclasses, typing, contract, resources
  - class `EffectDecision`: 
  - class `EffectPolicy`: __init__, _normalize_scopes, _normalize_resource_rules, _normalize_semantic_rules, _effective_requester, _component_access_allowed, _evaluate_filesystem_effect, _evaluate_boundary
- `section_1_central_mind/guard/effects.py` (145 lines)
  - imports: __future__, typing, contract, resources
  - class `EffectClassifier`: __init__, classify
- `section_1_central_mind/guard/layer.py` (245 lines)
  - imports: __future__, pathlib, contract, policy, effect_policy
  - class `GuardLayer`: __init__, audit_action
- `section_1_central_mind/guard/policy.py` (172 lines)
  - imports: __future__, dataclasses, typing, contract
  - class `PolicyDecision`: 
  - class `GuardPolicy`: __init__, _normalize_capability, _normalize_set, _normalize_grants, grants_for, evaluate
- `section_1_central_mind/guard/production_policy.py` (118 lines)
  - imports: __future__, effect_policy, policy
  - functions: build_production_guard_policy, build_production_effect_policy
- `section_1_central_mind/guard/resources.py` (377 lines)
  - imports: __future__, dataclasses, pathlib, os, typing
  - class `ResourceDescriptor`: __post_init__, to_dict
  - class `ResourceClassifier`: __init__, _is_within, _build_component_roots, _semantic_roots, boundaries_within, classify
- `section_1_central_mind/main.py` (124 lines)
  - imports: __future__, sys, pathlib, bootstrap, section_4_chatbox, mind
  - functions: main, _argument_value, main_serve
- `section_1_central_mind/mind/__init__.py` (10 lines)
  - imports: loop, organ, proposals, audit, scheduler
- `section_1_central_mind/mind/appraiser.py` (173 lines)
  - imports: __future__, typing, cognition
  - class `SelfAppraiser`: appraise, capability_gap, _classify_failure, _reusable_value
- `section_1_central_mind/mind/audit.py` (110 lines)
  - imports: __future__, typing
  - class `AuditStage`: __init__, evaluate, _v
- `section_1_central_mind/mind/broker.py` (676 lines)
  - imports: __future__, importlib, importlib.util, sys, time, guard.contract, guard.effects, guard.resources
  - class `BoundToolBroker`: __init__, component_chain, call, available, with_workspace, __setattr__
  - class `ToolBroker`: __init__, _discover, bind_component, bind_central_mind, reset_budget, available, _call_bound, _finish
- `section_1_central_mind/mind/caller.py` (167 lines)
  - imports: __future__, typing, json
  - class `Caller`: __init__, call, route, _invoke_resource
- `section_1_central_mind/mind/capability_expansion.py` (118 lines)
  - imports: __future__, dataclasses, hashlib, typing, time
  - class `CapabilityProposal`: as_dict
  - class `CapabilityExpansion`: __init__, propose_from_appraisal, proposals
- `section_1_central_mind/mind/cognition.py` (134 lines)
  - imports: __future__, dataclasses, typing
  - class `CognitiveStep`: as_dict
  - class `CognitivePlan`: as_dict
  - class `Appraisal`: __post_init__, as_dict
- `section_1_central_mind/mind/composer.py` (58 lines)
  - imports: __future__, typing
  - class `Composer`: combine, _merge_outputs
- `section_1_central_mind/mind/designer.py` (282 lines)
  - imports: __future__, ast, hashlib, threading, time, pathlib, typing
  - class `Designer`: __init__, _is_included, _hash_architecture, _parse_python, build, write, run_once, _watch_loop
- `section_1_central_mind/mind/inventory.py` (187 lines)
  - imports: __future__, importlib.util, dataclasses, pathlib, typing
  - class `OrganInfo`: 
  - class `Inventory`: __init__, discover, all, get, by_keyword, by_capability, names, capability_catalog
- `section_1_central_mind/mind/learner.py` (88 lines)
  - imports: __future__, typing
  - class `Learner`: __init__, learn
- `section_1_central_mind/mind/loop.py` (1545 lines)
  - imports: __future__, time, pathlib, typing, inventory, router, composer, questioner
  - class `CentralMind`: __init__, _record_experience, run_self_assessment, _fulfill_domain_requirement, _receive_memory_proposal, learn_memory_proposal, decide_memory_proposal, _semantic_route_model
- `section_1_central_mind/mind/organ.py` (99 lines)
  - imports: __future__, typing
  - class `Organ`: can_handle, handle, questions, verify, evaluate_knowledge, receive_proposal
- `section_1_central_mind/mind/proposals.py` (137 lines)
  - imports: __future__, time, uuid, dataclasses, typing
  - class `ProposalContractError`: 
  - class `Proposal`: __post_init__, as_dict
  - class `ProposalQueue`: __init__, append, get, list, record_audit, record_decision, _require
- `section_1_central_mind/mind/questioner.py` (29 lines)
  - imports: __future__, typing
  - class `Questioner`: __init__, ask
- `section_1_central_mind/mind/reasoner/__init__.py` (9 lines)
  - imports: head
- `section_1_central_mind/mind/reasoner/consultation.py` (137 lines)
  - imports: __future__, typing
  - class `Consultation`: __init__, available, request
- `section_1_central_mind/mind/reasoner/discovery.py` (235 lines)
  - imports: __future__, typing
  - class `Discovery`: __init__, _component, validate_consultation, trusted_consultations, unresolved_material_needs
- `section_1_central_mind/mind/reasoner/head.py` (831 lines)
  - imports: __future__, typing, cognition, state, understanding, discovery, consultation
  - class `Reasoner`: __init__, _recall, _memory_ids, _semantic_catalog, _semantic_proposal, _strings, _assimilate_proposal, _validate_steps
- `section_1_central_mind/mind/reasoner/state.py` (134 lines)
  - imports: __future__, dataclasses, typing
  - class `ReasoningEvidence`: as_dict
  - class `ReasoningState`: add_evidence, mark_consulted, can_continue, can_consult, begin_cycle, evidence_payload, as_dict
- `section_1_central_mind/mind/reasoner/understanding.py` (380 lines)
  - imports: __future__, json, typing
  - class `SemanticUnderstanding`: __init__, _string_list, _confidence, _strip_json_fence, _catalog, propose
- `section_1_central_mind/mind/resource_socket.py` (91 lines)
  - imports: __future__, dataclasses, typing
  - class `ResourceRequirement`: as_dict
  - class `ResourceSocket`: __init__, connect, connected, request
- `section_1_central_mind/mind/router.py` (68 lines)
  - imports: __future__, typing, inventory
  - class `Router`: __init__, route, _score, _fallback
- `section_1_central_mind/mind/scheduler.py` (118 lines)
  - imports: __future__, threading, time, dataclasses, typing
  - class `_Job`: 
  - class `Scheduler`: __init__, register, unregister, start, stop, run_once, status, _run
- `section_1_central_mind/mind/scorer.py` (121 lines)
  - imports: __future__, collections, copy, typing, json, time
  - class `EvidenceContractError`: 
  - class `Scorer`: __init__, record, recent, read_records, _validate_json
- `section_1_central_mind/mind/verifier.py` (41 lines)
  - imports: __future__, typing
  - class `Verifier`: _valid_verdict, verify
- `section_1_central_mind/runtime_identity.py` (2 lines)
- `section_1_central_mind/server.py` (1207 lines)
  - imports: __future__, asyncio, json, os, sys, pathlib, typing, auth_service
  - class `AppChatbox`: __init__, ask, _emit, notify, present, tool_status
  - class `SessionRuntimes`: __init__, resolve, subscribe, unsubscribe, forget
  - functions: _process_exists, _default_auth_database, _is_within_root, _guard_principal_from_account, run_server

### Documentation

- `section_1_central_mind/START_HERE.md`
- `section_1_central_mind/guard/rules/authority.md`
- `section_1_central_mind/guard/rules/deletion.md`
- `section_1_central_mind/guard/rules/kernel.md`
- `section_1_central_mind/guard/rules/memory.md`
- `section_1_central_mind/guard/rules/readme.md`
- `section_1_central_mind/readme.md`

### Other files

- `section_1_central_mind/guard/denials.json`

## section_2_constitution

Total files: 9  (.py: 0, .js/.ts: 0, .rs: 0, .md: 9, other: 0)

### Documentation

- `section_2_constitution/authority.md`
- `section_2_constitution/coding.md`
- `section_2_constitution/core.md`
- `section_2_constitution/design.md`
- `section_2_constitution/design_actual.md`
- `section_2_constitution/image.md`
- `section_2_constitution/readme.md`
- `section_2_constitution/trading.md`
- `section_2_constitution/video.md`

## section_3_memory

Total files: 9  (.py: 8, .js/.ts: 0, .rs: 0, .md: 1, other: 0)

### Python modules

- `section_3_memory/__init__.py` (9 lines)
  - imports: api, entry
- `section_3_memory/api.py` (274 lines)
  - imports: __future__, json, time, pathlib, typing, , entry, store
  - class `Memory`: __init__, _load_sequences, _save_sequences, _next_seq, record, get, exists, count
- `section_3_memory/bridge.py` (228 lines)
  - imports: __future__, pathlib, typing, api
  - class `MemoryBridge`: __init__, recall, recall_tested, recall_rejections, get, remember_raw, remember_tested, remember_derived
- `section_3_memory/config.py` (96 lines)
  - imports: __future__, pathlib, os
  - functions: compute_score, compute_state
- `section_3_memory/entry.py` (184 lines)
  - imports: __future__, time, dataclasses, typing, 
  - class `Originator`: as_dict
  - class `Failure`: as_dict
  - class `CrossRef`: as_dict
  - class `Entry`: recompute_score, state, record_success, record_failure, as_dict, from_dict
  - functions: make_id, parse_id
- `section_3_memory/index.py` (65 lines)
  - imports: __future__, typing, store
  - class `Index`: __init__, build, _add, _ensure, by_domain, by_tag, by_kind, by_class
- `section_3_memory/service.py` (541 lines)
  - imports: __future__, copy, json, os, tempfile, time, pathlib, typing
  - class `MemoryService`: __init__, _load_deletion_journal, _save_deletion_journal, _load_knowledge_journal, _save_knowledge_journal, _find_committed_entry, register_proposal_handler, _dispatch_knowledge_proposal
  - class `MemoryClient`: __init__, recall, recall_tested, recall_rejections, get, propose_knowledge, propose_delete, summary
- `section_3_memory/store.py` (70 lines)
  - imports: __future__, json, re, threading, pathlib, typing, , entry
  - class `Store`: __init__, _path_for, write, read, exists, list_ids, iter_entries, count

### Documentation

- `section_3_memory/readme.md`

## section_4_chatbox

Total files: 4  (.py: 4, .js/.ts: 0, .rs: 0, .md: 0, other: 0)

### Python modules

- `section_4_chatbox/__init__.py` (22 lines)
  - imports: chatbox, runtime, state
- `section_4_chatbox/chatbox.py` (98 lines)
  - imports: __future__, typing
  - class `Chatbox`: __init__, ask, render_for_review, notify, present, tool_status
- `section_4_chatbox/runtime.py` (313 lines)
  - imports: __future__, pathlib, os, typing, state
  - class `ChatRuntime`: __init__, delete_chat, open_chat, _context_packet, _final_text, list_chats, load_chat, respond
- `section_4_chatbox/state.py` (530 lines)
  - imports: __future__, json, time, uuid, hashlib, re, shutil, dataclasses
  - class `Turn`: 
  - class `Rejected`: 
  - class `Verified`: 
  - class `Chat`: __init__, _new_id, is_first_message, set_topic, check_topic, _words, _recent_text, model_messages
  - class `ChatStore`: __init__, _chat_path, delete, create, load, list_ids, latest

## section_5_domains

Total files: 65  (.py: 63, .js/.ts: 0, .rs: 0, .md: 1, other: 1)

### Python modules

- `section_5_domains/__init__.py` (6 lines)
- `section_5_domains/coding/__init__.py` (1 lines)
- `section_5_domains/coding/__manifest__.py` (74 lines)
- `section_5_domains/coding/classification/__init__.py` (3 lines)
  - imports: classifier
- `section_5_domains/coding/classification/classifier.py` (84 lines)
  - imports: __future__, cognition, typing
  - class `CodingClassifier`: classify
- `section_5_domains/coding/coding_engine.py` (641 lines)
  - imports: __future__, pathlib, typing, mind.organ, project_context, classification, inspection, recall
  - class `CodingOrgan`: __init__, _for_caller, evaluate_knowledge, verify, can_handle, open_project, close_project, describe_project
  - functions: _assess_coding_result
- `section_5_domains/coding/cognition.py` (118 lines)
  - imports: __future__, ast, json
  - class `CodingCycle`: generate
  - functions: request_model, parse_object, resource_question
- `section_5_domains/coding/debugger.py` (10 lines)
  - imports: cognition
  - class `Debugger`: diagnose
- `section_5_domains/coding/execution.py` (66 lines)
  - imports: __future__, json, cognition, tester
  - class `CodingExecution`: __init__, run
- `section_5_domains/coding/experience.py` (54 lines)
  - imports: __future__, collections, hashlib, json, tester
  - class `CodingExperience`: __init__, _key, remember, evaluate
- `section_5_domains/coding/history/__init__.py` (3 lines)
  - imports: history
- `section_5_domains/coding/history/history.py` (80 lines)
  - imports: __future__, json, pathlib, time, workspace
  - class `ProjectHistory`: __init__, path, read, prepare_append
- `section_5_domains/coding/inspection/__init__.py` (3 lines)
  - imports: inspector
- `section_5_domains/coding/inspection/analyzer.py` (73 lines)
  - imports: __future__, cognition, typing
  - class `InspectionAnalyzer`: read_selected, analyze
- `section_5_domains/coding/inspection/inspector.py` (131 lines)
  - imports: __future__, analyzer, selector
  - class `CodingInspector`: __init__, inspect
- `section_5_domains/coding/inspection/selector.py` (82 lines)
  - imports: __future__, cognition, json, re, typing
  - class `RelevantFileSelector`: select
- `section_5_domains/coding/inspector.py` (4 lines)
  - imports: inspection
- `section_5_domains/coding/memory/__init__.py` (3 lines)
  - imports: memory
- `section_5_domains/coding/memory/memory.py` (53 lines)
  - imports: __future__, json, pathlib, workspace
  - class `ProjectMemory`: __init__, path, read, prepare_write
- `section_5_domains/coding/operations.py` (57 lines)
  - imports: __future__, json, pathlib, cognition, planner, tester
  - class `CodingOperations`: plan, test
  - functions: selected_capability, python_tests
- `section_5_domains/coding/planner.py` (14 lines)
  - imports: __future__, cognition
  - class `Planner`: plan
- `section_5_domains/coding/project/__init__.py` (3 lines)
  - imports: project
- `section_5_domains/coding/project/project.py` (37 lines)
  - imports: __future__, dataclasses, pathlib
  - class `CodingProject`: open, to_dict
- `section_5_domains/coding/project_context.py` (88 lines)
  - imports: __future__, pathlib, history, memory, project, rules, tree, workspace
  - class `CodingProjectContext`: __init__, is_open, project, workspace, tree, rules, memory, history
- `section_5_domains/coding/recall/__init__.py` (3 lines)
  - imports: recaller
- `section_5_domains/coding/recall/recaller.py` (64 lines)
  - imports: __future__, typing
  - class `CodingRecaller`: recall
- `section_5_domains/coding/rules/__init__.py` (3 lines)
  - imports: rules
- `section_5_domains/coding/rules/rules.py` (38 lines)
  - imports: __future__, workspace
  - class `ProjectRules`: __init__, load
- `section_5_domains/coding/tester.py` (20 lines)
  - imports: __future__
  - class `Tester`: run, passed
- `section_5_domains/coding/tree/__init__.py` (3 lines)
  - imports: tree
- `section_5_domains/coding/tree/tree.py` (113 lines)
  - imports: __future__, pathlib, workspace
  - class `ProjectTree`: __init__, _trusted_entry, list, files
- `section_5_domains/coding/verifier.py` (62 lines)
  - imports: typing, tester
  - class `Verifier`: verify
- `section_5_domains/coding/workspace/__init__.py` (3 lines)
  - imports: workspace
- `section_5_domains/coding/workspace/workspace.py` (42 lines)
  - imports: __future__, pathlib, project
  - class `CodingWorkspace`: __init__, resolve, relative, contains
- `section_5_domains/coding/writer.py` (7 lines)
  - imports: execution
- `section_5_domains/general/__manifest__.py` (20 lines)
- `section_5_domains/general/general_engine.py` (36 lines)
  - imports: __future__, typing, mind.organ
  - class `GeneralOrgan`: can_handle, handle
- `section_5_domains/image/__init__.py` (16 lines)
  - imports: base
  - class `ImageDomain`: capabilities, execute
- `section_5_domains/image/__manifest__.py` (13 lines)
- `section_5_domains/image/domain.py` (0 lines)
- `section_5_domains/image/image_engine.py` (17 lines)
  - imports: mind.organ
  - class `ImageOrgan`: can_handle, handle
- `section_5_domains/image/inspector.py` (0 lines)
- `section_5_domains/image/tester.py` (0 lines)
- `section_5_domains/image/verifier.py` (0 lines)
- `section_5_domains/image/writer.py` (0 lines)
- `section_5_domains/languages/__manifest__.py` (58 lines)
- `section_5_domains/languages/languages_engine.py` (418 lines)
  - imports: __future__, json, re, pathlib, typing, mind.organ
  - class `LanguagesEngine`: __init__, _load_languages, known_natural, known_technical, handle, _learn, _read, _translate
  - functions: language_name
- `section_5_domains/trading/__init__.py` (16 lines)
  - imports: base
  - class `TradingDomain`: capabilities, execute
- `section_5_domains/trading/__manifest__.py` (13 lines)
- `section_5_domains/trading/domain.py` (0 lines)
- `section_5_domains/trading/inspector.py` (0 lines)
- `section_5_domains/trading/tester.py` (0 lines)
- `section_5_domains/trading/trading_engine.py` (17 lines)
  - imports: mind.organ
  - class `TradingOrgan`: can_handle, handle
- `section_5_domains/trading/verifier.py` (0 lines)
- `section_5_domains/trading/writer.py` (0 lines)
- `section_5_domains/video/__init__.py` (16 lines)
  - imports: base
  - class `VideoDomain`: capabilities, execute
- `section_5_domains/video/__manifest__.py` (13 lines)
- `section_5_domains/video/domain.py` (0 lines)
- `section_5_domains/video/inspector.py` (0 lines)
- `section_5_domains/video/tester.py` (0 lines)
- `section_5_domains/video/verifier.py` (0 lines)
- `section_5_domains/video/video_engine.py` (17 lines)
  - imports: mind.organ
  - class `VideoOrgan`: can_handle, handle
- `section_5_domains/video/writer.py` (0 lines)

### Documentation

- `section_5_domains/coding/rules.md`

### Other files

- `section_5_domains/languages/languages.json`

## section_6_capabilities

Total files: 2  (.py: 2, .js/.ts: 0, .rs: 0, .md: 0, other: 0)

### Python modules

- `section_6_capabilities/__init__.py` (3 lines)
  - imports: capability_manager
- `section_6_capabilities/capability_manager.py` (32 lines)
  - imports: __future__, pathlib, typing
  - class `CapabilityManager`: __init__, names, register

## section_7_models

Total files: 8  (.py: 7, .js/.ts: 0, .rs: 0, .md: 1, other: 0)

### Python modules

- `section_7_models/__init__.py` (3 lines)
  - imports: interface
- `section_7_models/interface.py` (183 lines)
  - imports: __future__, typing
  - class `ModelProvider`: generate, chat, is_available
  - functions: provider_name_for, execution_model_for, build_resource_provider, build_provider
- `section_7_models/model_router.py` (180 lines)
  - imports: __future__, json, re, pathlib, yaml, requests
  - class `ModelRouter`: __init__, _available, _candidates, fulfill, try_capability
  - functions: failure_code, _answer
- `section_7_models/providers/__init__.py` (1 lines)
- `section_7_models/providers/ollama.py` (65 lines)
  - imports: __future__, os, requests
  - class `OllamaProvider`: __init__, models, is_available, chat, generate
- `section_7_models/providers/openai_compatible.py` (46 lines)
  - imports: __future__, requests
  - class `OpenAICompatibleProvider`: __init__, chat, generate
- `section_7_models/resource_selector.py` (448 lines)
  - imports: __future__, dataclasses, typing
  - class `ResourceRequirement`: from_mapping
  - class `ResourceCandidate`: 
  - functions: _strings, _blob, _installed, _quality, _eligible, rank_resources

### Documentation

- `section_7_models/models_readme.md`

## section_8_tools

Total files: 25  (.py: 25, .js/.ts: 0, .rs: 0, .md: 0, other: 0)

### Python modules

- `section_8_tools/_base/__init__.py` (2 lines)
  - imports: tool
- `section_8_tools/_base/paths.py` (50 lines)
  - imports: __future__, pathlib
  - functions: missing_parent_directories
- `section_8_tools/_base/tool.py` (44 lines)
  - imports: __future__, pathlib, typing, guard.contract
  - class `Tool`: __init__, effects, call, _resolve
- `section_8_tools/filesystem/__init__.py` (2 lines)
  - imports: filesystem
- `section_8_tools/filesystem/__manifest__.py` (25 lines)
- `section_8_tools/filesystem/filesystem.py` (228 lines)
  - imports: __future__, pathlib, typing, _base.tool, guard.contract, _base.paths
  - class `ListFiles`: effects, call
  - class `ReadFile`: effects, call
  - class `SearchFiles`: effects, call
  - class `WriteFile`: effects, call
- `section_8_tools/folders/__init__.py` (2 lines)
  - imports: folders
- `section_8_tools/folders/__manifest__.py` (16 lines)
- `section_8_tools/folders/folders.py` (64 lines)
  - imports: __future__, pathlib, typing, _base.tool, _base.paths, guard.contract
  - class `CreateFolder`: effects, call
- `section_8_tools/intake/__init__.py` (2 lines)
  - imports: intake
- `section_8_tools/intake/__manifest__.py` (21 lines)
- `section_8_tools/intake/intake.py` (233 lines)
  - imports: __future__, json, time, pathlib, typing, _base.tool, guard.contract
  - class `IntakePropose`: effects, _source_path, _read_workspace, call
  - class `IntakeCommit`: effects, call
- `section_8_tools/scaffold/__init__.py` (2 lines)
  - imports: scaffold
- `section_8_tools/scaffold/__manifest__.py` (23 lines)
- `section_8_tools/scaffold/scaffold.py` (326 lines)
  - imports: __future__, json, pathlib, typing, _base.tool, guard.contract, _base.paths
  - class `_ScaffoldBase`: _scaffolds_root
  - class `ListScaffolds`: effects, call
  - class `ReadScaffold`: effects, call
  - class `ApplyScaffold`: effects, call
- `section_8_tools/terminal/__init__.py` (2 lines)
  - imports: terminal
- `section_8_tools/terminal/__manifest__.py` (27 lines)
- `section_8_tools/terminal/python_tests.py` (234 lines)
  - imports: __future__, json, io, tarfile, time, os, pathlib, re
  - class `RunPythonTests`: _validate, effects, call
- `section_8_tools/terminal/terminal.py` (213 lines)
  - imports: __future__, shlex, subprocess, pathlib, typing, _base.tool, guard.contract, python_tests
  - class `RunCommand`: effects, call
  - class `RunPythonCompile`: _validated_paths, effects, call
  - functions: _result
- `section_8_tools/vision/__init__.py` (2 lines)
  - imports: vision
- `section_8_tools/vision/__manifest__.py` (32 lines)
- `section_8_tools/vision/vision.py` (446 lines)
  - imports: __future__, base64, json, re, subprocess, urllib.request, pathlib, typing
  - class `ImageDescribe`: effects, call
  - class `ImageReadText`: effects, call
  - class `PdfRead`: effects, call
  - class `VideoExtractFrames`: effects, call
  - functions: _encode_image_b64, _call_vision
- `section_8_tools/web/__init__.py` (2 lines)
  - imports: web
- `section_8_tools/web/__manifest__.py` (19 lines)
- `section_8_tools/web/web.py` (218 lines)
  - imports: __future__, re, html.parser, typing, _base.tool, guard.contract
  - class `_TextExtractor`: __init__, handle_starttag, handle_endtag, handle_data
  - class `WebSearch`: effects, call
  - class `WebFetch`: effects, call

# Actual Design - AI Friend V1

Generated: 2026-11-25 16:50:21
Source: mechanical analysis of code (no model)

This document describes the actual current state of the code.
It regenerates automatically when architecture changes.
It is not a specification. For requirements, see each
section's requirements.md.

## section_0_app

Total files: 42  (.py: 0, .js/.ts: 27, .rs: 2, .md: 1, other: 12)

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
- `section_0_app/src/ui/coding/shell/shell.js`
- `section_0_app/src/ui/coding/terminal/terminal.js`
- `section_0_app/src/ui/shared/account_controls/account_controls.js`
- `section_0_app/src/ui/shared/auth_session/session.js`
- `section_0_app/src/ui/shared/build.js`
- `section_0_app/src/ui/shared/chat_history/chat_history.js`
- `section_0_app/src/ui/shared/media_permissions.js`
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

Total files: 19  (.py: 16, .js/.ts: 0, .rs: 0, .md: 1, other: 2)

### Python modules

- `section_10_workspace/branch_test/add_values.py` (2 lines)
  - functions: add
- `section_10_workspace/branch_test/build_index.py` (33 lines)
  - imports: argparse, json
  - functions: count_words_in_string, count_words_recursive, main
- `section_10_workspace/branch_test/lalalalalalala.py` (0 lines)
- `section_10_workspace/branch_test/scratch_demo.py` (2 lines)
  - functions: seven
- `section_10_workspace/branch_test/test_add_values.py` (13 lines)
  - imports: unittest, add_values
  - class `TestAddValues`: test_add_positive_integers, test_add_negative_and_positive
- `section_10_workspace/dictionary_tools/build_dictionary_index.py` (47 lines)
  - imports: argparse, json, sqlite3
  - functions: main
- `section_10_workspace/dictionary_tools/build_index.py` (77 lines)
  - imports: argparse, json, typing
  - functions: build_index, main
- `section_10_workspace/dictionary_tools/test_build_dictionary_index.py` (81 lines)
  - imports: json, sqlite3, subprocess, sys, tempfile, unittest, pathlib
  - class `BuildDictionaryIndexTests`: run_script, test_row_count_matches_fixture, test_table_columns, test_known_row_is_present, test_records_without_meanings_are_skipped
  - functions: expected_definition_count
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
- `section_10_workspace/smoke_project/main.py` (4 lines)
  - functions: add
- `section_10_workspace/smoke_project/test_main.py` (20 lines)
  - imports: unittest, main
  - class `TestAdd`: test_add_positive_numbers, test_add_negative_numbers, test_add_mixed_numbers, test_add_zero

### Documentation

- `section_10_workspace/scaffolds/memory_section/sources/readme.md`

### Other files

- `section_10_workspace/dictionary_tools/fixtures/sample_dictionary.json`
- `section_10_workspace/scaffolds/memory_section/scaffold.json`

## section_1_central_mind

Total files: 59  (.py: 51, .js/.ts: 0, .rs: 0, .md: 7, other: 1)

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
- `section_1_central_mind/mind/broker.py` (681 lines)
  - imports: __future__, importlib, importlib.util, sys, time, guard.contract, guard.effects, guard.resources
  - class `BoundToolBroker`: __init__, component_chain, call, available, with_workspace, __setattr__
  - class `ToolBroker`: __init__, _discover, bind_component, bind_central_mind, reset_budget, available, _call_bound, _finish
- `section_1_central_mind/mind/caller.py` (171 lines)
  - imports: __future__, typing, json
  - class `Caller`: __init__, call, route, _invoke_resource
- `section_1_central_mind/mind/capability_expansion.py` (6 lines)
  - imports: feature_expansion.loop
- `section_1_central_mind/mind/cognition.py` (137 lines)
  - imports: __future__, dataclasses, typing
  - class `CognitiveStep`: as_dict
  - class `CognitivePlan`: as_dict
  - class `Appraisal`: __post_init__, as_dict
- `section_1_central_mind/mind/composer.py` (58 lines)
  - imports: __future__, typing
  - class `Composer`: combine, _merge_outputs
- `section_1_central_mind/mind/consent.py` (52 lines)
  - imports: copy, secrets, threading, time
  - class `ConsentRequests`: __init__, offer, list, decide, _valid, approved
- `section_1_central_mind/mind/designer.py` (282 lines)
  - imports: __future__, ast, hashlib, threading, time, pathlib, typing
  - class `Designer`: __init__, _is_included, _hash_architecture, _parse_python, build, write, run_once, _watch_loop
- `section_1_central_mind/mind/feature_expansion/__init__.py` (3 lines)
  - imports: loop
- `section_1_central_mind/mind/feature_expansion/loop.py` (121 lines)
  - imports: __future__, dataclasses, hashlib, typing, time
  - class `CapabilityProposal`: as_dict
  - class `FeatureExpansionLoop`: __init__, propose_from_appraisal, proposals
- `section_1_central_mind/mind/intake_processing.py` (94 lines)
  - imports: __future__, hashlib, resource_socket
  - class `RawIntakeProcessor`: __init__, run
- `section_1_central_mind/mind/inventory.py` (187 lines)
  - imports: __future__, importlib.util, dataclasses, pathlib, typing
  - class `OrganInfo`: 
  - class `Inventory`: __init__, discover, all, get, by_keyword, by_capability, names, capability_catalog
- `section_1_central_mind/mind/learner.py` (88 lines)
  - imports: __future__, typing
  - class `Learner`: __init__, learn
- `section_1_central_mind/mind/loop.py` (3 lines)
  - imports: regular_operation.loop
- `section_1_central_mind/mind/organ.py` (99 lines)
  - imports: __future__, typing
  - class `Organ`: can_handle, handle, questions, verify, evaluate_knowledge, receive_proposal
- `section_1_central_mind/mind/proposals.py` (137 lines)
  - imports: __future__, time, uuid, dataclasses, typing
  - class `ProposalContractError`: 
  - class `Proposal`: __post_init__, as_dict
  - class `ProposalQueue`: __init__, append, get, list, record_audit, record_decision, _require
- `section_1_central_mind/mind/questioner.py` (3 lines)
  - imports: shared.questionnaire
- `section_1_central_mind/mind/reasoner/__init__.py` (9 lines)
  - imports: head
- `section_1_central_mind/mind/reasoner/consultation.py` (137 lines)
  - imports: __future__, typing
  - class `Consultation`: __init__, available, request
- `section_1_central_mind/mind/reasoner/discovery.py` (256 lines)
  - imports: __future__, typing
  - class `Discovery`: __init__, _component, validate_consultation, trusted_consultations, _subject_overlap, unresolved_material_needs
- `section_1_central_mind/mind/reasoner/head.py` (1235 lines)
  - imports: __future__, typing, cognition, state, understanding, discovery, consultation
  - class `Reasoner`: __init__, _recall, _memory_ids, _semantic_catalog, _semantic_proposal, _strings, _drop_format_leaks, _convert_execution_consultations
- `section_1_central_mind/mind/reasoner/state.py` (135 lines)
  - imports: __future__, dataclasses, typing
  - class `ReasoningEvidence`: as_dict
  - class `ReasoningState`: add_evidence, mark_consulted, can_continue, can_consult, begin_cycle, evidence_payload, as_dict
- `section_1_central_mind/mind/reasoner/understanding.py` (457 lines)
  - imports: __future__, json, typing
  - class `SemanticUnderstanding`: __init__, _string_list, _confidence, _strip_json_fence, _catalog, propose
- `section_1_central_mind/mind/regular_operation/__init__.py` (3 lines)
  - imports: loop
- `section_1_central_mind/mind/regular_operation/loop.py` (1620 lines)
  - imports: __future__, time, pathlib, typing, inventory, router, composer, shared.questionnaire
  - class `CentralMind`: __init__, _record_experience, run_self_assessment, process_pending_raw_intakes, process_raw_intake, _fulfill_domain_requirement, _receive_memory_proposal, _evaluate_memory_proposal
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
- `section_1_central_mind/mind/self_assessment/__init__.py` (3 lines)
  - imports: loop
- `section_1_central_mind/mind/self_assessment/loop.py` (115 lines)
  - imports: __future__, typing
  - class `SelfAssessmentLoop`: __init__, run
- `section_1_central_mind/mind/shared/__init__.py` (3 lines)
  - imports: questionnaire
- `section_1_central_mind/mind/shared/questionnaire.py` (31 lines)
  - imports: __future__, typing
  - class `Questionnaire`: __init__, ask
- `section_1_central_mind/mind/task_contract.py` (134 lines)
  - imports: __future__, copy, uuid, time
  - functions: task_contract, validate_task_contract, execution_receipt, attach_outcome, deterministic_report
- `section_1_central_mind/mind/verifier.py` (41 lines)
  - imports: __future__, typing
  - class `Verifier`: _valid_verdict, verify
- `section_1_central_mind/runtime_identity.py` (2 lines)
- `section_1_central_mind/server.py` (1465 lines)
  - imports: __future__, asyncio, json, os, sys, pathlib, typing, auth_service
  - class `AppChatbox`: __init__, ask, _emit, notify, present, tool_status
  - class `SessionRuntimes`: __init__, resolve, subscribe, unsubscribe, get_active_project, chat_context, set_active_project, forget
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

Total files: 10  (.py: 0, .js/.ts: 0, .rs: 0, .md: 10, other: 0)

### Documentation

- `section_2_constitution/authority.md`
- `section_2_constitution/coding.md`
- `section_2_constitution/core.md`
- `section_2_constitution/design.md`
- `section_2_constitution/design_actual.md`
- `section_2_constitution/image.md`
- `section_2_constitution/languages_learning_from_tests.md`
- `section_2_constitution/readme.md`
- `section_2_constitution/trading.md`
- `section_2_constitution/video.md`

## section_3_memory

Total files: 11  (.py: 10, .js/.ts: 0, .rs: 0, .md: 1, other: 0)

### Python modules

- `section_3_memory/__init__.py` (9 lines)
  - imports: api, entry
- `section_3_memory/api.py` (312 lines)
  - imports: __future__, json, re, time, pathlib, typing, , entry
  - class `Memory`: __init__, _load_sequences, _save_sequences, _next_seq, _new_raw_id, record, _record, get
- `section_3_memory/bridge.py` (269 lines)
  - imports: __future__, re, pathlib, typing, api
  - class `MemoryBridge`: __init__, recall, recall_tested, recall_rejections, get, remember_raw, remember_tested, remember_derived
- `section_3_memory/config.py` (101 lines)
  - imports: __future__, pathlib, os
  - functions: compute_score, compute_state
- `section_3_memory/entry.py` (194 lines)
  - imports: __future__, time, re, secrets, string, dataclasses, typing, 
  - class `Originator`: as_dict
  - class `Failure`: as_dict
  - class `CrossRef`: as_dict
  - class `Entry`: recompute_score, state, record_success, record_failure, as_dict, from_dict
  - functions: make_id, make_raw_id, parse_id
- `section_3_memory/index.py` (65 lines)
  - imports: __future__, typing, store
  - class `Index`: __init__, build, _add, _ensure, by_domain, by_tag, by_kind, by_class
- `section_3_memory/locking.py` (26 lines)
  - imports: contextlib, pathlib, threading
  - functions: memory_lock
- `section_3_memory/processing.py` (127 lines)
  - imports: contextlib, json, pathlib, sqlite3, time, uuid
  - class `ProcessingJournal`: __init__, connect, _event, enqueue, status, history, list, pending
- `section_3_memory/service.py` (779 lines)
  - imports: __future__, copy, json, os, tempfile, time, pathlib, typing
  - class `MemoryService`: __init__, _load_deletion_journal, _save_deletion_journal, _load_knowledge_journal, _save_knowledge_journal, _find_committed_entry, register_proposal_handler, _dispatch_knowledge_proposal
  - class `MemoryClient`: __init__, recall, recall_tested, recall_rejections, get, record_trainer_intake, propose_knowledge, propose_delete
  - functions: serialized_knowledge, serialized_intake
- `section_3_memory/store.py` (262 lines)
  - imports: __future__, json, re, shutil, threading, pathlib, typing, 
  - class `Store`: __init__, _class_directory, _validate_id, _path_for, _read_payload, _write_payload, _preserve_legacy_entries, _migrate_raw_payload

### Documentation

- `section_3_memory/readme.md`

## section_4_chatbox

Total files: 5  (.py: 5, .js/.ts: 0, .rs: 0, .md: 0, other: 0)

### Python modules

- `section_4_chatbox/__init__.py` (22 lines)
  - imports: chatbox, runtime, state
- `section_4_chatbox/chatbox.py` (126 lines)
  - imports: __future__, typing
  - class `Chatbox`: __init__, ask, render_for_review, notify, present, tool_status
- `section_4_chatbox/diagnostics.py` (31 lines)
  - functions: bounded, plan_summary, execution_summary
- `section_4_chatbox/runtime.py` (383 lines)
  - imports: __future__, pathlib, os, typing, state
  - class `ChatRuntime`: __init__, delete_chat, open_chat, retry_reply, _context_packet, _final_text, list_chats, load_chat
- `section_4_chatbox/state.py` (533 lines)
  - imports: __future__, json, time, uuid, hashlib, re, shutil, dataclasses
  - class `Turn`: 
  - class `Rejected`: 
  - class `Verified`: 
  - class `Chat`: __init__, _new_id, is_first_message, set_topic, check_topic, _words, _recent_text, model_messages
  - class `ChatStore`: __init__, _chat_path, delete, create, load, list_ids, latest

## section_5_domains

Total files: 70  (.py: 67, .js/.ts: 0, .rs: 0, .md: 2, other: 1)

### Python modules

- `section_5_domains/__init__.py` (6 lines)
- `section_5_domains/_image/__init__.py` (16 lines)
  - imports: base
  - class `ImageDomain`: capabilities, execute
- `section_5_domains/_image/__manifest__.py` (13 lines)
- `section_5_domains/_image/domain.py` (0 lines)
- `section_5_domains/_image/image_engine.py` (17 lines)
  - imports: mind.organ
  - class `ImageOrgan`: can_handle, handle
- `section_5_domains/_image/inspector.py` (0 lines)
- `section_5_domains/_image/tester.py` (0 lines)
- `section_5_domains/_image/verifier.py` (0 lines)
- `section_5_domains/_image/writer.py` (0 lines)
- `section_5_domains/_video/__init__.py` (16 lines)
  - imports: base
  - class `VideoDomain`: capabilities, execute
- `section_5_domains/_video/__manifest__.py` (13 lines)
- `section_5_domains/_video/domain.py` (0 lines)
- `section_5_domains/_video/inspector.py` (0 lines)
- `section_5_domains/_video/tester.py` (0 lines)
- `section_5_domains/_video/verifier.py` (0 lines)
- `section_5_domains/_video/video_engine.py` (17 lines)
  - imports: mind.organ
  - class `VideoOrgan`: can_handle, handle
- `section_5_domains/_video/writer.py` (0 lines)
- `section_5_domains/coding/__init__.py` (1 lines)
- `section_5_domains/coding/__manifest__.py` (88 lines)
- `section_5_domains/coding/acceptance.py` (65 lines)
  - imports: hashlib, json, re
  - functions: acceptance_module
- `section_5_domains/coding/classification/__init__.py` (3 lines)
  - imports: classifier
- `section_5_domains/coding/classification/classifier.py` (92 lines)
  - imports: __future__, cognition, typing
  - class `CodingClassifier`: classify
- `section_5_domains/coding/coding_engine.py` (729 lines)
  - imports: __future__, pathlib, typing, mind.organ, project_context, conventions, classification, inspection
  - class `CodingOrgan`: __init__, _for_caller, handle_intake_processing, evaluate_knowledge, verify, can_handle, open_project, close_project
  - functions: _assess_coding_result
- `section_5_domains/coding/cognition.py` (123 lines)
  - imports: __future__, ast, json
  - class `CodingCycle`: generate
  - functions: request_model, parse_object, resource_question
- `section_5_domains/coding/conventions.py` (67 lines)
  - imports: __future__, pathlib, typing
  - functions: module_under_test, conventional_test_path, plan_requirements_block, delegated_write_scope
- `section_5_domains/coding/debugger.py` (10 lines)
  - imports: cognition
  - class `Debugger`: diagnose
- `section_5_domains/coding/execution.py` (91 lines)
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
- `section_5_domains/coding/intake_examiner.py` (88 lines)
  - imports: ast, collections, hashlib, json, pathlib, re
  - class `CodingIntakeExaminer`: __init__, key, examine, evaluate
- `section_5_domains/coding/learning.py` (48 lines)
  - imports: hashlib, json, tester, re, pathlib
  - functions: _tested_modules, _covered_by_tests, verified_example
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
- `section_5_domains/coding/tester.py` (35 lines)
  - imports: __future__
  - class `Tester`: run, passed, unavailable
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
- `section_5_domains/general/__manifest__.py` (32 lines)
- `section_5_domains/general/general_engine.py` (95 lines)
  - imports: __future__, pathlib, typing, mind.organ
  - class `GeneralOrgan`: can_handle, handle, _chat_messages, handle_consultation
- `section_5_domains/languages/__manifest__.py` (59 lines)
- `section_5_domains/languages/languages_engine.py` (518 lines)
  - imports: __future__, json, re, pathlib, typing, mind.organ
  - class `LanguagesEngine`: __init__, _load_languages, known_natural, known_technical, handle, _planned_task, _objective_text, _ask
  - functions: language_name
- `section_5_domains/trading/__init__.py` (16 lines)
  - imports: base
  - class `TradingDomain`: capabilities, execute
- `section_5_domains/trading/__manifest__.py` (14 lines)
- `section_5_domains/trading/domain.py` (0 lines)
- `section_5_domains/trading/inspector.py` (0 lines)
- `section_5_domains/trading/tester.py` (0 lines)
- `section_5_domains/trading/trading_engine.py` (17 lines)
  - imports: mind.organ
  - class `TradingOrgan`: can_handle, handle
- `section_5_domains/trading/verifier.py` (0 lines)
- `section_5_domains/trading/writer.py` (0 lines)

### Documentation

- `section_5_domains/coding/rules.md`
- `section_5_domains/general/self_description.md`

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
- `section_7_models/model_router.py` (223 lines)
  - imports: __future__, json, re, pathlib, yaml, requests
  - class `ModelRouter`: __init__, _available, _candidates, fulfill, _debug_record, _fulfill, try_capability
  - functions: failure_code, _answer
- `section_7_models/providers/__init__.py` (1 lines)
- `section_7_models/providers/ollama.py` (65 lines)
  - imports: __future__, os, requests
  - class `OllamaProvider`: __init__, models, is_available, chat, generate
- `section_7_models/providers/openai_compatible.py` (46 lines)
  - imports: __future__, requests
  - class `OpenAICompatibleProvider`: __init__, chat, generate
- `section_7_models/resource_selector.py` (455 lines)
  - imports: __future__, dataclasses, typing
  - class `ResourceRequirement`: from_mapping
  - class `ResourceCandidate`: 
  - functions: _strings, _blob, _installed, _quality, _eligible, rank_resources

### Documentation

- `section_7_models/models_readme.md`

## section_8_tools

Total files: 32  (.py: 31, .js/.ts: 0, .rs: 0, .md: 1, other: 0)

### Python modules

- `section_8_tools/_base/__init__.py` (2 lines)
  - imports: tool
- `section_8_tools/_base/paths.py` (50 lines)
  - imports: __future__, pathlib
  - functions: missing_parent_directories
- `section_8_tools/_base/tool.py` (44 lines)
  - imports: __future__, pathlib, typing, guard.contract
  - class `Tool`: __init__, effects, call, _resolve
- `section_8_tools/audio/__init__.py` (0 lines)
- `section_8_tools/audio/__manifest__.py` (6 lines)
- `section_8_tools/audio/audio.py` (112 lines)
  - imports: base64, json, os, pathlib, subprocess, tempfile, yaml, _base.tool
  - class `AudioTranscribe`: configuration, effects, parse_reports, call
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
- `section_8_tools/intake/intake.py` (262 lines)
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
- `section_8_tools/terminal/python_tests.py` (249 lines)
  - imports: __future__, json, io, tarfile, time, os, pathlib, re
  - class `RunPythonTests`: _validate, effects, call
  - functions: runtime_image, docker_executable
- `section_8_tools/terminal/terminal.py` (213 lines)
  - imports: __future__, shlex, subprocess, pathlib, typing, _base.tool, guard.contract, python_tests
  - class `RunCommand`: effects, call
  - class `RunPythonCompile`: _validated_paths, effects, call
  - functions: _result
- `section_8_tools/vision/__init__.py` (2 lines)
  - imports: vision
- `section_8_tools/vision/__manifest__.py` (41 lines)
- `section_8_tools/vision/vision.py` (822 lines)
  - imports: __future__, base64, binascii, io, json, math, re, shutil
  - class `ImageDescribe`: effects, call
  - class `ImageReadText`: effects, call
  - class `PdfRead`: effects, call
  - class `DocumentRead`: _input, effects, call
  - class `VideoRead`: _input, effects, call
  - class `VideoExtractFrames`: effects, call
  - functions: _ffmpeg_executable, _ocr_image_bytes, _read_pdf_bytes, _read_docx_bytes, _read_pptx_bytes, _read_xlsx_bytes, read_document_bytes, read_video_bytes
- `section_8_tools/web/__init__.py` (2 lines)
  - imports: web
- `section_8_tools/web/__manifest__.py` (21 lines)
- `section_8_tools/web/browser.py` (128 lines)
  - imports: datetime, urllib.parse, _base.tool, guard.contract, url_policy
  - class `BrowserInteract`: validate, effects, call
  - functions: origin
- `section_8_tools/web/media.py` (109 lines)
  - imports: base64, urllib.parse, _base.tool, guard.contract, browser, url_policy
  - class `BrowserMedia`: approved, effects, call, fetch_media
- `section_8_tools/web/url_policy.py` (51 lines)
  - imports: json, os, pathlib, posixpath, urllib.parse
  - functions: policy_path, canonical, check_url
- `section_8_tools/web/web.py` (245 lines)
  - imports: __future__, re, html.parser, urllib.parse, url_policy, typing, _base.tool, guard.contract
  - class `_TextExtractor`: __init__, handle_starttag, handle_endtag, handle_data
  - class `WebSearch`: effects, call
  - class `WebFetch`: effects, call

### Documentation

- `section_8_tools/vision/README.md`

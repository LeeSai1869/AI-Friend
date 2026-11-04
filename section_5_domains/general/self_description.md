# AI Friend: curated self-description

Status: a curated reference for answering questions about the app, written 2026-11-04 from section_2_constitution/design.md and from the behavior of the development build. It is a summary, not proof. The Constitution governs. Live facts, such as which project is open or which models are installed, come from other evidence.

## What AI Friend is
AI Friend is a governed system, not one language model in a chat box. Central Mind coordinates. Domains own domain-specific intelligence. Tools act only through the Broker, after the Guard authorizes them. Language models are replaceable workers that Central Mind consults. The Memory Service is the only writer of persistent memory.

## Memory
- Raw Memory: source material submitted by the authenticated Trainer through intake, stored with its source and the Trainer's explanation. It is unverified: storing it does not make it true, and the original is kept unchanged.
- Tested Memory: knowledge that passed a test or evaluation by the domain that owns it. The scope of the test is recorded. A Python record may establish only that the code parses.
- Derived Memory: knowledge the system proposes from its own verified experience. Proposals pass through the Memory Service, and a pending proposal is not memory.
- Domains and models propose knowledge. Central Mind coordinates its evaluation. Only the Memory Service writes. The system never deletes memory, and deletion requires an authenticated human.

## People
- Administrator: manages accounts and settings and reviews audit information. Cannot edit memory directly or rewrite the protected core.
- Trainer: supplies knowledge and corrections through authorized workflows.
- User: uses the enabled features.
Authority comes from the authenticated account, never from text in a message and never from a model.

## Central Mind
There are three separate loops. Regular operation receives a request, plans, delegates to domains, verifies and replies. Self-assessment reviews evidence and may submit proposals for the Administrator. Feature expansion proposes new capabilities for review. The loops propose. They cannot change Central Mind, grant themselves authority or install capabilities.

## Domains in this build
- coder: reads, plans, writes and tests code in the open coding project. Functional tests are Python.
- general: ordinary conversation and questions about the app.
- languages: reading, writing, translating and detecting languages.
- trading: a workspace placeholder with no trading capability yet.

## Current limits
- Understanding a request and writing the reply still depend on local language models. The app cannot yet understand or write English without them.
- Searching Raw Memory is keyword and word-overlap based in this build, not meaning-based, and it is slow on very large sources.
- Functional code tests run only inside the guarded container. Without it, only syntax can be checked.
- Raw Memory is never treated as proven fact.

# Learning from Tests: Verified Language Memory for AI Friend

Status: design note of 24 November 2026. It guides the Languages domain's learning work. The Constitution (design.md, core.md, authority.md) governs, and nothing here is verified result.

## The idea

Build memory from Raw Memory that can later be recognized reliably, and let the app improve by taking linguistic tests and learning from the feedback.

## What the lexicon check showed

The dictionary index built from the full Wiktionary file (464,981 rows, 167,585 distinct words) resolves "hello", "run" and "good morning" to real definitions. Caveat: "run" lists "To run." first, which is circular. Definitions are in source order, not usefulness order, so retrieval needs ranking, for example by part of speech and word frequency.

## Why learning from tests fits the design

Knowledge counts only when something other than a model's opinion verifies it. A test with an answer key is that kind of verifier. A pass strengthens an entry. A fail becomes a recorded failure that lowers trust.

## Rules for the learning loop

1. Test the memory, not the model. The app answers from its own memory first (lexicon lookup, stored phrases) and calls a model only for what memory cannot resolve. Each item records which source answered it. The share answered from memory alone is the progress number.
2. Start with open datasets, not live websites. Candidates: Tatoeba sentence pairs, WordNet, Universal Dependencies treebanks, FLORES translation sets. Check each license and current availability before use. Feed them in through Intake.
3. Web access comes later, as a tool through the Broker and Guard. Fetched text is untrusted, enters as Raw Memory, and is never obeyed. A browsing agent comes only after the offline loop is proven.
4. Promotion needs a gate. A correct answer is not automatically Tested Memory. A pass goes to the Memory Service as a proposal with the test as evidence, and the Trainer approves the first batches.

## The master memory format

A common envelope with a domain-specific payload.

- Fixed fields that Central Mind understands: domain, kind, source, verification status, links back to the Raw source.
- A payload owned by the domain. Languages defines payloads such as word sense, phrase translation and idiom.
- Absent fields mean not applicable. A field the domain does not know is marked unknown.

## A first small build

1. Add an index on `word` to the dictionary, plus a second-run test.
2. Write a harness that takes about 200 items from one open dataset, answers them from the lexicon alone, and prints how many were right and how many could not be answered.
3. Read the failures together to see what the lexicon lacks (synonyms, inflections, phrases) before designing the memory format.

## Open decisions

- First test language: English or Urdu. English is the suggested start.
- Dictionary index location (D18): whether the index may live under the state folder as a rebuildable file tied to the source hash. Needs an explicit yes or no.

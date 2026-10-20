# Authority Rules

## The Administrator

- May inspect and search memory read-only.
- May review, approve, or reject permitted proposals.
- May create/manage ordinary accounts and configure public registration.
- May not directly edit or delete memory entries.
- May not rewrite Central Mind, the Constitution, authentication code,
  security guards, or protected core implementation.
- May not bypass audit or verification.

## The Trainer

- May submit training material and manage learning content through the
  Memory Service's authorized workflows.
- May correct memory and use explicitly permitted retirement,
  supersession, or deletion workflows.
- May not rewrite Central Mind, the Constitution, authentication code,
  security guards, or protected core implementation.
- May not bypass audit, verification, or the learning cycle.

## Ordinary Users

- May use permitted application features.
- May submit material only through workflows enabled for ordinary users.
- Do not receive privileged permissions from client-supplied role fields.

## Central Mind and Agents

- Are internal system components, not human accounts.
- May propose changes but cannot grant themselves authority.
- Must use trusted backend interfaces for decisions and memory operations.
- Cannot bypass guards, audit, or verification.

## Memory and History

- All memory access must pass through the standard Memory Service.
- No component may directly mutate memory storage.
- Proposals do not become accepted memory until an authorized decision
  succeeds.
- Deletion requests do not erase entries unless a separately authorized
  deletion workflow executes.
- Preserve provenance and history.

## Enforcement

The backend, not the frontend, enforces permissions on every operation.
Missing, invalid, or unverifiable authorization is denied.
The guards enforce protected boundaries independently of the mind.

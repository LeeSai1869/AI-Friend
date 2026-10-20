# Authority and Permissions

## 1. Human Accounts

The system has three human account roles:
- Administrator
- Trainer
- Ordinary user

Roles are assigned and enforced by trusted backend authentication and
authorization services. A client-supplied role, actor name, or approval
string is never proof of authority.

There is one designated Administrator account and one designated Trainer
account. Ordinary accounts are separate from these privileged accounts.

## 2. Administrator

The Administrator may:
- Inspect and search memory in read-only mode.
- Review, approve, or reject permitted proposals.
- Create and manage ordinary accounts.
- Configure whether ordinary-user self-registration is enabled.
- Manage permitted administrative settings and review audit history.

The Administrator may not directly edit or delete memory entries.
The Administrator may not rewrite Central Mind, the Constitution,
security guards, or protected core implementation.
The Administrator may not bypass verification or audit controls.

## 3. Trainer

The Trainer may:
- Submit knowledge and learning material.
- Correct and manage memory content through authorized Memory Service
  operations.
- Request or execute only those deletion workflows explicitly permitted
  by the Memory Service authorization policy.
- Provide training examples and review learning quality.

The Trainer may not rewrite Central Mind, the Constitution, security
guards, authentication code, or protected core implementation.
The Trainer may not bypass verification, audit, or learning-cycle rules.

## 4. Ordinary Users

Ordinary users may use permitted application features and submit material
only where the relevant workflow allows it. They do not receive
Administrator or Trainer privileges.

## 5. Central Mind and Internal Agents

Central Mind and its agents are system components, not human accounts.
They do not gain authority by supplying a role string or naming
themselves as an approver.

Internal decisions must pass through trusted backend interfaces and
applicable verification and audit controls. Agents may propose changes,
merges, supersession, retirement, or deletion, but may not grant
themselves human privileges.

## 6. Protected Core

Central Mind, authentication and authorization code, security guards,
and the Constitution are protected. Ordinary users, Trainers,
Administrators, and autonomous agents cannot directly rewrite these
protected components through normal application tools.

Changes to protected components require a separate explicitly authorized
maintenance process with verification and an auditable history.

## 7. Memory Service Boundary

All organs and domains access memory through the standard Memory Service.
No component may directly read or mutate memory storage outside that
boundary.

The service enforces authorization, validation, provenance, and history.
Pending proposals do not become accepted knowledge merely because they
were submitted or reviewed.

Deletion requests remain proposals until an explicitly authorized
workflow permits execution. History and audit records must be preserved.

## 8. Denial by Audit Layer

Authorization and verification fail closed. Missing, invalid, or
unverifiable authority is a denial, not permission.

The audit layer must record security-relevant denials and decisions.
Neither a human role nor an internal agent may bypass mandatory
verification.

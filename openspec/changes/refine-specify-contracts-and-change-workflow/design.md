## Context

The formal spec is the source of truth for current Contracts. Changes are independent work units that may be implemented in parallel and later synchronized into formal specs. A change needs enough context to explain its intent, but small fixes should not be forced into a large proposal/design template.

## Goals / Non-Goals

**Goals:**

- Make Contract references stable when titles or bodies change.
- Detect when a change's target Contract has moved since its delta was prepared.
- Keep formal specs focused on Contracts and keep change context with the change.
- Make synchronization repeatable and make archive a record-only step after sync.

**Non-Goals:**

- Use the Specify CLI to manage or validate its own implementation change.
- Add a database or a separate JSON store for Contract identity or sync baselines.
- Define automatic semantic conflict resolution; authors must revise a conflicting delta.

## Decisions

### Contract identity and formal format

- A formal spec has a `# contract` section and Contract headings in the form `## [<contract-id>] <title>`.
- The author chooses a short kebab-case ID when adding a Contract. It is unique within that spec and remains stable across title/body edits and renames.
- The full reference is `<type>:<spec-id>:<contract-id>`. The ID is explicit text, not a content hash.
- Delta headings carry the operation and ID, for example `## [MODIFIED] [password-login] Password login` and `## [RENAMED] [password-login] Old title -> New title`.
- `spec-index.md` lists formal spec types and IDs; change context and archived changes are not indexed.

### Spec type authoring templates

- Each `specTypes` entry may declare `template: template/<name>.md`, resolved relative to the project's `spec/` directory. `kinds` entries do not accept this field.
- Initialization installs the built-in requirement, capability, feature, component, architecture, and rule templates under `spec/template/`. Existing files are preserved so re-running initialization does not replace project edits.
- `specify create <type> <spec-id>` copies the configured Markdown template to the new `spec.md`; a type without a template gets the generic Contract skeleton.
- The templates provide practical writing structures such as WHEN/THEN/MUST for business requirements, responsibility sections for components, and a nested tree for architecture. Generic validation still checks Markdown structure, Contract IDs, and non-empty bodies; it does not claim to enforce all semantic guidance written in templates.
- The `arch` entry under `kinds` remains a change category. The formal architecture document is a separate `architecture` spec type with its own template.

### Contract body extraction and version hash

- A Contract body is the Markdown source after its `## [id] title` heading up to the next protocol-level `##` heading or the end of the `# contract` section. `###` headings are body content. Heading-like lines inside fenced code, blockquotes, and list-contained content do not delimit a Contract.
- To hash a body, normalize CRLF/CR to LF, remove only blank lines at the outer edges, preserve all other Markdown text and whitespace, then calculate SHA-256 over UTF-8 bytes.
- A delta records the current body hash in `meta-data.yaml` under `baseVersions`, keyed by the full Contract reference, for each modified, removed, or renamed Contract. An added Contract has no baseline.
- After drafting concrete operations, the author explicitly runs `specify change baseline <id>` to capture the current target bodies into `baseVersions`; this command can be run again after the author has reviewed a conflict and aligned the delta with the latest spec.
- Do not capture baselines when an empty change directory is created or implicitly during verify/sync. The explicit command makes the point at which the author accepts the current baseline visible.

### Sync and archive

- `sync` applies the current change's deltas to formal `specs/`. Before writing, it checks every recorded baseline and validates operation targets; any mismatch aborts without applying the change.
- On a baseline mismatch, the author reads the latest Contract, revises the delta to align with it, updates the baseline hash, and retries sync.
- After a successful sync, metadata records the applied delta hashes and time. Repeating sync with unchanged deltas is a no-op. A successful sync pins the delta contents; if a delta is edited afterward, its receipt is stale and sync/archive fail. Further semantic adjustments must be made in a follow-up change instead of reapplying an edited delta over its own prior result.
- A change with deltas may be archived only when its sync receipt matches the current deltas. Archive moves and records the change; it does not replay deltas. A change with no spec impact may be archived without a sync receipt.
- Baselines and sync receipts live in the change's YAML metadata. Formal Contract content remains in `specs/`; no database is introduced. Existing archival manifest behavior is retained unless a later change explicitly revises it.

### Change context document

- Use one `change.md` for the intent, context, and design rationale that would otherwise be split between proposal and design documents.
- `change.md` has no mandatory section list. Authors include only the information needed to understand and review the change; a small fix may use a short paragraph.
- This document belongs to the change and is never copied into formal specs or the spec index.

### Example fixture

- Keep `example_specs/` as a human-readable fixture covering formal specs, explicit Contract IDs, deltas, frozen baseline metadata, sync receipt, and archive examples.
- The example should illustrate the target protocol without implying that the CLI implementation already supports it.

## Risks / Trade-offs

- Markdown extraction depends on a precise distinction between protocol headings and nested or fenced content; the parser must follow the documented boundary rules consistently.
- Body hashes intentionally treat internal whitespace and Markdown formatting as content changes. This can require re-aligning a delta after editorial changes, but avoids silently ignoring meaningful source edits.
- Pinning deltas after sync means a follow-up correction needs a separate change. This keeps sync idempotent without storing pre-sync snapshots or adding a replay protocol.
- Atomic recovery if a process is interrupted while writing multiple formal specs is not defined here; keep sync preflighted and report this as an unresolved implementation concern rather than adding a journal protocol in this design iteration.
- Template prose improves consistency but cannot prove that a business requirement is semantically complete; machine-enforced content rules would require a later explicit validation profile.

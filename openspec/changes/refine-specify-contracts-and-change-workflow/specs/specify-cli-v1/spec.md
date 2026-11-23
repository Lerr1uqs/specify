## MODIFIED Requirements

### Requirement: Project initialization and scaffolding
The CLI SHALL initialize a target repository with validated `spec/config.yaml`, `specs/`, `template/`, `changes/{proposed,processing,implemented,rejected,archived}/`, and a deterministic empty index, and SHALL create formal spec and change skeletons. Each configured spec type MAY reference a Markdown authoring template relative to `spec/`; `specify create` SHALL copy that template as the new spec's initial content. Initialization SHALL install the built-in templates while preserving existing files. Templates guide authors but do not replace generic Markdown and Contract structure validation. A formal spec SHALL contain only a `# contract` section with Contract entries; change intent and design context SHALL stay in its change directory.

#### Scenario: Initialize with a valid config
- **WHEN** a user runs `specify init <path> --config <init.yaml>` with non-empty valid `specTypes` and `kinds`
- **THEN** the CLI creates the required directories, installs built-in Markdown templates under `spec/template/` without overwriting existing templates, and copies the validated configuration to `spec/config.yaml`

#### Scenario: Create a spec from its configured template
- **WHEN** a user runs `specify create <type> <spec-id>` for a configured type with a template path
- **THEN** the CLI copies that Markdown template into the new spec's `spec.md`

#### Scenario: Create a spec without a configured template
- **WHEN** a user runs `specify create <type> <spec-id>` for a configured type without a template path
- **THEN** the CLI creates the generic `# contract` skeleton with an unfinished `[<contract-id>] <title>` Contract placeholder

#### Scenario: Reject a missing configured template
- **WHEN** a configured type references a template that does not exist under `spec/`
- **THEN** `specify create` reports the missing template and does not create the spec

#### Scenario: Create a change context document
- **WHEN** a user creates a change
- **THEN** its directory contains one `change.md` for intent, context, and design rationale, with no mandatory section list, and the document is not copied into formal specs

### Requirement: Structured document parsing and Contract identity
The CLI SHALL parse protocol Markdown while ignoring heading-like content inside fenced code blocks, blockquotes, and list-contained content. Formal Contract headings SHALL use `## [<contract-id>] <title>`; each ID SHALL be kebab-case, unique within its spec, and stable across Contract title and body changes. A full Contract reference SHALL be `<type>:<spec-id>:<contract-id>`. Contract bodies SHALL extend from the Contract heading to the next protocol-level `##` heading or the end of the `# contract` section; `###` headings remain body content.

#### Scenario: Ignore non-protocol headings
- **WHEN** a formal spec contains protocol-looking headings inside a fenced code block, blockquote, or list-contained content
- **THEN** those lines remain Contract prose and do not create protocol sections or Contracts

#### Scenario: Preserve Contract identity across a rename
- **WHEN** a delta renames a Contract title
- **THEN** the Contract keeps its explicit ID and full reference, while normalized titles remain unique within the spec

#### Scenario: Extract a Contract body
- **WHEN** the parser reads a formal spec containing a Contract with nested `###` headings
- **THEN** the body includes those nested headings and ends only at the next protocol-level `##` heading or the end of the contract section

### Requirement: Spec and change validation
The CLI SHALL validate formal spec structure, unique Contract IDs and normalized titles, delta operation legality, metadata references, task numbering and completion rules, and rejected-change exceptions, returning a validation failure without mutating files. Contract body hashes SHALL be SHA-256 of UTF-8 bytes after normalizing line endings to LF and removing only blank lines at the outer edges; all remaining body text and whitespace SHALL be preserved. Change metadata SHALL store base versions by full Contract reference and sync receipts by delta path and content hash. After drafting concrete deltas, authors SHALL explicitly capture base versions with `specify change baseline <id>`; verify and sync SHALL never silently refresh them.

#### Scenario: Reject an invalid formal spec
- **WHEN** a spec has a missing or extra top-level section, duplicate Contract ID or title, forbidden `->` outside a rename heading, or empty Contract body
- **THEN** `specify validate --specs` reports the precise issue and exits with code 1

#### Scenario: Validate affect and delta agreement
- **WHEN** a change metadata entry declares a target but the matching delta is absent, extra, or uses an operation inconsistent with the target
- **THEN** `specify change verify <id>` reports the mismatch and exits with code 1

#### Scenario: Compute a stable Contract body hash
- **WHEN** the CLI hashes a Contract body whose source uses CRLF or CR line endings and outer blank lines
- **THEN** it normalizes line endings to LF, strips only outer blank lines, preserves internal text and whitespace, and hashes the resulting UTF-8 bytes with SHA-256

#### Scenario: Store a frozen baseline
- **WHEN** a change adds a concrete MODIFIED, REMOVED, or RENAMED delta for an existing Contract
- **THEN** `specify change baseline <id>` records that Contract's current body hash in `meta-data.yaml` under `baseVersions` keyed by `<type>:<spec-id>:<contract-id>`

#### Scenario: Refresh a reviewed baseline
- **WHEN** sync reports a stale Contract baseline and the author has reviewed the latest Contract and revised the delta
- **THEN** the author may run `specify change baseline <id>` again to explicitly capture the reviewed current body hash before retrying verification and sync

### Requirement: Change lifecycle
The CLI SHALL locate changes by globally unique ID, enforce valid state transitions, and support create, process, status, verify, implement, reject, remove, and confirmation-gated removal across the configured change tree. A change SHALL use one `change.md` for context that would otherwise be split between proposal and design; its sections are optional and proportionate to the change. Rejected changes SHALL preserve this context document and their deltas.

#### Scenario: Capture a requirement before planning
- **WHEN** a user runs `specify change create <kind> <id>` without declaring Spec impact
- **THEN** the CLI creates a proposed change with `change.md` starting at `## Requirement` and basic metadata

#### Scenario: Begin processing or migrate a legacy proposal
- **WHEN** a user runs `specify change process <id>` on a proposed change
- **THEN** it moves to `changes/processing/<kind>/<id>/`, creates a task skeleton when needed, and preserves any existing tasks, deltas, and baselines

#### Scenario: Mark a verified change implemented
- **WHEN** a processing change has complete tasks and passes deterministic verification
- **THEN** `specify change implement <id>` moves it to `changes/implemented/<kind>/<id>/`

#### Scenario: Reject with a reason
- **WHEN** a proposed or processing change is rejected with a supplied reason
- **THEN** the CLI moves it to `changes/rejected/<kind>/<id>/`, writes `rejectedReason`, and preserves `change.md` and its delta artifacts

#### Scenario: Track an implementation-only bug fix without changing formal specs
- **WHEN** a bug fix restores implementation behavior to an existing Contract and does not change externally visible Contract behavior
- **THEN** the change may contain a concise `change.md` and implementation tasks without adding or modifying a formal spec or delta

#### Scenario: Keep a small change concise
- **WHEN** a change is a small fix with no need for multiple context sections
- **THEN** its `change.md` may contain only a short explanation of the issue and intended result

### Requirement: Delta merge and synchronization
The CLI SHALL locate Contracts by explicit IDs, compare each modified, removed, or renamed Contract body against its frozen hash in change metadata, validate all operation targets and baselines before writing, then apply deltas in `RENAMED`, `MODIFIED`, `ADDED`, `REMOVED` order. Added Contracts SHALL have no base version and SHALL fail if the same ID or normalized title already exists. A successful sync SHALL record the applied delta content hashes and time in YAML metadata. Repeating sync with unchanged delta content SHALL be a no-op. If a baseline differs, sync SHALL stop without mutation; the author must align the delta with the current Contract, update the baseline, and retry. A successful sync pins the delta content; if a delta is edited afterward, sync and archive SHALL reject the stale receipt and the follow-up change SHALL be expressed as a new change.

#### Scenario: Rename then modify
- **WHEN** a delta contains a rename followed by a modification using the same Contract ID and new title
- **THEN** merge applies both operations to that Contract in the documented order

#### Scenario: Stop on a changed baseline
- **WHEN** a target Contract's current body hash differs from the change's recorded base version
- **THEN** sync reports the conflict and applies none of that change's deltas

#### Scenario: Retry after aligning a delta
- **WHEN** an author revises a conflicting delta to align with the latest Contract and updates its baseline hash
- **THEN** a subsequent sync validates the new baseline and applies the revised delta

#### Scenario: Repeat a completed sync
- **WHEN** `specify change sync <id>` is run again with the same delta hashes as the saved receipt
- **THEN** the second run is a no-op and leaves formal spec bytes unchanged

#### Scenario: Reject a delta edited after sync
- **WHEN** a delta's content hash differs from the saved sync receipt
- **THEN** sync and archive report a stale receipt without changing formal specs, and the adjustment must be made in a follow-up change

### Requirement: Index, listing, and inspection
The CLI SHALL list formal specs by optional type, show a requested `<type>:<spec-id>`, and build a deterministic `spec-index.md` from formal spec types and IDs only. Contract IDs SHALL be available in the formal spec content; change context and archived entries SHALL NOT be indexed.

#### Scenario: Rebuild the index deterministically
- **WHEN** `specify index build` runs repeatedly without source changes
- **THEN** each generated index has identical bytes and excludes changes and archived entries

### Requirement: Archive and frozen history validation
The CLI SHALL require a sync receipt matching the current delta hashes before archiving a change with spec-impacting deltas. Archive SHALL move the verified change without replaying its deltas, date-prefix the archived directory, append immutable manifest entries with SHA-256 file hashes, and detect missing, unregistered, or modified archived files. A change with no spec impact MAY be archived without a sync receipt.

#### Scenario: Archive a synced change
- **WHEN** an implemented change with deltas passes validation and its sync receipt matches its current delta hashes
- **THEN** its complete directory moves under `changes/archived/YYYY-MM-DD-<id>/` without writing formal specs again, and the manifest is appended deterministically

#### Scenario: Reject archive when sync is missing or stale
- **WHEN** an implemented change has deltas but no matching sync receipt
- **THEN** archive reports the missing or stale receipt and leaves formal specs and the change directory unchanged

#### Scenario: Archive a no-impact change
- **WHEN** an implemented change, such as an implementation-only bug fix, has no spec-impacting deltas
- **THEN** it may be archived without a sync receipt

#### Scenario: Detect archive tampering
- **WHEN** an archived file is modified, removed, or added without the corresponding manifest entry
- **THEN** `specify validate --archived` reports the mismatch and exits with code 1

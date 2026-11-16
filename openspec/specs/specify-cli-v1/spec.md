# specify-cli-v1 Specification

## Purpose
TBD - created by archiving change implement-specify-cli-v1. Update Purpose after archive.
## Requirements
### Requirement: Project initialization and scaffolding
The CLI SHALL initialize a target repository with validated `spec/config.yaml`, `specs/`, `changes/{proposed,implemented,rejected,archived}/`, and a deterministic empty index, and SHALL create fixed-format spec and change skeletons.

#### Scenario: Initialize with a valid config
- **WHEN** a user runs `specify init <path> --config <init.yaml>` with non-empty valid `specTypes` and `kinds`
- **THEN** the CLI creates the required directories and copies the validated configuration to `spec/config.yaml`

#### Scenario: Create a spec skeleton
- **WHEN** a user runs `specify create <type> <spec-id>` for a configured type
- **THEN** the CLI creates exactly one `spec.md` containing only a `# contract` section with an unfinished `[<contract-id>] <title>` Contract placeholder

### Requirement: Structured document parsing and Contract identity
The CLI SHALL parse specs, deltas, and tasks from Markdown outside fenced code blocks, reject malformed protocol sections, and identify each Contract by its explicit kebab-case ID within a spec.

#### Scenario: Ignore headings in a fenced block
- **WHEN** a spec contains `# contract` or `## title` inside a fenced code block
- **THEN** those lines remain Contract prose and do not create protocol sections

#### Scenario: Preserve Contract identity across a rename
- **WHEN** a delta renames a Contract title
- **THEN** the Contract keeps its explicit ID, while normalized titles remain unique within the spec

### Requirement: Spec and change validation
The CLI SHALL validate spec structure, unique Contract IDs and normalized titles, delta operation legality, metadata references, task numbering and completion rules, and rejected-change exceptions, returning a validation failure without mutating files.

#### Scenario: Reject an invalid formal spec
- **WHEN** a spec has a missing or extra top-level section, duplicate Contract title, forbidden `->`, or empty Contract body
- **THEN** `specify validate --specs` reports the precise issue and exits with code 1

#### Scenario: Validate affect and delta agreement
- **WHEN** a change metadata entry declares a target but the matching delta is absent, extra, or uses an operation inconsistent with the target
- **THEN** `specify change verify <id>` reports the mismatch and exits with code 1

### Requirement: Change lifecycle
The CLI SHALL locate changes by globally unique ID, enforce valid state transitions, and support create, status, verify, implement, reject, remove, and confirmation-gated removal across the configured change tree.

#### Scenario: Mark a verified change implemented
- **WHEN** a proposed change has complete tasks and passes deterministic verification
- **THEN** `specify change implement <id>` moves it to `changes/implemented/<kind>/<id>/`

#### Scenario: Reject with a reason
- **WHEN** a proposed change is rejected with a supplied reason
- **THEN** the CLI moves it to `changes/rejected/<kind>/<id>/`, writes `rejectedReason`, and preserves the proposal artifacts

### Requirement: Delta merge and synchronization
The CLI SHALL locate Contracts by their explicit IDs, compare changed or removed Contract bodies against the base hashes recorded in change metadata, apply deltas in `RENAMED`, `MODIFIED`, `ADDED`, `REMOVED` order, support whole-spec create/remove semantics, and record a receipt after successful sync.

#### Scenario: Rename then modify
- **WHEN** a delta contains a rename followed by a modification using the new title
- **THEN** merge applies both operations to the renamed Contract in the documented order

#### Scenario: Repeat a completed sync
- **WHEN** `specify change sync <id>` is run twice against the same change
- **THEN** the second run matches the saved receipt, is a no-op, and leaves the formal spec bytes unchanged

### Requirement: Index, listing, and inspection
The CLI SHALL list active changes with task progress by default, switch to formal specs with `--spec` and optional `--type`, show a requested `<type>:<spec-id>`, and build a deterministic `spec-index.md` from formal spec types and IDs only. List output SHALL be JSON by default; `--human` SHALL render the selected collection for people.

#### Scenario: List change progress for people
- **WHEN** an active change has 10 completed tasks out of 42 and the user runs `specify list --human`
- **THEN** the change row shows its ID, kind, lifecycle state, validation state, and `10/42` tasks

#### Scenario: Select formal specs
- **WHEN** the user runs `specify list --spec --human`
- **THEN** the table lists formal specs and does not represent their change tasks as spec tasks

#### Scenario: Rebuild the index deterministically
- **WHEN** `specify index build` runs repeatedly without source changes
- **THEN** each generated index has identical bytes and excludes changes and archived entries

### Requirement: Archive and frozen history validation
The CLI SHALL require a matching sync receipt for a change with deltas, archive the verified change without replaying its deltas, date-prefix the archived directory, append immutable manifest entries with SHA-256 file hashes, and detect missing, unregistered, or modified archived files.

#### Scenario: Archive a completed change
- **WHEN** an implemented change passes validation and is archived
- **THEN** its complete directory moves under `changes/archived/YYYY-MM-DD-<id>/` without writing formal specs again, and the manifest is appended deterministically

#### Scenario: Detect archive tampering
- **WHEN** an archived file is modified, removed, or added without the corresponding manifest entry
- **THEN** `specify validate --archived` reports the mismatch and exits with code 1

### Requirement: CLI output and failure contract
The CLI SHALL provide human-readable output by default, optional machine-readable JSON reports, and exit codes 0 for success, 1 for content validation failure, 2 for usage errors, and 3 for environment or IO failures.

#### Scenario: Emit a JSON validation report
- **WHEN** a user runs a validation command with `--json`
- **THEN** stdout contains a stable JSON object describing success or every validation issue without human formatting

#### Scenario: Report a missing project configuration
- **WHEN** a project command runs without `spec/config.yaml`
- **THEN** the CLI reports an environment error and exits with code 3


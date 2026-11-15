## Context

The repository has a written V1 protocol under `plan/`, but no runtime implementation. The CLI must operate on a local directory tree, preserve human-authored Markdown and YAML semantics, expose deterministic machine-checkable results, and remain small enough to install as a normal Python package.

## Goals / Non-Goals

**Goals:**

- Provide the complete V1 command surface described by the implementation plan.
- Parse fenced Markdown structurally, derive stable Contract hashes, and validate all protocol invariants.
- Make change synchronization and archive operations repeatable and auditable.
- Keep CLI presentation separate from domain logic so parsers, validators, merge behavior, and lifecycle transitions are directly testable.

**Non-Goals:**

- Automatic merging of concurrent changes that target the same Contract.
- Remote storage, daemon processes, database state, or an agent integration API.
- Inferring whether an implementation matches business intent; `verify` only performs deterministic checks.

## Decisions

1. **Use a `src/` Python package with Click.** `pyproject.toml` exposes `specify`, while `cli.py` only translates command arguments and domain results into human or JSON output. Click is sufficient for the small, fixed command tree and keeps command errors predictable.

2. **Use markdown-it-py token streams and ruamel.yaml.** Heading boundaries are detected from Markdown tokens, so headings in fenced code are never mistaken for protocol sections. YAML round-trip loading preserves key order and gives structured unknown-field validation. A small fallback-friendly error layer maps parse, validation, and IO failures to the documented exit codes.

3. **Use immutable in-memory models for parse and merge.** `SpecDoc`, `Contract`, and delta models carry source-independent values. `merge.apply` executes `RENAMED`, `MODIFIED`, `ADDED`, `REMOVED` in that fixed order and serializes a canonical Markdown document. Replaying a delta therefore yields the same bytes without marker files.

4. **Resolve identities from paths, not metadata status.** `paths.py` scans the state directories, strips archive date prefixes only for comparison, rejects duplicate IDs, and validates the metadata/path kind relationship. Lifecycle commands move directories atomically within the same `changes/` tree.

5. **Treat archive integrity as a manifest contract.** Archiving first validates and applies deltas, then moves the complete change under a date-prefixed directory and appends sorted file hashes to `changes/archived/manifest.json`. Archived validation compares the manifest with disk in all three directions and never rewrites old entries.

6. **Keep generated output deterministic.** Index sections, spec listings, JSON reports, and manifest entries use stable sorting and normalized line endings. Writes use temporary sibling files followed by replacement so an interrupted generation does not leave a partial target.

## Risks / Trade-offs

- **[Risk] Markdown formatting authored outside the protocol may not round-trip byte-for-byte.** → The parser keeps contract prose and headings, emits canonical protocol Markdown, and tests semantic/idempotent output rather than preserving arbitrary formatting.
- **[Risk] YAML library availability can prevent installation.** → Dependencies are declared in `pyproject.toml`; startup reports a concise environment error and tests install the declared runtime dependencies.
- **[Risk] A later change can overwrite a Contract changed by an earlier change.** → V1 deliberately rejects automatic parallel merging; validation and merge report conflicts, while the deferred policy remains documented in `plan/todo/`.
- **[Risk] Moving a change can cross filesystem boundaries in unusual layouts.** → Lifecycle paths remain below one repository root and use rename operations; failures map to exit code 3 without deleting the source.

## Migration Plan

There is no existing executable package or runtime data to migrate. Installing the package and running `specify init` creates a new `spec/` tree; existing plan documents remain usable as the protocol reference. Rollback is uninstalling the package and manually removing only a newly initialized project tree, with CLI destructive removal requiring confirmation.

## Open Questions

- The exact machine-readable JSON report schema is intentionally minimal in V1 and will be stabilized by the tests and command consumers.
- The default type and kind labels follow the examples in `plan/format/config.yaml.md`; projects can replace them during initialization.

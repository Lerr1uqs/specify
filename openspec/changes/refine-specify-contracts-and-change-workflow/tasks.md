## 1. Formal Contract format and parsing

- [x] 1.1 Update spec and delta formats to require explicit kebab-case Contract IDs and stable full references.
- [x] 1.2 Define and implement Markdown Contract-body boundaries, including fenced, blockquote, list-contained, and nested headings.
- [x] 1.3 Implement the documented normalized-body SHA-256 algorithm and validation for duplicate IDs and titles.

## 2. Change context and metadata

- [x] 2.1 Replace target change `proposal.md` and `design.md` with a single `change.md` whose sections are optional and proportionate to the change.
- [x] 2.2 Define `meta-data.yaml` fields for base versions keyed by full Contract reference and for successful sync receipts keyed by delta path and content hash.
- [x] 2.3 Update change creation, validation, rejection, and examples to preserve `change.md` and the new metadata contract.

## 3. Synchronization and archive

- [x] 3.1 Add an explicit baseline-capture command for drafted MODIFIED, REMOVED, and RENAMED deltas; do not assign a baseline to ADDED Contracts or capture implicitly during verify/sync.
- [x] 3.2 Preflight all delta targets and base hashes before mutating formal specs, then apply operations in the specified order.
- [x] 3.3 Record sync receipts, make repeat sync a no-op for unchanged delta content, and reject stale baselines or post-sync delta edits without partial application.
- [x] 3.4 Require a current receipt when archiving changes with spec-impacting deltas, and ensure archive does not reapply deltas.

## 4. Index and examples

- [x] 4.1 Keep the formal spec index limited to formal spec types and IDs; exclude change context and archived changes.
- [x] 4.2 Update `example_specs/` to show the merged `change.md`, explicit Contract IDs, frozen baselines, sync receipt, and archive behavior.
- [x] 4.3 Document the unresolved multi-file write-interruption recovery question without adding a journal protocol in this change.

## 5. CLI regression coverage

- [x] 5.1 Cover every CLI action, valid and invalid lifecycle transition, multi-target baseline conflict rejection, stale post-sync delta rejection, and archive without delta replay.

## 6. Spec type authoring templates

- [x] 6.1 Add template paths to spec type configuration, install built-in templates during init, and preserve customized template files.
- [x] 6.2 Make `specify create` copy the configured template and document template guidance versus structural validation.
- [x] 6.3 Add CLI regression coverage for initialized templates and type-specific template selection.

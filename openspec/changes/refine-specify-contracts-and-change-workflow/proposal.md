## Why

The current design needs a clear contract identity and synchronization protocol so multiple implemented changes can coexist without silently overwriting each other. It also needs a lighter change-document format and a clear boundary between formal contracts, change context, and synchronization metadata.

## What Changes

- Formal specs contain only Contracts; proposal/design context stays with its change and does not propagate into `spec-index.md`.
- Give each Contract an explicit, stable kebab-case ID, forming the reference `<type>:<spec-id>:<contract-id>`.
- Define Markdown Contract-body extraction, body hashing, frozen baselines in change YAML, conflict handling during sync, and archive behavior.
- Combine proposal and design context into `change.md` without mandatory sections; document only what a change needs.
- Provide a representative `example_specs/` fixture for reviewing the file formats and workflow.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `specify-cli-v1`: clarify formal spec shape, Contract identity, change artifacts and metadata, delta synchronization, and archive lifecycle.

## Impact

This change updates and implements the Specify CLI contract workflow in Python, including its example files and CLI-level regression coverage. OpenSpec remains the workflow managing this change; Specify will not manage its own implementation change.

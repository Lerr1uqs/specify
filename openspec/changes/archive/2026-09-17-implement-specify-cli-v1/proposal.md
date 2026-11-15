## Why

The repository currently contains a detailed protocol and implementation plan for a custom Specify CLI, but no executable package. Without an implementation, projects cannot initialize the layout, validate specs and changes, or safely merge and archive contract updates. This change turns the agreed V1 protocol into a usable, tested Python CLI.

## What Changes

- Add a Python 3.11+ package with a `specify` console entry point.
- Implement config loading, project/spec/change scaffolding, Markdown and YAML parsing, contract hashing, and deterministic index generation.
- Implement spec, change, task, and archived-manifest validation with documented exit codes and optional JSON reports.
- Implement change lookup and lifecycle transitions: create, status, verify, implement, reject, remove, sync, and archive.
- Implement ordered, idempotent delta application for added, modified, removed, and renamed Contracts.
- Add focused unit and integration tests covering the protocol rules and end-to-end lifecycle.

## Capabilities

### New Capabilities

- `specify-cli-v1`: Initialize, inspect, validate, update, and archive a contract-based spec repository through a deterministic command-line interface.

### Modified Capabilities

None. The repository has no existing OpenSpec capabilities; the `plan/` documents are the source protocol for this new capability.

## Impact

This adds `pyproject.toml`, `src/specify/`, tests, and the OpenSpec change artifacts. Runtime dependencies are limited to `click`, `markdown-it-py`, and `ruamel.yaml`; the CLI writes only within the target spec repository, including its `spec/` and `changes/` trees. Existing design documents remain unchanged and are treated as the implementation contract.

## 1. Package and core models

- [x] 1.1 Add `pyproject.toml`, the `src/specify/` package, console entry point, runtime dependencies, and a typed error/exit-code layer.
- [x] 1.2 Implement repository paths, config loading, atomic text/JSON writes, and deterministic project scaffolding.
- [x] 1.3 Implement Contract normalization, SHA-256 identity, and in-memory spec/delta/task models with function and key-logic comments.

## 2. Parsers and validators

- [x] 2.1 Implement fenced-Markdown-aware document, formal spec, delta, and task parsers with protocol errors.
- [x] 2.2 Implement formal spec and change validators, including metadata/path rules, affects/delta agreement, rejected exceptions, and task checks.
- [x] 2.3 Implement archived manifest generation and three-way frozen-history validation.

## 3. Merge, index, and archive services

- [x] 3.1 Implement ordered idempotent delta merge for add, modify, remove, and rename operations.
- [x] 3.2 Implement deterministic formal-spec index generation, list/show helpers, and sync behavior.
- [x] 3.3 Implement change lookup, lifecycle transitions, archive movement, and append-only manifest updates.

## 4. CLI and verification

- [x] 4.1 Implement the Click command tree, human/JSON output, usage handling, and documented exit codes.
- [x] 4.2 Add parser, hash, merge, lifecycle, archive, and CLI integration tests covering happy and invalid paths.
- [x] 4.3 Run the complete test suite and manual end-to-end smoke flow, then mark all OpenSpec tasks complete.

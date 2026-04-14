# CLAUDE.md

This repository is used for IMC trading research and experiments.

## Scope

- Keep changes small and reviewable.
- Prefer deterministic scripts over ad-hoc notebook edits when logic becomes reusable.
- Do not commit credentials, tokens, or local environment files.

## Python Conventions

- Target Python 3.10+.
- Prefer clear, typed functions for strategy logic.
- Keep strategy code side-effect-light and separate from I/O.
- Use small helper modules instead of very large single-file traders.

## Data and Outputs

- Treat datasets and generated backtest outputs as local artifacts unless explicitly required.
- Avoid committing large generated files (plots, logs, checkpoints, temporary reports).
- Keep reproducible scripts under version control; keep generated outputs ignored.

## Repo Hygiene

- Respect `.gitignore` and avoid force-adding ignored files.
- Keep top-level clutter low; place new work in clearly named subfolders.
- Remove dead experimental files once superseded by documented alternatives.

## Before Committing

- Run relevant tests/backtests for touched code.
- Confirm no secrets or local paths are present.
- Keep commit messages specific about strategy/risk/execution impact.

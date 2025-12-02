# Repository Guidelines

## Project Structure & Module Organization
- Python package code belongs in `src/mc_ledger_stats/` (core ledger/statistics logic) with small, focused modules; avoid sprawling utility grab-bags.
- Tests live in `tests/` mirroring the package layout (`tests/<module>/test_<feature>.py`); keep fixtures in `tests/conftest.py` or `tests/fixtures/`.
- CLI or automation scripts go in `scripts/` with executable bits set (`chmod +x`) and minimal dependencies.
- Large or generated assets (data exports, cache files) should be kept out of version control; prefer documenting required inputs in `README` or `docs/`.

## Build, Test, and Development Commands
- Create a virtual environment and install dev deps: `python -m venv .venv && source .venv/bin/activate && python -m pip install -e .[dev]`.
- Run the suite: `pytest` (fast feedback), and for coverage: `pytest --cov=mc_ledger_stats --cov-report=term-missing`.
- Static checks and formatting: `ruff check .` then `ruff format .` to keep import order and style consistent.
- Local package sanity: `python -m pip install .` to ensure packaging metadata stays valid.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indents and type hints on public functions/classes; prefer `from __future__ import annotations` in new modules.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and `SCREAMING_SNAKE_CASE` for constants; modules should use short, descriptive snake_case names.
- Keep functions small and pure where possible; centralize I/O and environment access near entrypoints to simplify testing.
- Add concise docstrings for public APIs describing inputs, outputs, and side effects; prefer dataclasses or typed dicts for structured data over loose dicts.

## Testing Guidelines
- Use `pytest` with test files named `test_*.py`; co-locate tests with the module under test and favor fixture reuse over repeated setup.
- Mark long-running or integration-heavy tests (`@pytest.mark.slow`) so they can be skipped in quick runs.
- Aim to cover branches around ledger calculations and data validation paths; include regression tests when fixing bugs.
- When adding new CLI/script behavior, test both happy-path and failure-path (bad config, missing files) cases.

## Commit & Pull Request Guidelines
- Write imperative, concise commit messages (`Add ledger summary CLI`) and group related changes together; avoid mixing refactors with behavior changes.
- Reference issues where applicable (`Fix: handle null amounts (#123)`) and describe observable effects in the body.
- PRs should include a short summary, testing notes (`pytest`, `ruff check` results), and any relevant screenshots/log excerpts for user-facing changes.
- Keep diffs focused; if a refactor is required to land a feature, land it in a preparatory commit/PR to ease review.

## Security & Configuration Tips
- Never commit secrets or live credentials; use environment variables and document expected keys in `.env.example`.
- Validate external inputs early (file paths, numeric ranges, encodings) and sanitize any output intended for logs or downstream systems.
- When handling ledger data, redact personally identifiable information in fixtures and test data.

# Wwise Batch Container Builder

Python desktop tool using:

- WAAPI
- PySide6
- pytest

## Architecture

```text
main.py
  -> src/ui/main_window.py
  -> src/grouping.py
  -> src/planning.py
  -> src/executor.py
  -> src/wwise/
```

## Development rules

- Keep grouping logic independent from WAAPI.
- `grouping.py` must not modify Wwise.
- `planning.py` produces an execution plan.
- `executor.py` is the only layer that performs Wwise mutations.
- Add tests for grouping/planning changes.
- Do not modify existing WAAPI behavior without checking tests.

## Tests

Run:

```text
pytest
```

## Coding style

- Prefer small functions.
- Use type hints.
- Keep UI logic separate from business logic.

---
phase: 04-postflop-decisions
plan: 03
subsystem: testing
tags: [gap-closure, test-fix, postflop, EHS, pot-odds]
dependency_graph:
  requires: [04-02]
  provides: [clean-test-suite]
  affects: [tests/test_bot_safety.py]
tech_stack:
  added: []
  patterns: [_ehs-mock-for-determinism, make_card-for-valid-treys-encoding]
key_files:
  modified:
    - tests/test_bot_safety.py
decisions:
  - Used EHS mock lambdas for deterministic postflop test behavior
  - Chose call_amount=50 with EHS=0.70 for call test (req_eq=0.625)
  - Chose call_amount=300 with EHS=0.20 for fold test (req_eq=0.909)
  - Used EHS=0.30 for check-when-free test (weak hand, below all bet thresholds)
metrics:
  duration: 285s
  completed: 2026-04-11T12:58:58Z
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 04 Plan 03: Fix Stale test_bot_safety.py Tests Summary

Replaced stale tight-passive postflop tests with EHS-driven pot-odds tests using mocked _ehs and valid treys-encoded board cards for deterministic behavior.

## What Was Done

### Task 1: Replace stale tight-passive tests with EHS-driven postflop tests

Rewrote three tests in `tests/test_bot_safety.py` that used invalid treys card constants (`0x00010000`, `0x00020000`, `0x00040000`) and tested the removed tight-passive fallback logic. The new tests exercise the Phase 4 EHS-driven `_facing_bet()` and `_bet_or_check()` postflop decision engine via mocked `_ehs` for full determinism.

**Changes made:**

1. **`test_d01_call_when_cheap` -> `test_postflop_calls_when_ehs_above_req_eq`**: Tests POST-07 pot-odds calling. Valid flop board (4d, 9s, Qc via `make_card`), call_amount=50, EHS=0.70 mocked. req_eq = 50/(30+50) = 0.625. EHS 0.70 >= 0.625 -> call.

2. **`test_d01_fold_when_expensive` -> `test_postflop_folds_when_ehs_below_req_eq`**: Tests POST-07 pot-odds folding. Same valid flop board, call_amount=300, EHS=0.20 mocked. req_eq = 300/(30+300) = 0.909. EHS 0.20 < 0.909 -> fold.

3. **`test_d03_check_when_free`**: Updated to use valid board cards and mocked EHS=0.30. With call_amount=0, routes to `_bet_or_check()`, where weak EHS with no aggressor flag produces check (returned as `("call", 0)`).

4. **Section comment**: Updated from `D-01: Tight-passive call/fold logic` to `POST-07: Pot odds call/fold (EHS-driven postflop)`.

5. **`__main__` runner**: Updated test function references to match new names.

**Commit:** `f8328a0`

## Verification Results

- `python -m pytest tests/test_bot_safety.py -v`: 13/13 passed
- `python -m pytest tests/ -v`: 181/181 passed (full suite)
- Zero occurrences of `0x00010000`, `0x00020000`, `0x00040000` in test_bot_safety.py
- `test_postflop_calls_when_ehs_above_req_eq` appears 2 times (def + runner)
- `test_postflop_folds_when_ehs_below_req_eq` appears 2 times (def + runner)
- `_ehs.*=.*lambda` appears 3 times (one per fixed test)
- Zero occurrences of "tight-passive" in section comments

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | f8328a0 | Replace stale tight-passive tests with EHS-driven postflop tests |

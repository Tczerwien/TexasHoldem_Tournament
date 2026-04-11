---
phase: 04-postflop-decisions
plan: 02
subsystem: postflop-routing
tags: [postflop, routing, integration-tests, decide]
dependency_graph:
  requires: [04-01]
  provides: [postflop-routing-wired]
  affects: [players/mtt_bot.py, tests/test_postflop_decisions.py]
tech_stack:
  added: []
  patterns: [integration-test-pipeline, mock-ehs-for-determinism]
key_files:
  created: []
  modified:
    - players/mtt_bot.py
    - tests/test_postflop_decisions.py
decisions:
  - "Replaced tight-passive fallback with single _postflop() call -- no conditional logic needed"
  - "Added small blind to make_gs test helper to support preflop regression test"
metrics:
  duration: 115s
  completed: "2026-04-10"
  tasks_completed: 1
  tasks_total: 1
  tests_added: 4
  tests_total: 34
  test_suite_total: 181
---

# Phase 04 Plan 02: Wire _decide to _postflop and Integration Tests Summary

Wire postflop decision engine into _decide() routing, replacing tight-passive fallback with _postflop() call, verified by 4 integration tests proving the full pipeline works end-to-end.

## What Was Done

### Task 1: Wire _decide() to _postflop() and add integration tests

**Part A -- _decide() modification (players/mtt_bot.py):**
- Replaced the tight-passive fallback (lines 583-591) with `return self._postflop(game_state, est_pot)`
- Updated docstring from "postflop fallback" to "postflop decision engine"
- Changed design reference from D-11 to D-10
- Removed the "Phase 3/4 will add postflop logic" comment
- Net change: 6 lines of fallback logic replaced with 1 line of routing

**Part B -- Integration tests (tests/test_postflop_decisions.py):**
- Added `TestDecidePostflopRouting` class with 4 tests proving full pipeline:
  1. `test_decide_routes_to_postflop` -- aggressor c-bets on DRY flop via _postflop
  2. `test_decide_postflop_fold` -- folds when EHS far below required equity
  3. `test_decide_postflop_call` -- calls when EHS above pot odds but below MONSTER
  4. `test_decide_preflop_unchanged` -- regression test confirming preflop routing intact

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added small blind to make_gs test helper**
- **Found during:** Task 1, preflop regression test
- **Issue:** `make_gs()` only included `blinds.big` but `_detect_situation()` also reads `blinds.small`, causing KeyError when _decide routes to _preflop
- **Fix:** Added `"small": big_blind // 2` to the blinds dict in `make_gs()`
- **Files modified:** tests/test_postflop_decisions.py
- **Commit:** 4e55690

## Verification Results

- `python -m pytest tests/test_postflop_decisions.py -x -q` -- 34 passed (30 unit + 4 integration)
- `python -m pytest tests/ -x -q` -- 181 passed, zero regressions
- `grep "_postflop(game_state, est_pot)" players/mtt_bot.py` -- routing confirmed wired
- `grep -c "tight-passive" players/mtt_bot.py` -- 1 occurrence (class docstring only, not in _decide)
- All 4 integration test names present in test file

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 4e55690 | feat(04-02): wire _decide to _postflop and add integration tests |

## Key Pipeline Path (Proven by Tests)

```
get_action() -> _decide() -> _postflop() -> _ehs() + _classify_board()
                                          -> _facing_bet() or _bet_or_check()
                                          -> _guard() -> (action, amount)
```

All postflop decisions now flow through the EHS-driven postflop decision engine. The tight-passive fallback has been fully replaced. Phase 4 is complete.

## Self-Check: PASSED

- [x] players/mtt_bot.py exists
- [x] tests/test_postflop_decisions.py exists
- [x] 04-02-SUMMARY.md exists
- [x] Commit 4e55690 exists in git log

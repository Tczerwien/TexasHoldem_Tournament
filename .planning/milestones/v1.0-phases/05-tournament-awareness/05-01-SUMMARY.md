---
phase: 05-tournament-awareness
plan: 01
subsystem: tournament-awareness
tags: [tdd, tournament-stage, stack-role, classification]
dependency_graph:
  requires: []
  provides: [_get_tournament_stage, _get_stack_role, _initial_table_players]
  affects: [05-02]
tech_stack:
  added: []
  patterns: [player-count-priority-stage-detection, chip-conservation-avg-estimation]
key_files:
  created:
    - tests/test_tournament.py
  modified:
    - players/mtt_bot.py
decisions:
  - "Player count takes absolute priority over blind level for stage detection (heads_up/itm/bubble checked before blinds)"
  - "Stack role uses _initial_table_players * 1500 for total chips, estimating avg from active_players"
metrics:
  duration: "~2 minutes"
  completed: "2026-04-12T02:36:24Z"
  tasks_completed: 1
  tasks_total: 1
  tests_added: 15
  tests_total: 196
---

# Phase 5 Plan 01: Tournament Stage & Stack Role Summary

TDD implementation of _get_tournament_stage (6 stages from active_players + blinds) and _get_stack_role (big/medium/short via chip-conservation average estimation) with 15 unit tests covering all classification boundaries.

## What Was Done

### Task 1: TDD stage detection and stack role methods

**RED phase** (commit f5538f2):
- Created `tests/test_tournament.py` with mock engine pattern
- TestStageDetection: 9 tests covering heads_up, itm, bubble, early, middle, late, boundaries, and player-count-overrides-blinds
- TestStackRole: 6 tests covering big, short, medium, boundary values, and _initial_table_players usage
- All 15 tests failed as expected (methods did not exist)

**GREEN phase** (commit bd39fed):
- Added `_initial_table_players = 0` to `__init__` (line 462)
- Added `self._initial_table_players = game_state["active_players"]` to sentinel block in `_detect_new_hand` (line 533)
- Added `_get_tournament_stage(self, game_state)` under new "PHASE 5: TOURNAMENT AWARENESS" section (line 627):
  - n <= 2: "heads_up", n <= 3: "itm", n <= 4: "bubble"
  - bb <= 30: "early", bb <= 100: "middle", else: "late"
- Added `_get_stack_role(self, game_state)` (line 649):
  - total_chips = _initial_table_players * 1500
  - avg = total_chips / active_players
  - >= 1.5x avg: "big", <= 0.5x avg: "short", else: "medium"
- All 15 new tests pass, 196 total regression green

**REFACTOR phase**: No changes needed -- docstrings with TOURN-01 and TOURN-03 requirement IDs were included in GREEN phase.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| f5538f2 | test | Add failing tests for tournament stage and stack role |
| bd39fed | feat | Implement tournament stage detection and stack role classification |

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| _get_tournament_stage defined in mtt_bot.py | PASS (1 match) |
| _get_stack_role defined in mtt_bot.py | PASS (1 match) |
| _initial_table_players in 3+ locations | PASS (4 matches: __init__, _detect_new_hand, _get_stack_role, comment) |
| TOURN-01 in mtt_bot.py docstring | PASS |
| TOURN-03 in mtt_bot.py docstring | PASS |
| heads_up in mtt_bot.py | PASS |
| bubble in mtt_bot.py | PASS |
| TestStageDetection in tests | PASS |
| TestStackRole in tests | PASS |
| pytest tests/test_tournament.py exits 0 | PASS (15 passed) |
| pytest tests/ exits 0 (regression) | PASS (196 passed) |

## Deviations from Plan

None -- plan executed exactly as written.

## Self-Check: PASSED

- [x] tests/test_tournament.py exists
- [x] players/mtt_bot.py exists
- [x] 05-01-SUMMARY.md exists
- [x] Commit f5538f2 found
- [x] Commit bd39fed found

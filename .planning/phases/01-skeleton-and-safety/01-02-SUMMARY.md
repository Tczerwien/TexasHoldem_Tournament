---
phase: 01-skeleton-and-safety
plan: 02
subsystem: core
tags: [poker-bot, state-tracking, pot-accumulator, hand-detection]

# Dependency graph
requires:
  - "01-01: HawkEyeBot skeleton with safety guards and _decide() method"
provides:
  - "_detect_new_hand() method for hand boundary detection with sentinel handling"
  - "_update_pot() method for cross-street pot accumulation workaround"
  - "Preflop aggressor flag set on preflop raises, persists to postflop"
  - "Hand counter incrementing across hands within a simulation"
  - "State tracking test suite with 6 tests covering STATE-01 through STATE-04"
affects: [02-preflop-system, 03-postflop-analysis, 04-postflop-decisions]

# Tech tracking
tech-stack:
  added: []
  patterns: [additive-pot-tracking, sentinel-based-hand-detection, board-length-transition]

key-files:
  created:
    - tests/test_bot_state.py
  modified:
    - players/mtt_bot.py

key-decisions:
  - "Additive pot tracking via board_len transitions -- locks in previous street pot when board grows"
  - "Sentinel value -1 for _last_board_len to handle first-hand edge case distinctly from new-hand detection"
  - "Preflop aggressor flag set inline in _decide() raise paths rather than in a separate method"

metrics:
  duration: 3min
  completed: "2026-04-11T01:59:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 01 Plan 02: State Tracking Summary

Cross-street pot accumulator and hand boundary detection wired into _decide() with sentinel-based first-hand handling, preflop aggressor tracking, and 6-test validation suite.

## What Was Done

### Task 1: Add _detect_new_hand and _update_pot methods, wire into _decide
- Added `_detect_new_hand(self, game_state)` method that detects hand boundaries via board_cards length transitions
- Sentinel value `_last_board_len == -1` handles first-hand initialization (sets `_hand_num = 1`)
- Subsequent new hands detected when `board_len == 0 and _last_board_len > 0` (board went from non-empty to empty)
- Per-hand state (`_pot_total`, `_street_pot`, `_was_preflop_aggressor`) resets on every new hand
- Added `_update_pot(self, game_state)` method that accumulates pot across streets
- When board grows (`board_len > _last_board_len`), locks in previous street's pot into `_pot_total`
- Always reads `game_state["pot_size"]` into `_street_pot` for current street
- Returns `_pot_total + _street_pot` as estimated total pot
- Wired both methods at the top of `_decide()` -- they execute before any decision logic
- Set `_was_preflop_aggressor = True` in both preflop raise paths (free raise and facing-bet raise)
- **Commit:** `067a980`

### Task 2: Create state tracking test suite
- Created `tests/test_bot_state.py` with 6 tests covering all STATE requirements
- `test_state01_pot_accumulator_across_streets`: verifies pot accumulates correctly across preflop (30) -> flop (60) -> turn (40) -> river (80) = 210 total
- `test_state02_hand_boundary_resets`: verifies pot_total, street_pot, and aggressor flag reset when board transitions from non-empty to empty
- `test_state03_preflop_aggressor_persists`: verifies flag is True after AA raise preflop and remains True on flop
- `test_state04_hand_counter_increments`: verifies hand_num goes 1, 2, 3 across 3 hand transitions
- `test_first_hand_sentinel`: verifies _last_board_len starts at -1 and first call sets hand_num to 1
- `test_same_street_no_double_count`: verifies multiple calls within preflop don't create false street transitions
- Uses same mock engine pattern as test_bot_safety.py
- **Commit:** `552ff7a`

## Verification Results

1. `python tests/test_bot_state.py` -- 6/6 state tests PASS
2. `python tests/test_bot_safety.py` -- 13/13 safety tests PASS (no regressions)
3. `python -c "import ast; ..."` -- Syntax OK

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | `067a980` | feat | Add state tracking methods and wire into _decide |
| 2 | `552ff7a` | test | Add state tracking test suite covering all STATE requirements |

## Self-Check: PASSED

All files verified present. All commits verified in git log.

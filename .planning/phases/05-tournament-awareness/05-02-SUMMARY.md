---
phase: 05-tournament-awareness
plan: 02
subsystem: tournament-awareness
tags: [tdd, bubble, itm, heads-up, icm, exploit, preflop, postflop]
dependency_graph:
  requires: [_get_tournament_stage, _get_stack_role, _initial_table_players]
  provides: [tournament-aware-preflop, icm-multiplier, exploit-adjustment, heads-up-opening]
  affects: []
tech_stack:
  added: []
  patterns: [threshold-offset-adjustment, icm-calling-multiplier, exploit-value-threshold]
key_files:
  created: []
  modified:
    - players/mtt_bot.py
    - tests/test_tournament.py
    - tests/test_postflop_decisions.py
decisions:
  - "Heads-up early exit placed BEFORE stack mode branches so it overrides push_fold/shallow/deep"
  - "ICM 1.4x multiplier only applied when call >= 30% of stack to avoid over-folding small bets"
  - "exploit_adj of 0.10 applied universally (all stages) since test field is always weak bots"
  - "test_icm_capped_at_one uses ehs=0.80 (not 0.95) to avoid triggering monster raise path at ehs>=0.85"
metrics:
  duration: "~6 minutes"
  completed: "2026-04-12T02:46:49Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 21
  tests_total: 217
---

# Phase 5 Plan 02: Tournament-Aware Decision Integration Summary

TDD wiring of tournament stage awareness into _preflop (heads-up/bubble/ITM threshold adjustments), _facing_bet (ICM 1.4x calling multiplier at bubble), and _bet_or_check (0.55 value bet threshold for field exploitation) with 21 new tests covering all tournament stages.

## What Was Done

### Task 1: TDD tournament-aware preflop/postflop adjustments

**RED phase** (commit 18ecaab):
- Added 17 new tests across 5 test classes:
  - TestHeadsUp: 5 tests for TOURN-06 (chen>=3 opening, sb_complete, facing_open)
  - TestBubblePlay: 3 tests for TOURN-04 (big stack widens, medium tightens, short uses push-fold)
  - TestITMAggression: 2 tests for TOURN-05 (wider opening, no ICM at ITM)
  - TestICMMultiplier: 4 tests for TOURN-02 (bubble large call, non-bubble, small call, cap at 1.0)
  - TestExploitAdjustment: 3 tests for TOURN-07 (turn/river threshold lowered, below threshold checks)
- 9 tests failed as expected (tournament-aware code not yet implemented)

**GREEN phase** (commit 001532e):
- Modified `_preflop()`:
  - Added `stage = self._get_tournament_stage(game_state)` before mode branches
  - TOURN-06: Heads-up early exit with chen>=3 for rfi/sb_complete, chen>=5 for facing_open
  - TOURN-04: Bubble adjustments in deep/medium path (big stack -1, medium +2 to rfi_threshold)
  - TOURN-05: ITM lowers rfi_threshold by 1
- Modified `_facing_bet()`:
  - TOURN-02: ICM 1.4x multiplier on req_eq when stage=="bubble" and call >= 30% stack, capped at 1.0
- Modified `_bet_or_check()`:
  - TOURN-07: exploit_adj=0.10, value_threshold=0.55 replaces hardcoded 0.65 on turn/river
- Fixed `tests/test_postflop_decisions.py` make_gs helper to include `active_players` field (Rule 3 auto-fix)
- All 213 tests pass

### Task 2: Final integration verification and regression

**Commit ac60d08:**
- Added TestRegression class with 4 tests:
  - test_early_stage_rfi_threshold_unchanged: chen=6 opens, chen=5 folds (threshold=6 preserved)
  - test_early_stage_facing_bet_no_icm: no ICM multiplier outside bubble
  - test_early_stage_value_bet_threshold: exploit_adj applies to all stages (ehs=0.58 bets)
  - test_middle_stage_no_bubble_adjustment: middle stage threshold unmodified
- Verified no blocked imports (time, collections, itertools)
- Verified single class (HawkEyeBot), all state picklable (int, float, bool)
- Verified _initial_table_players in 4+ locations
- Full suite: 217 tests pass

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 18ecaab | test | Add failing tests for tournament-aware preflop/postflop adjustments |
| 001532e | feat | Wire tournament awareness into preflop and postflop decisions |
| ac60d08 | test | Add regression tests and verify full integration |

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| TOURN-02 in mtt_bot.py | PASS (1 match) |
| TOURN-04 in mtt_bot.py | PASS (2 matches) |
| TOURN-05 in mtt_bot.py | PASS (1 match) |
| TOURN-06 in mtt_bot.py | PASS (1 match) |
| TOURN-07 in mtt_bot.py | PASS (3 matches) |
| 1.4 in mtt_bot.py | PASS (2 matches) |
| exploit_adj in mtt_bot.py | PASS (2 matches) |
| value_threshold in mtt_bot.py | PASS (3 matches) |
| TestHeadsUp in tests | PASS |
| TestBubblePlay in tests | PASS |
| TestICMMultiplier in tests | PASS |
| TestExploitAdjustment in tests | PASS |
| TestRegression in tests | PASS |
| pytest tests/test_tournament.py exits 0 | PASS (36 passed) |
| pytest tests/ exits 0 (regression) | PASS (217 passed) |
| No blocked imports | PASS |
| Single class HawkEyeBot | PASS (1 match) |
| _initial_table_players in 3+ locations | PASS (4 matches) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added active_players to test_postflop_decisions.py make_gs helper**
- **Found during:** Task 1 GREEN phase
- **Issue:** Existing postflop test helper `make_gs()` did not include `active_players` key, causing KeyError when `_facing_bet` now calls `_get_tournament_stage()`
- **Fix:** Added `active_players=6` default parameter to `make_gs()` and included it in returned dict
- **Files modified:** tests/test_postflop_decisions.py
- **Commit:** 001532e

**2. [Rule 1 - Bug] Fixed test_icm_capped_at_one using ehs below monster threshold**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test used ehs=0.95 which triggers monster hand raise (ehs >= 0.85) before pot-odds check, bypassing ICM logic under test
- **Fix:** Changed to ehs=0.80 so pot-odds path is exercised and ICM cap is properly tested
- **Files modified:** tests/test_tournament.py
- **Commit:** 001532e

## Self-Check: PASSED

- [x] players/mtt_bot.py exists
- [x] tests/test_tournament.py exists
- [x] tests/test_postflop_decisions.py exists
- [x] 05-02-SUMMARY.md exists
- [x] Commit 18ecaab found
- [x] Commit 001532e found
- [x] Commit ac60d08 found

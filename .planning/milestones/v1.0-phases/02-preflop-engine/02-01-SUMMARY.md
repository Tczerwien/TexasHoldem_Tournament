---
phase: 02-preflop-engine
plan: 01
subsystem: preflop
tags: [chen-formula, push-fold, lookup-tables, treys-encoding, precomputation]

# Dependency graph
requires:
  - phase: 01-skeleton-and-safety
    provides: HawkEyeBot class with safety guards, pot accumulator, hand detection
provides:
  - FULL_DECK: 52-card treys-encoded deck for MC sampling
  - CHEN_TABLE: 169-entry preflop hand strength scores
  - SHOVE_TABLE: 169-entry push-fold shove ranges by BB depth
  - CALL_TABLE: 169-entry push-fold call ranges by villain BB depth
  - COMBO_INDICES: 21 C(7,5) index tuples for hand evaluation
  - _get_chen_key: method to extract lookup key from treys hole cards
affects: [02-preflop-engine, 03-postflop-analysis, 04-postflop-decisions, 05-tournament-integration]

# Tech tracking
tech-stack:
  added: [math.ceil]
  patterns: [module-level precomputation, dict-based lookup tables, treys bit extraction]

key-files:
  created:
    - tests/test_preflop.py
    - .gitignore
  modified:
    - players/mtt_bot.py

key-decisions:
  - "Chen formula gap penalty applied before straight bonus per thepokerbank.com reference"
  - "Shove/call tables use Nash equilibrium values tightened for multiway pots"
  - "All 169 entries initialized to 0 first, then specific values set to ensure full coverage"
  - "Pairs marked suited=False in _get_chen_key via r1 != r2 check"

patterns-established:
  - "Module-level table builders: _build_X_table() functions called at import time"
  - "Key format: (high_rank_int, low_rank_int, suited_bool) with high >= low"
  - "Treys bit extraction: rank=(card>>8)&0xF, suit=(card>>12)&0xF"
  - "Test pattern: mock engine module before import, make_card() helper for treys cards"

requirements-completed: [PRE-01, PRE-04, PRE-05, COMP-01, COMP-02, COMP-03, COMP-04, COMP-05]

# Metrics
duration: 5min
completed: 2026-04-11
---

# Phase 2 Plan 1: Preflop Lookup Tables Summary

**Four module-level precomputed lookup tables (FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE) with 25-test validation suite covering all 169 hand categories**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-11T04:16:40Z
- **Completed:** 2026-04-11T04:22:05Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Built all four lookup tables at module level with zero runtime cost to 500ms decision budget
- Chen formula produces correct scores for all known reference hands (AA=20, KK=16, 22=5, 72o minimal)
- Push-fold shove and call tables cover all 169 hand categories with Nash-derived BB depth thresholds
- Call ranges are provably tighter than shove ranges for every hand (verified by test)
- 25 comprehensive unit tests covering structure, known values, monotonicity, and regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Build module-level lookup tables and _get_chen_key helper** - `451e66b` (feat)
2. **Task 2: Create preflop test suite for tables and chen key extraction** - `ac225b4` (test)
3. **.gitignore for pycache** - `f40a2d6` (chore)

## Files Created/Modified
- `players/mtt_bot.py` - Added FULL_DECK (52 cards), CHEN_TABLE (169 entries), SHOVE_TABLE (169 entries), CALL_TABLE (169 entries), COMBO_INDICES (21 tuples), _get_chen_key method
- `tests/test_preflop.py` - 25 unit tests across 7 test classes covering all table requirements
- `.gitignore` - Excludes __pycache__/, *.pyc, .pytest_cache/

## Decisions Made
- Chen formula gap penalty applied before straight bonus, matching thepokerbank.com reference exactly
- Shove/call tables initialized all 169 entries to 0 first, then set specific values -- ensures no missing keys
- Pairs cannot be suited: enforced both in table construction (skip suited=True for pairs) and in _get_chen_key (r1 != r2 check)
- Straight bonus only applies when both ranks below Queen (rank_int < 10) and gap <= 1

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added .gitignore for generated files**
- **Found during:** Post-commit cleanup
- **Issue:** __pycache__ directories created by test runs were showing as untracked
- **Fix:** Created .gitignore with __pycache__/, *.pyc, .pytest_cache/ patterns
- **Files modified:** .gitignore
- **Verification:** git status shows clean working tree
- **Committed in:** f40a2d6

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor housekeeping. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All four lookup tables ready for Plan 02 (preflop decision logic)
- _get_chen_key provides the bridge from treys card encoding to table lookups
- COMBO_INDICES ready for Phase 3 hand evaluator
- FULL_DECK ready for Phase 3 Monte Carlo sampling
- 44 total tests passing (25 preflop + 13 safety + 6 state)

## Self-Check: PASSED

- All 4 key files found on disk
- All 3 task commits verified in git log (451e66b, ac225b4, f40a2d6)
- 44/44 tests passing across all test suites

---
*Phase: 02-preflop-engine*
*Completed: 2026-04-11*

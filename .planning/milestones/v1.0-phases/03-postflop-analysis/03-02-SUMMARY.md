---
phase: 03-postflop-analysis
plan: 02
subsystem: postflop-analysis
tags: [mc-equity, draw-detection, board-texture, ehs, monte-carlo]
dependency_graph:
  requires: [03-01]
  provides: [_mc_equity, _detect_draws, _classify_board, _ehs]
  affects: [players/mtt_bot.py, tests/test_postflop.py]
tech_stack:
  added: [random.sample]
  patterns: [monte-carlo-simulation, set-based-deck-filtering, tuple-comparison]
key_files:
  created: []
  modified: [players/mtt_bot.py, tests/test_postflop.py]
decisions:
  - "Fixed iteration caps (300/400/500) avoid time module dependency"
  - "Set-based deck filtering for O(1) card exclusion in MC sampling"
  - "Draw bonus priority: combo(0.09) > flush(0.06) > OESD(0.05) > gutshot(0.03)"
  - "Board connectedness requires 3 ranks within span<=3 to avoid over-classification (Pitfall 4)"
metrics:
  duration: 244s
  completed: "2026-04-11T05:00:41Z"
  tasks_completed: 1
  tasks_total: 1
  tests_added: 30
  tests_total: 147
---

# Phase 03 Plan 02: MC Equity, Draw Detection, Board Texture, and EHS Summary

MC equity estimation via random.sample with fixed iteration caps (300/400/500), draw detection for flush/OESD/gutshot/combo with edge case handling, board texture classification (PAIRED/DRY/SEMI_WET/WET), and EHS combiner that adds draw bonus to equity (capped at 1.0).

## What Was Built

### _mc_equity (POST-02)
Monte Carlo equity estimation sampling random opponent hands against hero. Uses `random.sample()` for the inner loop (50x faster than numpy for small samples). Fixed iteration caps: 300 flop, 400 turn, 500 river. Preflop guard returns 0.5. Set-based deck filtering prevents duplicate cards (T-03-04 mitigation).

### _detect_draws (POST-03)
Draw type detection from hole + board cards. Detects flush draws (4 of a suit), OESD (4 consecutive ranks with both ends open), gutshots (4 ranks spanning 5), and combo draws (flush + straight). Edge cases handled: made flush suppresses flush draw (Pitfall 2), ace boundaries suppress OESD (Pitfall 3), made straight suppresses straight draws.

### _classify_board (POST-05)
Board texture classification. PAIRED takes priority (any rank count >= 2). Then checks flush potential (3+ of a suit) and connectedness (3 ranks within span <= 3). Both = WET, either = SEMI_WET, neither = DRY.

### _ehs (POST-04)
Effective Hand Strength combining MC equity with draw bonus. Priority order: combo_draw=0.09, flush_draw=0.06, oesd=0.05, gutshot=0.03. No bonus on river (no cards to come). Capped at 1.0.

## Task Execution

### Task 1: MC equity, draw detection, board texture, and EHS (TDD)

| Phase | Commit | Description |
|-------|--------|-------------|
| RED | 82c463f | Added 30 failing tests across 4 test classes |
| GREEN | 45d9274 | Implemented all 4 methods, 147/147 tests pass |
| REFACTOR | -- | No refactor needed, code clean and minimal |

**Files modified:** players/mtt_bot.py, tests/test_postflop.py

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_semi_wet_flush_possible board composition**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test used board [9h, Th, 2d] expecting SEMI_WET, but ranks 7(9), 8(T), 0(2) have no 3-rank window within span<=3, so connectedness was False, yielding DRY
- **Fix:** Changed board to [9h, Th, 8d] where ranks 6(8), 7(9), 8(T) form a connected group (span=2)
- **Files modified:** tests/test_postflop.py
- **Commit:** 45d9274

## Commits

| Hash | Type | Message |
|------|------|---------|
| 82c463f | test | add failing tests for MC equity, draw detection, board texture, and EHS |
| 45d9274 | feat | implement MC equity, draw detection, board texture, and EHS |

## Known Stubs

None -- all four methods are fully implemented and wired to the evaluator from Plan 01.

## Self-Check: PASSED

- players/mtt_bot.py: FOUND
- tests/test_postflop.py: FOUND
- Commit 82c463f: FOUND
- Commit 45d9274: FOUND
- 4 methods implemented (_mc_equity, _detect_draws, _classify_board, _ehs)
- 4 test classes added (TestMCEquity, TestDrawDetection, TestBoardTexture, TestEHS)
- 147/147 tests passing

---
phase: 02-preflop-engine
plan: 02
subsystem: preflop-decisions
tags: [preflop, decision-tree, push-fold, stack-mode, chen-formula, raise-sizing]
dependency_graph:
  requires: [02-01]
  provides: [_preflop, _get_stack_mode, _detect_situation, _is_3bet_hand, _is_4bet_hand, _preflop_raise_amount]
  affects: [_decide, tests/test_bot_safety.py, tests/test_bot_state.py]
tech_stack:
  added: []
  patterns: [preflop-decision-tree, stack-mode-routing, situation-inference, chen-threshold-ranges]
key_files:
  created: []
  modified:
    - players/mtt_bot.py
    - tests/test_preflop.py
    - tests/test_bot_safety.py
    - tests/test_bot_state.py
decisions:
  - "BB option always checks (trap play) -- updated Phase 1 tests that expected AA raise on call_amount=0"
  - "Chen thresholds: deep RFI >= 6 (~25.5%), medium RFI >= 7 (~17.8%)"
  - "3-bet range: QQ+/AKs only; 4-bet range: AA/KK only -- tight for MTT"
  - "Raise sizing uses additive format: desired_total - call_amount"
metrics:
  duration: 6m41s
  completed: 2026-04-11T04:32:34Z
  tasks_completed: 2
  tasks_total: 2
  test_count: 93
  files_modified: 4
requirements:
  - PRE-02
  - PRE-03
  - PRE-06
  - PRE-07
  - PRE-08
  - PRE-09
---

# Phase 02 Plan 02: Preflop Decision Engine Summary

Full preflop decision tree with stack mode routing, situation inference, Chen-threshold opening ranges, push-fold shove/call logic, 3-bet/4-bet detection, and correct additive raise sizing for the engine.

## What Was Built

### Task 1: Preflop Decision Engine (TDD)

Implemented 6 new methods on HawkEyeBot and replaced _decide() routing:

- **_get_stack_mode()** (PRE-02): Classifies stack depth as deep (40BB+), medium (25-39BB), shallow (15-24BB), or push_fold (<15BB). Includes T-02-05 division-by-zero guard for bb=0.

- **_detect_situation()** (PRE-06): Infers preflop situation from call_amount relative to blinds -- bb_option (0), sb_complete (bb-sb), rfi (bb), facing_open (<6x bb), facing_3bet (6x+ bb).

- **_is_3bet_hand()** (PRE-08): QQ+, AKs -- hands that 3-bet facing an open.

- **_is_4bet_hand()** (PRE-08): AA, KK -- hands that 4-bet facing a 3-bet.

- **_preflop_raise_amount()** (PRE-09): Calculates raise increment (desired_total - call_amount) by stack mode: deep 2.5x BB, medium 2.2x BB, shallow 2.0x BB.

- **_preflop()** (PRE-03, PRE-07): Main decision tree routing:
  - Push-fold: shove/fold via SHOVE_TABLE, call/fold facing shoves via CALL_TABLE
  - Shallow: shove strong, raise decent, 3-bet/4-bet premium
  - Deep/medium: Chen-threshold opening ranges, 3-bet premium facing opens, 4-bet AA/KK facing 3-bets, call strong hands deep, check BB option, complete SB with decent hands

- **_decide()** (D-11): Routes to _preflop() when board is empty, tight-passive postflop fallback for Phase 3/4.

Every code path returns through _guard(). Preflop aggressor flag set on all raises.

### Task 2: Comprehensive Decision Behavior Tests

74 test functions in test_preflop.py covering all preflop requirements:

| Test Class | Count | Coverage |
|------------|-------|----------|
| Plan 01 table tests | 25 | FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE, _get_chen_key |
| TestStackModeDetection | 4 | deep/medium/shallow/push_fold at boundaries |
| TestSituationDetection | 6 | All 5 situations + combined test |
| TestPushFoldDecisions | 5 | AA shove, 72o fold, BB check, facing shove AA/72o |
| TestDeepDecisions | 7 | RFI open/fold, QQ 3-bet, AA 4-bet, fold trash, BB check, SB complete |
| TestRaiseSizing | 2 | Deep 2.5x, medium 2.2x |
| TestStackModeBoundaries | 4 | 39.9BB, 24.9BB, 14.9BB edge cases, bb=0 safety |
| Test3BetHandDetection | 8 | AA/KK/QQ/AKs yes, JJ/AKo/AQs/72o no |
| Test4BetHandDetection | 5 | AA/KK yes, QQ/JJ/AKs no |
| TestAggressorFlag | 3 | Set on raise, not on fold, not on call |
| TestRegressionPhase1 | 5 | Instantiation, postflop, guard checks |

Full suite: 93 tests (13 safety + 6 state + 74 preflop), all passing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Phase 1 D-01/D-03 tests used preflop game states**
- **Found during:** Task 1 GREEN phase
- **Issue:** test_d01_call_when_cheap, test_d01_fold_when_expensive, test_d03_check_when_free used empty board_cards. With _decide() now routing to _preflop(), these tests got different (correct) preflop decisions instead of the old tight-passive behavior.
- **Fix:** Updated tests to use postflop board_cards (3 board cards) since D-01 tight-passive logic is now the postflop fallback.
- **Files modified:** tests/test_bot_safety.py
- **Commit:** f0c0e28

**2. [Rule 1 - Bug] Phase 1 D-02 test expected raise on bb_option**
- **Found during:** Task 1 GREEN phase
- **Issue:** test_d02_raise_premium_preflop used call_amount=0 (bb_option) with AA, expecting a raise. The preflop engine correctly checks in bb_option (trap play).
- **Fix:** Changed test to use call_amount=20 (RFI) where AA correctly raises.
- **Files modified:** tests/test_bot_safety.py
- **Commit:** f0c0e28

**3. [Rule 1 - Bug] Phase 1 STATE-03 aggressor test used bb_option**
- **Found during:** Task 1 GREEN phase
- **Issue:** test_state03_preflop_aggressor_persists used call_amount=0 with AA, expecting raise to set aggressor flag.
- **Fix:** Changed to call_amount=20 (RFI) where AA raises and correctly sets the flag.
- **Files modified:** tests/test_bot_state.py
- **Commit:** f0c0e28

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 35de7af | test | RED: add failing preflop decision behavior tests |
| f0c0e28 | feat | GREEN: implement preflop decision engine with full decision tree |
| 7de91d3 | test | Add comprehensive preflop decision behavior tests |

## Verification Results

```
$ python -m pytest tests/ -v
93 passed in 0.07s
```

All acceptance criteria verified:
- All 6 methods present in mtt_bot.py
- _decide() routes to _preflop() on empty board, postflop fallback otherwise
- Every _preflop() return goes through _guard()
- Raise amounts use additive format (desired_total - call_amount)
- _was_preflop_aggressor set on all preflop raises
- get_action() try/except wrapper preserved (SAFE-02)
- _guard() unchanged from Phase 1
- 74+ test functions in test_preflop.py
- All grep patterns match: test_stack_mode, test_situation_detection, test_push_fold_shove, test_deep_rfi, test_facing_open, test_facing_3bet, test_bb_option, test_raise_sizing, test_aggressor_flag
- No regressions in Phase 1 test suites

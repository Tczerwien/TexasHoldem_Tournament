---
phase: 04-postflop-decisions
plan: 01
subsystem: postflop-decision-engine
tags: [postflop, ehs, cbet, pot-odds, bet-sizing, spr, tdd]
dependency_graph:
  requires:
    - 03-01 (hand evaluator, MC equity, EHS, draw detection, board texture)
    - 01-01 (safety guards, _guard method, pot accumulator)
  provides:
    - _postflop() entry point for postflop decisions
    - _facing_bet() for bet/raise/fold/call decisions
    - _bet_or_check() for c-bet, barrel, value bet decisions
    - _cbet_threshold() texture-dependent c-bet thresholds
    - _calc_bet_size() street/texture bet sizing
  affects:
    - 04-02 (wiring _postflop into _decide)
tech_stack:
  added: []
  patterns:
    - EHS-bucket thresholds (MONSTER >= 0.85, STRONG >= 0.65)
    - Pot odds formula (req_eq = call / (pot + call))
    - SPR commitment (stack / pot < 1.5 -> shove)
    - Stack commitment (bet >= 60% stack -> shove)
    - Texture-dependent bet sizing (33-75% pot)
key_files:
  created:
    - tests/test_postflop_decisions.py
  modified:
    - players/mtt_bot.py
decisions:
  - "Used nested helper _apply_commit() inside _bet_or_check to DRY up SPR + stack commitment checks across c-bet, turn barrel, and river value bet paths"
  - "Division guard uses est_pot=1 fallback when est_pot<=0 for SPR calc (avoids ZeroDivisionError per T-04-03)"
metrics:
  duration: 274s
  completed: "2026-04-11T07:47:23Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 30
  tests_total: 177
  lines_added: 188
---

# Phase 04 Plan 01: Postflop Decision Engine Summary

EHS-driven postflop decision engine with 5 methods implementing POST-06 through POST-13: c-bet with texture-dependent thresholds, pot odds call/fold, monster hand raises, street-specific bet sizing (33-75% pot), SPR commitment shoves, and stack commitment shoves.

## What Was Built

### Five New Methods on HawkEyeBot

1. **_postflop(game_state, est_pot)** -- Single entry point. Computes EHS and board texture exactly once, determines street from board length, routes to _facing_bet (call_amount > 0) or _bet_or_check (call_amount == 0).

2. **_facing_bet(game_state, est_pot, ehs, texture, street)** -- Decision when facing a bet. Implements:
   - POST-07: Pot odds via `req_eq = call / (pot + call)`. Calls when EHS >= req_eq, folds otherwise.
   - POST-08: Monster raise when EHS >= 0.85.
   - POST-10: Stack commitment -- if raise size >= 60% of stack, shoves instead.
   - POST-13: SPR commitment -- if stack/pot < 1.5 and has adequate equity, shoves.

3. **_bet_or_check(game_state, est_pot, ehs, texture, street)** -- Decision when first to act. Implements:
   - POST-06: C-bet on flop when preflop aggressor and EHS >= texture threshold.
   - POST-11: Turn barrel with STRONG+ hands (EHS >= 0.65) at 66% pot.
   - POST-12: River value bet with STRONG+ hands (EHS >= 0.65) at 75% pot.
   - POST-13: SPR commitment check before all bets.
   - POST-10: Stack commitment check before all bets.

4. **_cbet_threshold(texture)** -- Returns EHS threshold for c-betting: DRY=0.35, SEMI_WET=0.45, PAIRED=0.40, WET=0.55.

5. **_calc_bet_size(est_pot, stack, texture, street)** -- Returns bet amount: Flop DRY=33%, SEMI_WET/PAIRED=50%, WET=66%. Turn=66%. River=75%. Floored to 1 chip minimum.

### Test Coverage

30 new test methods across 10 test classes:
- TestCbet (4 tests): dry/wet c-bet, threshold behavior, non-aggressor check
- TestPotOdds (2 tests): fold below req_eq, call above req_eq
- TestFacingBet (3 tests): monster raise, pot odds call, fold without odds
- TestBetSizing (6 tests): all street/texture combinations
- TestStackCommit (2 tests): shove on 60%+ stack, normal otherwise
- TestTurnBarrel (2 tests): barrel with STRONG+, check with medium
- TestRiverValueBet (2 tests): value bet with STRONG+, check with medium
- TestSPRCommit (2 tests): shove on low SPR, normal on high SPR
- TestPostflopRouting (3 tests): routing, check path, single EHS call verification
- TestEdgeCases (4 tests): SPR facing bet, threshold values, min bet floor, zero pot guard

All tests use mocked _ehs() for deterministic sub-millisecond execution.

## Requirements Implemented

| Requirement | Description | Method |
|-------------|-------------|--------|
| POST-06 | C-bet logic with aggressor tracking and texture | _bet_or_check, _cbet_threshold |
| POST-07 | Pot odds call/fold with required equity | _facing_bet |
| POST-08 | Raise/call/fold decision hierarchy | _facing_bet |
| POST-09 | Bet sizing by street and texture | _calc_bet_size |
| POST-10 | Stack commitment (>= 60% -> shove) | _facing_bet, _bet_or_check |
| POST-11 | Turn barrel with STRONG+ hands | _bet_or_check |
| POST-12 | River value bet with STRONG+ hands | _bet_or_check |
| POST-13 | SPR commitment (< 1.5 -> shove) | _facing_bet, _bet_or_check |

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Task | Type | Hash | Description |
|------|------|------|-------------|
| 1 | RED | a15c141 | 30 failing tests for postflop decision methods |
| 2 | GREEN | 3e2c858 | 5 postflop decision methods passing all tests |

## Verification

- `python -m pytest tests/test_postflop_decisions.py -x -q` -- 30 passed
- `python -m pytest tests/ -x -q` -- 177 passed (no regressions)
- 5 new method definitions confirmed in players/mtt_bot.py

## Self-Check: PASSED

- FOUND: tests/test_postflop_decisions.py
- FOUND: players/mtt_bot.py
- FOUND: .planning/phases/04-postflop-decisions/04-01-SUMMARY.md
- FOUND: commit a15c141
- FOUND: commit 3e2c858

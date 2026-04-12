---
phase: 04-postflop-decisions
verified: 2026-04-11T13:30:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Full test suite passes with zero failures across all test files"
    - "test_bot_safety.py tests use valid treys-encoded board cards"
    - "Stale tight-passive tests are replaced with EHS-driven postflop behavior tests"
  gaps_remaining: []
  regressions: []
---

# Phase 4: Postflop Decisions Verification Report

**Phase Goal:** Bot makes correct postflop betting decisions using the analysis engine from Phase 3
**Verified:** 2026-04-11T13:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 04-03)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Bot fires c-bets on the flop when preflop aggressor with sufficient hand strength, considering board texture | VERIFIED | `_bet_or_check` line 1317: `if street == 3 and self._was_preflop_aggressor`. `_cbet_threshold` lines 1177-1197 returns 0.35/0.40/0.45/0.55 by texture. TestCbet 4 tests pass. |
| 2 | Bot folds when EHS is well below required equity (pot odds) and calls/raises when EHS exceeds threshold | VERIFIED | `_facing_bet` line 1256: `req_eq = call_amount / (est_pot + call_amount)`. Three-tier hierarchy verified. TestPotOdds and TestFacingBet 5 tests pass. |
| 3 | Bet sizing varies by street, texture, and situation (33-75% pot) | VERIFIED | `_calc_bet_size` lines 1215-1231: DRY flop=33%, WET flop=66%, SEMI_WET/PAIRED=50%, turn=66%, river=75%. TestBetSizing 6 tests pass. |
| 4 | Bot shoves instead of betting when bet would commit 60%+ of stack | VERIFIED | `_facing_bet` line 1270: `if raise_size >= stack * 0.6 -> shove`. `_apply_commit` line 1312: same check. TestStackCommit 2 tests pass. |
| 5 | Bot barrels turn with strong+ hands and value bets river with strong+ hands | VERIFIED | `_bet_or_check` line 1324: `if street == 4 and ehs >= 0.65`. Line 1329: `if street == 5 and ehs >= 0.65`. TestTurnBarrel 2 tests, TestRiverValueBet 2 tests pass. |
| 6 | `_decide()` routes to `_postflop()` when board_cards is non-empty | VERIFIED | Line 584: `return self._postflop(game_state, est_pot)`. Tight-passive fallback removed. TestDecidePostflopRouting 4 integration tests pass. |
| 7 | Full test suite passes with zero failures across all test files | VERIFIED | `python -m pytest tests/` — 181/181 passed. test_bot_safety.py 13/13 passed. test_postflop_decisions.py 34/34 passed. Zero failures, zero flaky tests. |
| 8 | test_bot_safety.py uses valid treys-encoded board cards with mocked EHS for determinism | VERIFIED | Zero occurrences of `0x00010000`, `0x00020000`, `0x00040000`. Three tests use `make_card()` for valid treys encoding and lambda mocks for `_ehs`. |

**Score:** 8/8 must-haves verified

### Gap Closure Status

The single gap from initial verification (Truth 7 — intermittent test failures from stale tight-passive tests) is fully resolved by Plan 04-03:

- `test_d01_call_when_cheap` replaced by `test_postflop_calls_when_ehs_above_req_eq` (valid board cards, mocked EHS=0.70, call_amount=50 -> call)
- `test_d01_fold_when_expensive` replaced by `test_postflop_folds_when_ehs_below_req_eq` (valid board cards, mocked EHS=0.20, call_amount=300 -> fold)
- `test_d03_check_when_free` updated to use valid board cards with mocked EHS=0.30
- Section comment updated from "D-01: Tight-passive call/fold logic" to "POST-07: Pot odds call/fold (EHS-driven postflop)"
- `__main__` runner updated with new test function names

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `players/mtt_bot.py` | `_postflop, _facing_bet, _bet_or_check, _cbet_threshold, _calc_bet_size` methods | VERIFIED | All 5 methods present (lines 1177, 1199, 1233, 1281, 1336). Each substantive. All wired via `_decide()` at line 584. |
| `tests/test_postflop_decisions.py` | 20+ unit tests with mocked EHS for all POST requirements | VERIFIED | 34 tests across 10 classes. All use mocked `_ehs()` for deterministic execution. All pass. |
| `tests/test_bot_safety.py` | Updated postflop tests with valid treys cards and mocked EHS | VERIFIED | 13 tests pass. No invalid card constants. 3 postflop tests use `make_card()` and `_ehs` lambda mocks. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_decide()` | `_postflop()` | `len(board_cards) > 0` branch | WIRED | Line 584: `return self._postflop(game_state, est_pot)`. Tight-passive fallback removed. |
| `_postflop()` | `_ehs(), _classify_board()` | Single computation at entry | WIRED | Lines 1354-1355: EHS and texture computed once, passed to sub-methods. `test_postflop_computes_ehs_once` passes. |
| `_facing_bet(), _bet_or_check()` | `_calc_bet_size()` | Bet sizing for raises and value bets | WIRED | `_facing_bet` line 1268, `_bet_or_check` lines 1320, 1325, 1330 all call `self._calc_bet_size(...)`. |
| `_facing_bet(), _bet_or_check()` | `_guard()` | Every return path | WIRED | All 8 return statements in `_facing_bet`, all 5 in `_bet_or_check` (including inside `_apply_commit`) use `self._guard(...)`. |
| `tests/test_bot_safety.py` | `players/mtt_bot.py` | `_ehs` mock + `_facing_bet` behavior | WIRED | 3 tests mock `bot._ehs = lambda hole, board: VALUE` and call `bot._decide()` through the full pipeline. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `_postflop()` | `ehs` (float 0-1) | `_ehs(hole, board)` — MC simulation over Phase 3 hand evaluator | Yes — MC sampling with 300/400/500 iterations | FLOWING |
| `_postflop()` | `texture` (str) | `_classify_board(board)` — deterministic rank/suit analysis | Yes | FLOWING |
| `_facing_bet()` | `req_eq` (float) | `call_amount / (est_pot + call_amount)` from engine-provided game_state | Yes | FLOWING |
| `_bet_or_check()` | `self._was_preflop_aggressor` (bool) | Set by `_preflop()` Phase 2 during preflop raise | Yes — persists across streets (STATE-03) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_cbet_threshold("DRY") == 0.35` | `test_cbet_threshold_values` | 0.35 | PASS |
| `_cbet_threshold("WET") == 0.55` | `test_cbet_threshold_values` | 0.55 | PASS |
| `_facing_bet(call=50, pot=100, ehs=0.20)` folds (req_eq=0.333) | `test_pot_odds_fold` | ('fold', 0) | PASS |
| `_facing_bet(call=50, pot=100, ehs=0.40)` calls (req_eq=0.333) | `test_pot_odds_call` | ('call', 0) | PASS |
| `_calc_bet_size(300, 1000, 'DRY', 3)` = 99 (33%) | `test_sizing_dry_flop` | 99 | PASS |
| `_calc_bet_size(300, 1000, 'WET', 3)` = 198 (66%) | `test_sizing_wet_flop` | 198 | PASS |
| `_calc_bet_size(300, 1000, 'DRY', 4)` = 198 (66%) | `test_sizing_turn` | 198 | PASS |
| `_calc_bet_size(300, 1000, 'DRY', 5)` = 225 (75%) | `test_sizing_river` | 225 | PASS |
| Turn barrel: `_bet_or_check(stack=1000, pot=300, ehs=0.70, turn)` raises 198 | `test_turn_barrel_strong` | ('raise', 198) | PASS |
| River value: `_bet_or_check(stack=1000, pot=300, ehs=0.70, river)` raises 225 | `test_river_value_bet_strong` | ('raise', 225) | PASS |
| Stack commit: `_bet_or_check(stack=300, pot=300, ehs=0.70, turn)` shoves stack | `test_stack_commit_shoves` | ('raise', 300) | PASS |
| Full suite: 181 tests | `python -m pytest tests/ -q` | 181 passed | PASS |
| test_bot_safety.py: no invalid treys cards | `grep 0x00010000 tests/test_bot_safety.py` | zero matches | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| POST-06 | 04-01, 04-02 | C-bet logic based on preflop aggressor status, EHS bucket, board texture | SATISFIED | `_bet_or_check` lines 1317-1321; `_cbet_threshold` lines 1177-1197; TestCbet 4 tests pass |
| POST-07 | 04-01, 04-02, 04-03 | Pot odds call/fold via `req_eq = call_amount / (est_pot + call_amount)` | SATISFIED | `_facing_bet` line 1256; formula exact; TestPotOdds 2 tests pass; `test_postflop_calls_when_ehs_above_req_eq` and `test_postflop_folds_when_ehs_below_req_eq` in test_bot_safety.py pass |
| POST-08 | 04-01, 04-02, 04-03 | Raise/call/fold hierarchy facing bet using EHS vs req_eq multipliers | SATISFIED | `_facing_bet` lines 1267-1279; TestFacingBet 3 tests pass |
| POST-09 | 04-01, 04-02 | Bet sizing system (33-75% pot by street, texture, situation) | SATISFIED | `_calc_bet_size` lines 1215-1231; all 4 textures and 3 streets covered; TestBetSizing 6 tests pass |
| POST-10 | 04-01, 04-02 | Stack commitment rule (bet >= 60% of stack -> shove) | SATISFIED | `_facing_bet` line 1270; `_apply_commit` line 1312; TestStackCommit 2 tests pass |
| POST-11 | 04-01, 04-02 | Turn barreling with STRONG+ hands (66% pot) | SATISFIED | `_bet_or_check` line 1324; TestTurnBarrel 2 tests pass |
| POST-12 | 04-01, 04-02 | River value betting with STRONG+ hands (75% pot) | SATISFIED | `_bet_or_check` line 1329; TestRiverValueBet 2 tests pass |
| POST-13 | 04-01, 04-02 | SPR-based commitment (SPR < 1.5 and betting -> shove) | SATISFIED | `_facing_bet` line 1262; `_apply_commit` line 1310; TestSPRCommit 2 tests pass; TestEdgeCases::test_spr_facing_bet_shove passes |

All 8 POST requirements are SATISFIED by implementation evidence.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `players/mtt_bot.py:448` | Class docstring references "tight-passive decision logic" (historical) | Info | No functional impact; docstring predates Phase 4 replacement but is cosmetic only |

No blockers. No warnings. One info-level stale docstring with zero functional impact.

### Human Verification Required

None. All Phase 4 behaviors are fully verifiable programmatically. The five decision methods are pure arithmetic on EHS values with no visual rendering, real-time, or external service dependencies.

### Gaps Summary

No gaps. The single gap from initial verification — intermittent test failures in `test_bot_safety.py` due to invalid treys card constants and stale tight-passive tests — was fully resolved by Plan 04-03. The three affected tests now use valid `make_card()` encoding and deterministic `_ehs` lambda mocks. The full test suite runs 181/181 passed with zero flaky behavior.

All five roadmap success criteria are satisfied. All eight POST requirements have implementation evidence. Phase 4 goal is achieved.

---
_Verified: 2026-04-11T13:30:00Z_
_Verifier: Claude (gsd-verifier)_

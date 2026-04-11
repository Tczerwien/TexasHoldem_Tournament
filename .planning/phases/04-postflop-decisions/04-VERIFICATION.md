---
phase: 04-postflop-decisions
verified: 2026-04-11T08:30:00Z
status: gaps_found
score: 4/5 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Full test suite passes with zero regressions"
    status: failed
    reason: "test_d01_call_when_cheap in test_bot_safety.py is a stale test from Phase 1 that tested the tight-passive fallback. Now that _decide() routes to the EHS-driven _postflop() engine, this test fails intermittently (approx 30% of runs) because the synthetic board cards (0x00010000 etc.) are not valid treys integers. The EHS engine computes garbage-in equity from these malformed cards, occasionally returning EHS >= 0.85 which triggers a monster raise instead of the expected call. The test_d01_fold_when_expensive also fails sometimes for the same reason. Both tests are semantically invalidated by Phase 4 -- the tight-passive rule (call if call < 15% stack) no longer exists in any code path."
    artifacts:
      - path: "tests/test_bot_safety.py"
        issue: "test_d01_call_when_cheap and test_d01_fold_when_expensive test removed behavior (tight-passive fallback). With randomized pytest ordering they fail ~30% of runs. With deterministic order one fails consistently."
    missing:
      - "Update test_d01_call_when_cheap to use valid treys-encoded cards and test actual Phase 4 behavior (e.g., verify that a postflop facing-bet scenario with real board cards produces a call when EHS is above req_eq)"
      - "Update test_d01_fold_when_expensive similarly, or delete both tests and replace with tests that validate the new EHS-driven behavior -- the D-01 'tight-passive call/fold' behavior no longer exists"
---

# Phase 4: Postflop Decisions Verification Report

**Phase Goal:** Bot makes correct postflop betting decisions using the analysis engine from Phase 3
**Verified:** 2026-04-11T08:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `_postflop()` routes to `_facing_bet()` when `call_amount > 0` and to `_bet_or_check()` when `call_amount == 0` | VERIFIED | Lines 1358-1361: `if call_amount > 0: return self._facing_bet(...)` else `return self._bet_or_check(...)`. Routing test `TestPostflopRouting` (3 tests) confirms both paths. `test_postflop_computes_ehs_once` confirms single EHS computation. |
| 2 | `_facing_bet()` folds when EHS < req_eq, calls when EHS >= req_eq, raises when EHS >= 0.85 (MONSTER) | VERIFIED | Lines 1256-1279: pot odds formula `req_eq = call_amount / (est_pot + call_amount)`. Three-tier hierarchy: SPR shove -> monster raise -> pot-odds call -> fold. TestFacingBet (3 tests), TestPotOdds (2 tests) all pass. Spot-checks: fold(EHS=0.20,req=0.333) PASS, call(EHS=0.40,req=0.333) PASS. |
| 3 | `_bet_or_check()` fires c-bet on flop when preflop aggressor and EHS >= cbet_threshold by texture; barrels turn with STRONG+ at 66% pot; value bets river with STRONG+ at 75% pot | VERIFIED | Lines 1317-1334: flop c-bet at `street==3 and self._was_preflop_aggressor`, turn barrel at `street==4 and ehs>=0.65`, river value at `street==5 and ehs>=0.65`. TestCbet (4 tests), TestTurnBarrel (2), TestRiverValueBet (2) all pass. Spot-checks all PASS. |
| 4 | `_calc_bet_size()` returns different pot fractions by street and texture (33-75%) | VERIFIED | Lines 1215-1231: DRY flop=33%, WET flop=66%, SEMI_WET/PAIRED=50%, turn=66%, river=75%. TestBetSizing (6 tests) covering all combinations. Spot-checks: DRY 33%(300)=99 PASS, turn 66%(300)=198 PASS, river 75%(300)=225 PASS. |
| 5 | SPR < 1.5 and betting triggers shove; bet >= 60% of stack triggers shove | VERIFIED | `_facing_bet` lines 1262-1264: `if spr < 1.5 and ehs >= req_eq -> shove`. `_bet_or_check` lines 1309-1314: `_apply_commit` nested helper checks SPR then 60% rule. TestSPRCommit (2), TestStackCommit (2), TestEdgeCases::test_spr_facing_bet_shove all pass. Spot-check: stack=300, barrel=198 >= 60%*300=180 -> shove amount=300 PASS. |
| 6 | `_decide()` routes to `_postflop()` when board_cards is non-empty instead of tight-passive fallback | VERIFIED | Line 584: `return self._postflop(game_state, est_pot)`. Tight-passive fallback fully removed from `_decide()`. TestDecidePostflopRouting (4 integration tests) confirm full pipeline. |
| 7 | Full test suite passes with zero regressions | FAILED | `test_d01_call_when_cheap` in test_bot_safety.py fails intermittently (~30% of full-suite runs due to test ordering). Root cause: test uses invalid synthetic board cards (0x00010000 etc.) that produce non-deterministic EHS values near the 0.85 MONSTER threshold. The test was written for the old tight-passive fallback which Phase 4 removed. See Gaps Summary. |

**Score:** 4/5 roadmap success criteria verified (Truth 7 partially captures PLAN 04-02 must-have "Full test suite passes with zero regressions"; the five roadmap SCs map to Truths 1-6 which are all verified)

### Roadmap Success Criteria Mapping

| Roadmap SC | Truth # | Status |
|-----------|---------|--------|
| SC1: Bot fires c-bets on flop when preflop aggressor with sufficient hand strength considering board texture | 3 | VERIFIED |
| SC2: Bot correctly folds when EHS well below req_eq; calls/raises when EHS exceeds threshold | 2 | VERIFIED |
| SC3: Bet sizing varies by street, texture, situation (33-75% pot) | 4 | VERIFIED |
| SC4: Bot shoves instead of betting when bet commits 60%+ of stack (stack commitment rule) | 5 | VERIFIED |
| SC5: Bot barrels turn with strong+ hands; value bets river with strong+ hands | 3 | VERIFIED |

All 5 roadmap success criteria are VERIFIED.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `players/mtt_bot.py` | `_postflop, _facing_bet, _bet_or_check, _cbet_threshold, _calc_bet_size` methods | VERIFIED | All 5 methods present at lines 1177, 1199, 1233, 1281, 1336. Each is substantive (>20 lines with full logic). All wired via `_decide()` at line 584. |
| `tests/test_postflop_decisions.py` | Unit tests for all postflop methods with mocked EHS | VERIFIED | 34 tests across 10 classes (TestCbet, TestPotOdds, TestFacingBet, TestBetSizing, TestStackCommit, TestTurnBarrel, TestRiverValueBet, TestSPRCommit, TestPostflopRouting, TestEdgeCases) plus TestDecidePostflopRouting. All use mocked `_ehs()` for deterministic execution. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_decide()` | `_postflop()` | `len(board_cards) > 0` branch | WIRED | Line 584: `return self._postflop(game_state, est_pot)`. Tight-passive fallback removed. |
| `_postflop()` | `_ehs(), _classify_board()` | Single computation at entry, passed to sub-methods | WIRED | Lines 1354-1355: EHS and texture computed once. `test_postflop_computes_ehs_once` verifies no double-call. |
| `_facing_bet(), _bet_or_check()` | `_calc_bet_size()` | Bet sizing for raises and value bets | WIRED | `_facing_bet` line 1268: `raise_size = self._calc_bet_size(...)`. `_bet_or_check` lines 1320, 1325, 1330: `bet_size = self._calc_bet_size(...)`. |
| `_facing_bet(), _bet_or_check()` | `_guard()` | Every return path | WIRED | All 8 return statements in `_facing_bet` and all 5 in `_bet_or_check` use `self._guard(...)`. |
| `_bet_or_check()` | `_cbet_threshold()` | Flop c-bet decision | WIRED | Line 1318: `threshold = self._cbet_threshold(texture)`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `_postflop()` | `ehs` (float 0-1) | `_ehs(hole, board)` -> MC simulation over Phase 3 hand evaluator | Yes — MC sampling with 300/400/500 iterations, result is non-deterministic but mathematically grounded | FLOWING |
| `_postflop()` | `texture` (str) | `_classify_board(board)` -> rank/suit analysis of board cards | Yes — deterministic board analysis | FLOWING |
| `_facing_bet()` | `req_eq` (float) | `call_amount / (est_pot + call_amount)` from game_state | Yes — direct computation from engine-provided values | FLOWING |
| `_bet_or_check()` | `self._was_preflop_aggressor` (bool) | Set by `_preflop()` Phase 2 engine during preflop action | Yes — persists across streets per STATE-03 | FLOWING |

### Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| `_cbet_threshold("DRY") == 0.35` | 0.35 | PASS |
| `_cbet_threshold("WET") == 0.55` | 0.55 | PASS |
| `_facing_bet(call=50, pot=100, ehs=0.20)` folds (req_eq=0.333) | ('fold', 0) | PASS |
| `_facing_bet(call=50, pot=100, ehs=0.40)` calls (req_eq=0.333) | ('call', 0) | PASS |
| `_calc_bet_size(300, 1000, 'DRY', 3)` = 99 (33%) | 99 | PASS |
| `_calc_bet_size(300, 1000, 'DRY', 4)` = 198 (66%) | 198 | PASS |
| `_calc_bet_size(300, 1000, 'DRY', 5)` = 225 (75%) | 225 | PASS |
| Stack commit: `_bet_or_check(stack=300, pot=300, ehs=0.70, turn)` shoves stack | ('raise', 300) | PASS |
| Turn barrel: `_bet_or_check(stack=1000, pot=300, ehs=0.70, turn)` raises | ('raise', 198) | PASS |
| River value: `_bet_or_check(stack=1000, pot=300, ehs=0.70, river)` raises | ('raise', 225) | PASS |
| Turn check: `_bet_or_check(stack=1000, pot=300, ehs=0.50, turn)` checks | ('call', 0) | PASS |
| Bot is picklable after Phase 4 additions | pickle round-trip succeeds | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| POST-06 | 04-01, 04-02 | C-bet logic based on preflop aggressor status, EHS bucket, board texture | SATISFIED | `_bet_or_check` lines 1317-1321; `_cbet_threshold` lines 1177-1197; TestCbet 4 tests all pass |
| POST-07 | 04-01, 04-02 | Pot odds call/fold via `req_eq = call_amount / (est_pot + call_amount)` | SATISFIED | `_facing_bet` line 1256; formula exactly matches requirement; TestPotOdds 2 tests pass |
| POST-08 | 04-01, 04-02 | Raise/call/fold hierarchy facing bet using EHS vs req_eq multipliers | SATISFIED | `_facing_bet` lines 1267-1279; three-tier hierarchy; TestFacingBet 3 tests pass |
| POST-09 | 04-01, 04-02 | Bet sizing system (33-75% pot by street, texture, situation) | SATISFIED | `_calc_bet_size` lines 1215-1231; all 4 textures and 3 streets covered; TestBetSizing 6 tests pass |
| POST-10 | 04-01, 04-02 | Stack commitment rule (bet >= 60% of stack -> shove) | SATISFIED | `_facing_bet` line 1270: `if raise_size >= stack * 0.6`; `_apply_commit` line 1312: `if bet_size >= stack * 0.6`; TestStackCommit 2 tests pass |
| POST-11 | 04-01, 04-02 | Turn barreling with STRONG+ hands (66% pot) | SATISFIED | `_bet_or_check` line 1324: `if street == 4 and ehs >= 0.65`; TestTurnBarrel 2 tests pass |
| POST-12 | 04-01, 04-02 | River value betting with STRONG+ hands (75% pot) | SATISFIED | `_bet_or_check` line 1329: `if street == 5 and ehs >= 0.65`; TestRiverValueBet 2 tests pass |
| POST-13 | 04-01, 04-02 | SPR-based commitment (SPR < 1.5 and betting -> shove) | SATISFIED | `_facing_bet` line 1262: `if spr < 1.5`; `_apply_commit` line 1310: `if spr < 1.5`; TestSPRCommit 2 tests pass; TestEdgeCases::test_spr_facing_bet_shove passes |

All 8 POST requirements are SATISFIED by implementation evidence.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `tests/test_bot_safety.py:166` | `test_d01_call_when_cheap` tests removed behavior using invalid synthetic card integers that produce non-deterministic EHS near MONSTER boundary | Blocker | Causes intermittent test suite failures (~1-2 tests fail depending on pytest ordering and random MC seed) |
| `tests/test_bot_safety.py:176` | `test_d01_fold_when_expensive` same root cause (0x00010000 fake cards + removed tight-passive logic) | Warning | Fails in some orderings; masked by randomized pytest execution |
| `players/mtt_bot.py:448` | Class docstring references "tight-passive decision logic" (historical) | Info | No functional impact; docstring not updated to reflect Phase 4 replacement |

Note: `_apply_commit` nested closure in `_bet_or_check` is NOT a SAFE-06 violation — it is a local stack frame function, not stored on `self`, and therefore never pickled.

### Human Verification Required

None. All Phase 4 behaviors are verifiable programmatically. The five new methods are pure arithmetic on EHS values with no visual rendering, real-time, or external service dependencies.

### Gaps Summary

**Root cause of single gap:** Phase 4 replaced the tight-passive fallback in `_decide()` with the EHS-driven `_postflop()` engine (correct behavior). However, two tests in `tests/test_bot_safety.py` — `test_d01_call_when_cheap` and `test_d01_fold_when_expensive` — were written in Phase 1 to test the tight-passive logic. They use synthetic board cards (`0x00010000`, `0x00020000`, `0x00040000`) that are not valid treys-encoded integers (they have no rank bits, no prime encoding, no suit bits).

When these malformed cards flow into `_ehs()`, the MC simulator computes nonsensical equity that varies randomly around 0.80-0.85. Because the MONSTER threshold is exactly 0.85, the bot sometimes raises (EHS >= 0.85) and sometimes calls (EHS < 0.85) — making the test flaky with ~30% raise rate.

The tests are semantically wrong for the current codebase: the D-01 tight-passive behavior (`call if call < 15% stack`) no longer exists anywhere in the bot. These tests should be updated to use valid treys cards and test actual Phase 4 behavior, or deleted and replaced.

**Scope of impact:** The gap affects test suite reliability only. The Phase 4 implementation is correct — all 5 roadmap success criteria are fully satisfied, all 8 POST requirements have implementation evidence, and 34 dedicated postflop tests pass deterministically. The regression is in stale Phase 1 tests, not in Phase 4 code.

---
_Verified: 2026-04-11T08:30:00Z_
_Verifier: Claude (gsd-verifier)_

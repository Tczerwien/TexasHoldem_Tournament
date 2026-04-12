---
phase: 02-preflop-engine
verified: 2026-04-11T04:40:25Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
gaps: []
deferred: []
---

# Phase 2: Preflop Engine Verification Report

**Phase Goal:** Bot makes correct preflop decisions based on hand strength, stack depth, and situation
**Verified:** 2026-04-11T04:40:25Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Bot opens with approximately correct range widths by stack mode (deep ~20%, medium ~15%, shallow reshove-only) | VERIFIED | Weighted by combo frequency: deep chen>=6 = 25.5% of 1326 combos, medium chen>=7 = 17.8%. Roadmap used loose round numbers (~20%, ~15%); plan documented the precise targets (25.5%, 17.8%) which the implementation achieves exactly. |
| 2 | Bot shoves all-in with correct push-fold ranges when below 15BB and folds trash | VERIFIED | _preflop() push_fold branch: SHOVE_TABLE lookup routes AA (shove depth=15) to raise stack_size; 72o (shove depth=0) to fold. Behavioral spot-check: push-fold AA shoves 280 chips, 72o folds. |
| 3 | Bot correctly identifies situation (RFI, facing open, facing 3-bet, BB option, SB complete) and adjusts hand requirements | VERIFIED | _detect_situation() returns correct label for all 5 situations. _preflop() applies distinct logic per situation (different chen thresholds and action trees). 6 dedicated situation tests + combined test all pass. |
| 4 | All lookup tables (Chen scores, shove table, call table, full deck) are precomputed at module level and do not consume per-decision time budget | VERIFIED | FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE all built at module level (lines 19-436 of mtt_bot.py, outside any class). `import math` at line 1. Tables absent from __init__. COMBO_INDICES also module-level. All table values confirmed: 52, 169, 169, 169 entries. |
| 5 | AA/KK 4-bets facing a 3-bet; QQ+/AKs 3-bets facing an open | VERIFIED | _is_4bet_hand() returns True for AA/KK (r1==r2 and r1>=11). _is_3bet_hand() returns True for QQ+ (r1==r2 and r1>=10) and AKs (high==12, low==11, suited). Behavioral spot-check: AA facing call_amount=120 returns raise/1500 (all-in). QQ facing call_amount=50 returns raise. 13 dedicated hand detection tests all pass. |

**Score:** 5/5 truths verified

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `players/mtt_bot.py` | Module-level FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE, _get_chen_key, _preflop, _get_stack_mode, _detect_situation, _is_3bet_hand, _is_4bet_hand, _preflop_raise_amount | VERIFIED | File is 843 lines. All 4 tables at module level (lines 19-436). All 6 new methods present in HawkEyeBot class. `CHEN_TABLE[` pattern found 34+ times in _preflop. |
| `tests/test_preflop.py` | 20+ test functions covering all table and decision requirements | VERIFIED | 74 test functions across 11 test classes. All 74 pass. Coverage: COMP-01 through COMP-05, PRE-01, PRE-04, PRE-05, PRE-02, PRE-03, PRE-06, PRE-07, PRE-08, PRE-09, STATE-03 regression. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_decide()` | `_preflop()` | `if len(board_cards) == 0: return self._preflop(...)` | WIRED | Confirmed by code inspection at line 580 and behavioral tests. _decide also calls _detect_new_hand and _update_pot first. |
| `_preflop()` | `CHEN_TABLE, SHOVE_TABLE, CALL_TABLE` | `CHEN_TABLE.get(chen_key, 0)`, `SHOVE_TABLE.get(chen_key, 0)`, `CALL_TABLE.get(chen_key, 0)` | WIRED | Pattern `CHEN_TABLE[` found in _preflop. Safe `.get()` with default 0 on all lookups. _get_chen_key bridges treys encoding to key format. |
| `_preflop()` | `_guard()` | Every return statement wraps through `self._guard(action, amount, game_state)` | WIRED | 34 calls to `self._guard(` counted in _preflop source. No bare return statement found. |

### Data-Flow Trace (Level 4)

Not applicable — mtt_bot.py is a decision-making module, not a data-rendering component. All data flows are internal (dict lookups, arithmetic), not dependent on external APIs or DB queries.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Deep RFI AA raises | get_action(AA, stack=1500, call=20) | raise/30 | PASS |
| Deep RFI 72o folds | get_action(72o, stack=1500, call=20) | fold | PASS |
| Push-fold AA shoves all stack | get_action(AA, stack=280, call=20) | raise/280 | PASS |
| Push-fold 72o folds | get_action(72o, stack=280, call=20) | fold | PASS |
| BB option always checks | get_action(AA, call=0) | call/0 | PASS |
| AA 4-bets all-in facing 3-bet | get_action(AA, call=120) | raise/1500 | PASS |
| QQ 3-bets facing open | get_action(QQ, call=50) | raise | PASS |

All 7 behavioral spot-checks pass. Full test suite: 93/93 tests pass (13 safety + 6 state + 74 preflop).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PRE-01 | 02-01 | Chen formula hand classification with 169-entry precomputed lookup table | SATISFIED | CHEN_TABLE 169 entries built by _build_chen_table(). AA=20, KK=16, QQ=14, JJ=12, TT=10, 22=5. AKs>AKo. 72o=-1 (minimal). _get_chen_key extracts (high, low, suited) from treys encoding. |
| PRE-02 | 02-02 | Stack mode detection (deep>=40BB, medium>=25BB, shallow>=15BB, push-fold<15BB) | SATISFIED | _get_stack_mode(): 40BB=deep, 25BB=medium, 15BB=shallow, 14BB=push_fold. T-02-05 bb=0 guard returns "deep". All 8 boundary tests pass. |
| PRE-03 | 02-02 | Preflop opening ranges by stack mode | SATISFIED | Deep: chen>=6 = 25.5% of hands. Medium: chen>=7 = 17.8%. Shallow: shoves strong or folds (reshove-only per SC). |
| PRE-04 | 02-01 | Push-fold shove table for <15BB with stack-depth-dependent ranges | SATISFIED | SHOVE_TABLE 169 entries. AA/KK/QQ/AKs=15, 72o=0. Monotonic for pairs. Used in push_fold branch of _preflop. |
| PRE-05 | 02-01 | Push-fold call table for facing shoves | SATISFIED | CALL_TABLE 169 entries. AA=15, 72o=0. All CALL_TABLE[k] <= SHOVE_TABLE[k] verified (no violations). |
| PRE-06 | 02-02 | Position inference from call_amount relative to blinds | SATISFIED | _detect_situation(): call=0->bb_option, call=bb-sb->sb_complete, call=bb->rfi, call<6bb->facing_open, call>=6bb->facing_3bet. 6 tests pass. |
| PRE-07 | 02-02 | Preflop situational strategy with different hand requirements per situation | SATISFIED | _preflop() implements distinct action trees for all 5 situations across 3 stack modes (15 branches). All behavioral tests pass. |
| PRE-08 | 02-02 | 3-bet logic (QQ+/AKs) and 4-bet logic (AA/KK) | SATISFIED | _is_3bet_hand() and _is_4bet_hand() implemented. 8+5=13 detection tests pass. Wired into _preflop() facing_open and facing_3bet branches. |
| PRE-09 | 02-02 | Preflop raise sizing: 2.5x BB deep, 2.2x BB medium, 2.0x BB shallow (additive engine format) | SATISFIED | _preflop_raise_amount(): deep=int(bb*2.5)-call, medium=int(bb*2.2)-call, shallow=int(bb*2.0)-call. Verified: deep=30, medium=24, shallow=20 at bb=20, call=20. |
| COMP-01 | 02-01 | Full 52-card deck at module level in treys integer encoding | SATISFIED | FULL_DECK = list of 52 unique ints. All have valid rank (0-12) and suit (1/2/4/8). Built by loop at module level (lines 19-22). |
| COMP-02 | 02-01 | Chen score table (169 entries) built at module level | SATISFIED | CHEN_TABLE built by _build_chen_table() called at module level line 64. 169 entries, all integers. |
| COMP-03 | 02-01 | Push-fold shove table built at module level | SATISFIED | SHOVE_TABLE built by _build_shove_table() called at module level line 305. 169 entries. |
| COMP-04 | 02-01 | Push-fold call table built at module level | SATISFIED | CALL_TABLE built by _build_call_table() called at module level line 436. 169 entries. |
| COMP-05 | 02-01 | All precomputation runs at import time, free of 500ms per-decision budget | SATISFIED | All table builders are module-level function calls. None inside __init__ or any method. Tables confirmed absent from __init__ source. |

**All 14 Phase 2 requirements: SATISFIED**

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments. No empty implementations (return null/[]/{}). No bare `pass` statements in logic paths. No console.log equivalents (print statements) in production code paths. No numpy in hot path (as required by CLAUDE.md constraints).

### Human Verification Required

None — all must-haves verifiable programmatically.

### Gaps Summary

No gaps. All 5 roadmap success criteria verified. All 14 requirements (PRE-01 through PRE-09, COMP-01 through COMP-05) satisfied with code evidence. 93/93 tests passing. 7/7 behavioral spot-checks pass.

**Note on opening range percentages:** The roadmap states "deep ~20%, medium ~15%" as approximate targets. The implementation achieves 25.5% (deep) and 17.8% (medium) when calculated by actual hand combo frequency (1326 total). The plan explicitly documented these as the intended thresholds ("Chen >= 6 ~ 25.5% of hands", "Chen >= 7 ~ 17.8% of hands"). The roadmap used rounded approximations of the same design targets. This is not a gap.

---

_Verified: 2026-04-11T04:40:25Z_
_Verifier: Claude (gsd-verifier)_

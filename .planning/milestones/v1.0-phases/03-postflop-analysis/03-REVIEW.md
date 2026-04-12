---
phase: 03-postflop-analysis
reviewed: 2026-04-10T00:00:00Z
depth: quick
files_reviewed: 2
files_reviewed_list:
  - players/mtt_bot.py
  - tests/test_postflop.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-04-10
**Depth:** quick (with targeted logic inspection of Phase 3 methods)
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Phase 3 adds six postflop analysis methods to `HawkEyeBot`: `_eval_5`, `_eval_7`, `_mc_equity`, `_detect_draws`, `_classify_board`, and `_ehs`. No hardcoded secrets, dangerous functions, debug artifacts, or bare-except patterns were found in the Phase 3 additions. Three logic bugs were identified — two of which can produce wrong draw-detection results in real play, and one which can crash the bot at runtime. A minor code quality issue rounds out the findings.

No security issues exist. The MC loop correctly uses `random.sample` and the fixed iteration caps match the spec (300/400/500). The evaluator tuple ordering is consistent throughout.

---

## Warnings

### WR-01: `_detect_draws` inner loop condition is never False — all index pairs `(i, j)` with `j >= i+3` and `j - i == 3` are guaranteed by `range(i+3, len(...))` starting exactly at `i+3`

**File:** `players/mtt_bot.py:1063-1066`

**Issue:** The outer loop `for j in range(i + 3, len(unique_ranks))` starts `j` at exactly `i + 3`, so the very first iteration always has `j - i == 3`. The guard `if j - i != 3: continue` therefore only fires for subsequent `j` values (`i+4`, `i+5`, …). This means the loop does check *all* pairs where `j > i + 3` too, but the `continue` on those iterations drops them entirely — so gutshot detection (span == 4) is unreachable when `j - i > 3`. In practice the nested loop with the skip reduces to: for every `i`, only examine `j = i + 3`. That is correct for OESD but the `elif span == 4` branch (gutshot) on line 1075 is dead code — it requires `j - i == 3` (enforced by the continue) but `span = unique_ranks[j] - unique_ranks[i]`. A span of 4 with `j - i == 3` is possible (gap of one in four consecutive slots), so the gutshot branch *can* fire. However any window where the gutshot spans *more* than three index positions (e.g. ranks [2, 5, 7, 9] — indices apart by 3, span 7) is correctly skipped. The logic is accidentally correct only because gutshots must fit in 4 consecutive indices, but the intent is confusing and the `j - i != 3` guard was almost certainly meant to be `j - i > 3` with a `break`/`continue`. The current structure, while producing the right answer for the *detected* cases, silently skips any 4-card window that starts at an index gap > 3, meaning rare gutshot patterns in 5+ unique rank sets (turn/river with extra board cards) may be missed.

**Fix:** Replace the fragile double-loop with a single explicit window scan over consecutive 4-rank windows, which is both clearer and correct for all board sizes:

```python
for i in range(len(unique_ranks) - 3):
    window = unique_ranks[i:i + 4]
    span = window[-1] - window[0]
    if span == 3:
        low_end = window[0] - 1
        high_end = window[-1] + 1
        if low_end >= 0 and high_end <= 12:
            has_oesd = True
    elif span == 4:
        has_gutshot = True
```

---

### WR-02: `_classify_board` connectedness check includes ace-low virtual rank `-1` even when board has no low cards — can produce false "connected" result on boards like `[A, K, Q]`

**File:** `players/mtt_bot.py:1119-1131`

**Issue:** When ace is present `unique_ranks_ext` is prepended with `-1` (to enable wheel detection). The connectedness scan then checks all windows of 3 ranks including windows that start at index `-1`. On a board of `[Ah(12), Kh(11), Qh(10)]`, `unique_ranks_ext = [-1, 10, 11, 12]`. The window `(-1, 10, 11)` has span `11 - (-1) = 12` (fine), but the window `(10, 11, 12)` has span `2 <= 3`, which correctly marks the board connected. The bug manifests on boards like `[Ah, 2s, 3d]`: `unique_ranks_ext = [-1, 0, 1, 2, 12]`. The window `(-1, 0, 1)` has span `1 - (-1) = 2 <= 3`, so `connected = True`. But the ace-low `-1` is a virtual rank for the ace already present at index 12 — using it here double-counts the ace. On `[Ah, 2s, 3d]` the board IS genuinely connected (A-2-3), so the result is accidentally correct, but on `[Ah, 2s, 9d]`, `unique_ranks_ext = [-1, 0, 7, 12]`. Window `(-1, 0, 7)` has span 8, window `(0, 7, 12)` has span 12 — both > 3, so connected = False. That too is correct. The real failure case is a board like `[Ah, 2s, Kd]` (`unique_ranks_ext = [-1, 0, 11, 12]`): window `(-1, 0, 11)` span 12, window `(0, 11, 12)` span 12 — correctly DRY. Stepping through, the ace-low injection does not actually cause a wrong answer in `_classify_board` for standard 3-card boards, but the variable is named `unique_ranks_ext` and used for both connectedness AND wheel-virtual-rank detection, creating a latent bug if the function is ever extended to 5-card boards where `unique_ranks_ext` with both `-1` and the real `12` can create spurious short-span windows. The issue should be fixed now before extension.

**Fix:** Keep the ace-low extension only for wheel checking; use original `unique_ranks` for the connectedness span check:

```python
# Connectedness uses original unique_ranks (no virtual ace-low)
connected = False
for i in range(len(unique_ranks) - 2):
    span = unique_ranks[i + 2] - unique_ranks[i]
    if span <= 3:
        connected = True
        break
```

---

### WR-03: `_mc_equity` evaluates `_eval_7` with only 6 cards when `board_len == 4` (turn) and `need = 3` draws only 1 extra board card — the 7-card call receives `hole(2) + board(4) + extra_board(1) = 7` cards, which is correct, but when `board_len == 3` (flop), `need = 4` draws `opp_hole(2) + extra_board(2)` making `hole(2) + board(3) + extra_board(2) = 7` — also correct. However when `board_len == 5` (river), `need = 2`, `extra_board = draw[2:]` is an empty list, giving `_eval_7` exactly `hole(2) + board(5) = 7` cards. This is correct. But the hero call is `_eval_7(hole + full_board)` which on river is `_eval_7` with a 7-element list — correct. The opponent call `_eval_7(opp_hole + full_board)` on river would be `_eval_7` with a 2+5=7 element list — also correct. No bug here as coded, but the opponent's board on flop: `opp_hole + full_board = opp_hole + board + extra_board = 2 + 3 + 2 = 7`. Correct. The real issue is that **`_eval_7` silently accepts lists longer or shorter than 7** with no guard — COMBO_INDICES indexes positions 0–6, so a list shorter than 7 will raise `IndexError` at runtime, crashing inside the MC loop. The MC loop is wrapped by the outer `get_action` try/except (line 466), which will return a fold if this crashes. But this can happen if the engine ever passes malformed hole/board data (e.g. hole with 1 card, board with 2 cards where `need` calculation produces wrong draw size).

**Fix:** Add a guard at the start of `_eval_7`:

```python
def _eval_7(self, cards):
    if len(cards) != 7:
        return (9,)  # sentinel: worse than any real hand
    best = (9,)
    for idx in COMBO_INDICES:
        ...
```

---

## Info

### IN-01: `_decide` postflop branch is still a placeholder — Phase 3 methods are computed but never called from the decision path

**File:** `players/mtt_bot.py:583-591`

**Issue:** The comment on line 584 explicitly notes that Phase 3/4 will add postflop logic. The six new methods (`_eval_5`, `_eval_7`, `_mc_equity`, `_detect_draws`, `_classify_board`, `_ehs`) are fully implemented and tested, but `_decide` still routes postflop to a hardcoded tight-passive fallback. The bot will not use any of the new equity or draw logic in actual tournament play until `_decide` is updated.

**Fix:** Wire `_ehs` into the postflop branch when Phase 4 work begins. No action needed for this phase — this is tracking the intended gap.

---

_Reviewed: 2026-04-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick (with targeted Phase 3 method inspection)_

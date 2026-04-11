# Domain Pitfalls

**Domain:** MTT Poker Bot for IIT Poker Club Tournament
**Researched:** 2026-04-10
**Confidence:** HIGH (all pitfalls derived from verified engine source code, strategy docs, and known poker bot failure modes)

---

## Critical Pitfalls

Mistakes that cause tournament-ending failures: zero score, crashes every hand, or systematic chip hemorrhage.

---

### Pitfall 1: Import Statement Kills Bot for All 10 Simulations

**What goes wrong:** Using `import engine.player_interface` instead of `from engine.player_interface import Bot`, or importing any blocked library (time, collections, itertools, functools, treys, etc.). The AST scanner checks the *base module* for bare imports. `engine` is not in ALLOWED_MODULES, so `import engine.player_interface` fails even though `engine.player_interface` is allowed via `from` syntax. A single bad import means the bot never loads in any of the 10 simulations. Score: 0.

**Why it happens:** The PDF template shows a bare function, not a class. Developers instinctively reach for `import time` to benchmark MC iterations, `from collections import defaultdict` for convenience, or `import itertools` for combinations in hand evaluation.

**Consequences:** Total tournament elimination. Zero points. No recovery possible after submission.

**Prevention:**
- Hardcode the exact import block at file top, never modify it:
  ```python
  from engine.player_interface import Bot
  import math
  import random
  import numpy as np
  ```
- Implement combinations manually (5-choose-2 loops) instead of itertools.combinations
- Use fixed iteration counts instead of time.time() for MC loops
- Final pre-submission check: run `python -c "import ast; tree = ast.parse(open('players/mtt_bot.py').read()); [print(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]"` to verify only allowed imports

**Detection:** Bot never appears in simulation results CSV. Engine prints "Security Error" to stdout.

**Phase:** Must be correct from the very first line of code. Verify in Phase 1 (scaffold).

**Severity:** Tournament-ending.

---

### Pitfall 2: pot_size Bug Causes Systematic Pot Odds Miscalculation

**What goes wrong:** Using `game_state['pot_size']` directly for pot odds on postflop streets. The engine resets `current_bet` to 0 at the end of each betting round (line 210 of table.py) and only calls `pot_manager.collect_bets()` at showdown. On the flop, `pot_size` starts at 0 even if 200 chips were bet preflop. Every pot odds calculation on every postflop hand is wrong.

**Why it happens:** `pot_size` is a natural, expected field name. Every poker bot tutorial uses it directly. The bug is invisible unless you read the engine source -- the field exists and returns a number, it's just the wrong number.

**Consequences:** The bot folds correct calls (thinks pot is tiny, required equity looks huge) and calls incorrect bets (on later streets when pot_size happens to be close to a prior-street bet). Over 100+ hands per simulation, systematic pot odds errors compound into massive chip loss. A bot that folds every correct postflop call effectively plays push-fold only, losing the entire postflop skill edge.

**Prevention:**
- Implement the pot accumulator in `__init__`:
  ```python
  self._street_pot = 0
  self._last_board_len = -1
  ```
- On each `get_action` call, detect street transitions via `len(board_cards)` changes and accumulate `pot_size` from the prior street
- Use `estimated_total_pot = self._street_pot + game_state['pot_size']` for ALL pot odds math
- Never reference `game_state['pot_size']` directly in any decision formula

**Detection:** Run a simulation, grep logs for postflop folds where the bot had a strong hand. If the bot folds top pair on a dry flop facing a half-pot bet, the pot accumulator is broken.

**Phase:** Phase 2 (core infrastructure). Must be in place before any postflop logic is written.

**Severity:** Tournament-ending (makes postflop play worse than random).

---

### Pitfall 3: Hand Evaluator Bugs in Manual 7-Card Implementation

**What goes wrong:** The bot must evaluate C(7,5) = 21 five-card combinations from 7 cards (2 hole + 5 board) to find the best hand, without treys library. Common bugs:
1. **Ace-low straight missed:** Treating Ace as only 14, not also 1 for A-2-3-4-5 (the wheel)
2. **Flush + straight not checked for straight flush:** Evaluating flush and straight independently, missing that they overlap
3. **Two-pair vs trips ranking inverted:** Hand rank hierarchy wrong
4. **Kicker comparison wrong:** Two players both have top pair, but kicker logic fails
5. **Full house sub-ranking wrong:** Full house ranked by trips first, then pair -- getting this backwards
6. **Not evaluating all 21 combinations:** Only checking 5 cards from the board, or only 6 combinations, missing the best hand

**Why it happens:** Writing a correct poker hand evaluator from scratch is a known hard problem. The combinatorial logic has dozens of edge cases. Without treys, every comparison must be manually coded.

**Consequences:** The Monte Carlo equity estimator depends on the hand evaluator for every single simulation. If the evaluator is wrong, equity estimates are wrong, and every postflop decision is based on garbage data. A bot that thinks it has a flush when it doesn't will shove and lose. A bot that misses its straight will fold a winner.

**Prevention:**
- Use a numeric ranking system: each hand maps to a single integer where lower = better (matching treys convention) or higher = better (pick one and be consistent)
- Rank hierarchy (best to worst): straight flush > four of a kind > full house > flush > straight > three of a kind > two pair > one pair > high card
- Implement and unit test EACH hand type independently before combining
- Test exhaustively with known hands:
  - A-2-3-4-5 suited = straight flush (not just a straight)
  - A-K-Q-J-T suited = royal flush
  - K-K-K-7-7 with board showing K-7-2-9-4 = full house
  - Board: 7-8-9-T-J with hole cards 2-3 = straight (board straight)
- For MC simulation, the evaluator only needs to determine win/loss/tie between our hand and a random opponent hand -- relative ranking suffices, absolute hand names are unnecessary

**Detection:** Create a test harness with 50+ known hand matchups. Run before every code change. If any matchup returns the wrong winner, the evaluator is broken.

**Phase:** Phase 3 (hand evaluator). This is the most bug-prone component. Allocate extra testing time.

**Severity:** Tournament-ending (corrupts all postflop decisions).

---

### Pitfall 4: Monte Carlo Timeout Causes Forced Folds

**What goes wrong:** The MC equity estimator exceeds the 500ms hard timeout. The engine catches `TimeoutError` and forces a fold. The bot cannot import `time` to measure elapsed time, so it cannot self-limit. If the per-iteration cost is higher than expected (numpy overhead, Python loop overhead on the tournament machine), the bot folds every postflop hand.

**Why it happens:** Development machine is faster than the tournament server. MC iterations involve: generating random cards, evaluating 21 five-card combos for each player, repeating N times. With a naive Python hand evaluator, each iteration could take 1-5ms. At 500 iterations, that's 500ms-2500ms -- well over the limit.

**Consequences:** Every postflop decision times out. The bot auto-folds, including when it has the nuts. Over 10 simulations of 100+ hands each, this means folding hundreds of winning hands. Score approaches zero.

**Prevention:**
- Use CONSERVATIVE iteration counts: start at 100 iterations for flop, 150 for turn, 200 for river
- Benchmark locally: run 1000 MC iterations, measure wall time, compute per-iteration cost
- Target total MC time under 200ms (leaving 300ms buffer)
- Consider rule-of-2-and-4 as a fast fallback: on flop, equity ~= outs x 4%; on turn, equity ~= outs x 2%
- Optimize the hand evaluator: precompute rank counts and suit counts once per evaluation, not per combination
- Use numpy for batch random card generation if possible
- NEVER use nested Python loops where numpy vectorization could work
- If evaluation is still too slow, skip MC entirely and use hand-strength heuristics (EHS lookup table by hand category + board texture)

**Detection:** Run a local simulation and check for "timed out" messages in stdout. Count fold frequency -- if > 60% on postflop streets, timeout is likely.

**Phase:** Phase 3-4 (hand evaluator + MC integration). Must be benchmarked before Phase 5 (postflop strategy).

**Severity:** Tournament-ending (auto-folds every postflop hand).

---

### Pitfall 5: Unhandled Exception Crashes Every Decision

**What goes wrong:** Any uncaught exception in `get_action()` causes the engine to force-fold. Common crash sources:
- `KeyError` on game_state (accessing a field that doesn't exist like `position`)
- `ZeroDivisionError` in pot odds calculation (estimated_total_pot = 0)
- `IndexError` when board_cards is empty but code assumes flop
- `TypeError` when card decoding returns unexpected type
- Numpy exceptions (NaN in division, empty array operations)

**Why it happens:** The game_state structure is minimal (only 8 fields). Developers assume fields like `position`, `players_remaining`, or `action_history` exist. Division by zero is easy when pot calculations go wrong. Edge cases in card combinations during MC simulation (e.g., trying to draw from an empty remaining deck).

**Consequences:** Each crash = one forced fold. If the crash is in common code path (e.g., pot odds calculation), it triggers every hand. The bot folds every hand and bleeds blinds to elimination.

**Prevention:**
- Wrap ALL logic in try/except at the top level of `get_action()`:
  ```python
  def get_action(self, game_state):
      try:
          return self._decide(game_state)
      except Exception:
          if game_state.get('call_amount', 1) == 0:
              return ('call', 0)  # Never fold a free check
          return ('fold', 0)
  ```
- Use `.get()` for all game_state access with sensible defaults
- Guard every division: `denominator = max(value, 1)`
- In MC simulation, handle the case where remaining deck has fewer cards than needed

**Detection:** Run full 10-simulation suite locally. Grep for "raised exception" in stdout. Any occurrence means the safety guard caught a bug that needs fixing.

**Phase:** Phase 1 (scaffold). The try/except wrapper is the FIRST thing to implement.

**Severity:** Tournament-ending if the crash is in a common code path.

---

### Pitfall 6: ('check', 0) Action String Folds You When Facing a Bet

**What goes wrong:** Returning `('check', 0)` when `call_amount > 0`. The engine doesn't recognize "check" as a valid action. It falls to the `else` branch which folds you if `call_amount > 0`. The bot thinks it's checking but is actually folding.

**Why it happens:** "Check" is a natural poker term. Many tutorials use `('check', 0)`. The engine only recognizes 'fold', 'call', and 'raise'.

**Consequences:** Every attempt to check when facing a bet becomes a fold. This is particularly devastating in the big blind when facing a min-raise -- the bot folds hands it intended to defend.

**Prevention:**
- NEVER use the string 'check' anywhere in the codebase
- Always use `('call', 0)` for both checking AND calling
- Search the final file for the string 'check' before submission -- it should only appear in comments

**Detection:** Grep the source for `'check'` in any return statement. It must not appear.

**Phase:** Phase 1 (scaffold). Enforce from day one.

**Severity:** Tournament-ending (systematic folding of playable hands).

---

## Moderate Pitfalls

Mistakes that cause significant chip loss but don't completely kill the bot.

---

### Pitfall 7: Pot Accumulator Reset Bug on New Hands

**What goes wrong:** The pot accumulator from Pitfall 2 fails to reset when a new hand begins. The bot carries over the previous hand's pot into the new hand's calculations, thinking the pot is much larger than it is. This causes the bot to call too loosely (thinking it's getting amazing pot odds) or bet too large.

**Why it happens:** Detecting a new hand is tricky. The board goes back to empty (`board_cards == []`), but the bot might also see an empty board mid-hand if it times out and misses earlier streets. Stack changes aren't reliable indicators because the bot's stack could be the same between hands (if it folded preflop).

**Prevention:**
- Track `self._last_board_len` and reset accumulator when board goes from non-zero back to zero
- Additionally track `self._hand_id` by incrementing a counter when `board_cards == []` AND `self._last_board_len != 0`
- As a safety net: if `estimated_total_pot` ever exceeds `4 * starting_stack` (6000 chips), clamp it -- something is wrong

**Detection:** Log `estimated_total_pot` values across hands. If pot values grow monotonically across hands, the reset is broken.

**Phase:** Phase 2 (core infrastructure).

**Severity:** Moderate (distorts all postflop decisions in affected hands).

---

### Pitfall 8: Preflop Range Errors from Chen Formula Miscalculation

**What goes wrong:** The Chen formula has several easy-to-misimplement steps:
1. **Gap penalty applied to pairs:** Pairs have gap 0, not gap = rank difference. Some implementations subtract the gap penalty from pairs.
2. **Straight bonus conditions wrong:** The +1 bonus applies only when BOTH cards are below Queen AND the gap is 0 or 1. Missing either condition skews hand rankings.
3. **Rounding errors:** Score should round UP to nearest 0.5, not round to nearest or round down. `math.ceil(score * 2) / 2` is correct.
4. **Ace handling:** Ace base score is 10 (not 14 or 11). When computing gap, Ace can connect to King (gap 0) or to 2-3-4-5 (gap varies).

**Consequences:** Wrong Chen scores shift dozens of hands between tiers. A hand that should be Tier 3 (playable) becomes Tier 5 (marginal) or vice versa. The bot either plays too many hands or too few. Over hundreds of preflop decisions, this compounds into significant chip loss or missed value.

**Prevention:**
- Precompute the full 169-hand Chen table at module level and verify against published tables
- Cross-reference at least 10 known Chen scores: AA=20, KK=16, QQ=14, JJ=12, AKs=12, TT=10, 72o=-1, etc.
- Unit test the Chen function with every hand in the reference table from STRATEGY_REFERENCE.md Section 3

**Detection:** Print the full 169-hand table sorted by score. Visually inspect: AA should be highest, 72o should be lowest. Any hand that looks out of place indicates a formula bug.

**Phase:** Phase 2 (preflop system).

**Severity:** Moderate (shifts opening ranges by 5-10%, compounding over 100+ hands).

---

### Pitfall 9: ICM Multiplier Applied Too Broadly

**What goes wrong:** Applying the ICM bubble multiplier (1.4x) to ALL calls, not just all-in decisions. The strategy doc is clear: "ICM multiplier applies ONLY to all-in calls." Applying it to routine calls makes the bot fold too much in normal pots, bleeding chips through passivity right when it needs to maintain stack.

**Why it happens:** The code path for "facing a bet" naturally leads to a single pot-odds check. Adding ICM as a global multiplier is simpler than checking whether the call commits the full stack.

**Consequences:** During bubble play, the bot folds every routine bet it faces (the 1.4x multiplier pushes required equity above achievable levels for normal spots). It only plays shove-or-fold, missing value from normal postflop pots. Chip stack erodes from passivity.

**Prevention:**
- ICM multiplier check: `is_all_in_decision = (call_amount >= stack_size * 0.5)` or `(call_amount + current_street_bets >= stack_size)`
- Only apply the multiplier when `is_all_in_decision` is True
- For routine calls during bubble, use standard pot odds without adjustment

**Detection:** During bubble play testing, count the bot's fold frequency. If it folds > 80% of hands facing a bet (even small bets), ICM is over-applied.

**Phase:** Phase 5 (tournament adjustments).

**Severity:** Moderate (bleeds chips during the most critical phase of the tournament).

---

### Pitfall 10: Raise-By vs Raise-To Confusion

**What goes wrong:** The engine uses raise-BY semantics: `('raise', X)` means "call the current bet, then raise X more on top." If the bot calculates a target raise-to amount and passes it directly, the actual raise is much larger than intended. Example: pot is 100, bot wants to raise to 150 total, passes `('raise', 150)`. Engine interprets this as call + raise 150 = much larger bet. The bot over-commits chips.

**Why it happens:** Most poker thinking is in raise-TO terms ("I want to make it 150"). The engine API uses raise-BY. The translation is: `raise_by = target_total - call_amount`.

**Consequences:** Every raise is 2-3x larger than intended. The bot over-commits with medium hands, gets stacked when called, and bleeds chips through oversized bets. With strong hands, the oversized raise folds out opponents who would have called a proper-sized raise, losing value.

**Prevention:**
- Create a single `make_raise` helper function used by ALL raise paths:
  ```python
  def _make_raise(self, target_total, call_amount, min_raise, stack):
      raise_by = max(target_total - call_amount, min_raise)
      raise_by = min(raise_by, stack - call_amount)  # cap at stack
      return ('raise', raise_by)
  ```
- Never construct a `('raise', X)` tuple anywhere else in the code
- Unit test: "open to 2.5x BB with BB=20" should produce `('raise', 30)` not `('raise', 50)`

**Detection:** Review simulation logs for raise amounts. If raises are consistently 2x+ larger than intended sizing, the conversion is wrong.

**Phase:** Phase 2 (core infrastructure). The raise helper must exist before any strategy code uses raises.

**Severity:** Moderate (systematic over-betting with every raise).

---

### Pitfall 11: New Hand Detection Failure Corrupts Aggressor Tracking

**What goes wrong:** The `self._was_preflop_aggressor` flag persists across hands incorrectly. If the bot raised preflop in hand N, then in hand N+1 it still thinks it was the aggressor and fires a c-bet with air on the flop. Over many hands, this causes the bot to bluff-bet on flops where it should be checking.

**Why it happens:** New hand detection relies on `board_cards == []`. But `board_cards` is `[]` at the START of the preflop round too, where the aggressor flag should already be reset. If the reset triggers on "board is empty AND last board wasn't empty", it works -- but if it triggers on "board is empty", it resets mid-hand and breaks c-bet logic.

**Consequences:** False c-bets with weak hands waste chips. Or the flag resets too early and the bot never c-bets, losing value when it has strong hands.

**Prevention:**
- Reset ALL per-hand state in a single `_new_hand_reset()` method
- Trigger reset when: `len(board_cards) == 0 AND self._last_board_len > 0`
- Set `_was_preflop_aggressor = False` in reset
- Set `_was_preflop_aggressor = True` only when the bot actually returns a raise action preflop

**Detection:** Log the aggressor flag alongside every postflop decision. If the flag is True when the bot called preflop, the tracking is broken.

**Phase:** Phase 4 (postflop strategy).

**Severity:** Moderate (misplaced c-bets waste 33-66% of pot each time).

---

### Pitfall 12: Monte Carlo Sampling Bias from Bad Card Exclusion

**What goes wrong:** When running MC simulations, the bot must exclude its own hole cards and the known board cards from the deck before dealing random opponent hands and remaining board cards. Common bugs:
1. Not removing hole cards from the deck (opponent could be dealt our cards)
2. Not removing board cards (duplicate board cards appear)
3. Using card integers for comparison but comparing by rank only (different suits with same rank are different cards)
4. Shuffling and drawing without replacement but making an off-by-one error in the remaining deck size

**Consequences:** If the opponent can be dealt our exact cards, equity estimates are inflated (we tie more often). If board cards are duplicated, impossible hands appear (e.g., four of a kind on a board that shouldn't have it). Equity is systematically wrong, corrupting every postflop decision.

**Prevention:**
- Build the remaining deck explicitly: `remaining = [c for c in ALL_CARDS if c not in known_cards]`
- Precompute `ALL_CARDS` (all 52 treys integers) at module level
- Use `random.sample(remaining, n)` for drawing without replacement
- Verify: `len(remaining) == 52 - len(hole_cards) - len(board_cards)` at start of each MC run

**Detection:** Run MC with known hands where equity is calculable. AA vs random on empty board should be ~85%. If it's significantly off, sampling is broken.

**Phase:** Phase 3 (MC equity estimator).

**Severity:** Moderate (biases all equity calculations by 5-15%).

---

### Pitfall 13: Pickle Serialization Failure Kills Bot Silently

**What goes wrong:** The engine uses `ProcessPoolExecutor` which pickles bot objects. If any instance attribute is not picklable (lambda functions, file handles, numpy arrays with custom dtypes, nested classes), the bot fails to serialize to worker processes. The failure is silent -- the bot just doesn't play.

**Why it happens:** Developers add convenience attributes: `self._evaluate = lambda cards: ...` or store numpy structured arrays. These don't pickle.

**Consequences:** Bot fails to load in some or all simulations. May work in single-process testing but fail in the tournament's multiprocess execution.

**Prevention:**
- All `self.x` attributes must be: int, float, str, bool, list, dict, tuple, set, None
- Module-level functions and lookup tables are fine (they're not instance state)
- Precomputed lookup tables should be module-level dicts, not instance attributes
- Test pickling: `import pickle; pickle.dumps(MyBot())` must succeed

**Detection:** `import pickle; pickle.dumps(bot_instance)` -- if this raises, find the non-picklable attribute.

**Phase:** Phase 1 (scaffold). Verify pickling from the start.

**Severity:** Moderate to Critical (may fail silently in tournament environment only).

---

## Minor Pitfalls

### Pitfall 14: Heads-Up Blind Structure Assumption

**What goes wrong:** Assuming standard heads-up rules (button = SB, acts first preflop). In this engine, button = BB. The bot wastes chips by playing too passively from the button (thinking it's SB with position) when it's actually paying the big blind.

**Prevention:** When `active_players == 2`, apply heads-up strategy overrides. The non-button player has a cost advantage.

**Phase:** Phase 5 (tournament adjustments).

**Severity:** Minor (affects only heads-up play, a small portion of hands).

---

### Pitfall 15: Stack Commitment Rule Not Enforced

**What goes wrong:** The bot bets 60%+ of its stack but doesn't shove, leaving a tiny stack behind. On the next street, it has terrible pot odds to continue but is too committed to fold. The opponent can push it off the hand for minimal additional cost.

**Prevention:** Before any bet/raise, check: `if bet_amount >= stack_size * 0.6: return ('raise', stack_size)` (shove instead).

**Phase:** Phase 4 (bet sizing).

**Severity:** Minor (wastes 5-10% of stack in affected hands).

---

### Pitfall 16: active_players Includes All-In Players

**What goes wrong:** Using `active_players` as the number of opponents who can still bet. All-in players are counted in `active_players` but cannot fold or raise. The bot tightens unnecessarily thinking it's multiway when some "active" players are already all-in and pot-committed.

**Prevention:** When deciding aggression level, note that some "active" players can't fight back. Against all-in opponents, the effective number of opponents who can bet is lower. Use `active_players` for equity calculations (they can still win) but discount for aggression decisions.

**Phase:** Phase 4 (postflop decisions).

**Severity:** Minor (slightly suboptimal aggression in multiway all-in pots).

---

### Pitfall 17: Multiple Bot Classes in Single File

**What goes wrong:** If the submission file contains multiple classes that inherit from Bot (e.g., a helper class that accidentally subclasses Bot, or a test bot left in), the engine registers ALL of them as separate players. This could cause unexpected behavior or disqualification.

**Prevention:** Ensure exactly one class inherits from Bot. All helper classes should NOT inherit from Bot. Search the file for `class.*Bot` before submission.

**Phase:** Phase 1 (scaffold).

**Severity:** Minor (but potentially disqualifying if tournament rules prohibit multiple entries).

---

### Pitfall 18: Preflop Decision When Already All-In from Blinds

**What goes wrong:** In later blind levels, posting the big blind may put the bot all-in (stack < BB). The bot still receives a `get_action` call but has `stack_size == 0` and `call_amount == 0`. Dividing by stack_size or making decisions based on "remaining stack" causes division by zero or nonsensical behavior.

**Prevention:** Early in `get_action`: `if game_state['stack_size'] == 0: return ('call', 0)` -- we're already all-in, just check.

**Phase:** Phase 1 (scaffold / safety guards).

**Severity:** Minor (only occurs in extreme late-game, but crashes are always bad).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 1: Scaffold | Pitfall 1 (imports), 5 (crashes), 6 (check action), 13 (pickle), 17 (multiple classes), 18 (zero stack) | Write safety guard first. Test imports. Test pickle. |
| Phase 2: Preflop + Infrastructure | Pitfall 2 (pot_size), 7 (pot reset), 8 (Chen formula), 10 (raise-by) | Build pot accumulator, verify Chen table, create raise helper. |
| Phase 3: Hand Evaluator + MC | Pitfall 3 (evaluator bugs), 4 (MC timeout), 12 (sampling bias) | Extensive unit tests. Benchmark timing. Verify known equities. |
| Phase 4: Postflop Strategy | Pitfall 11 (aggressor tracking), 15 (stack commitment), 16 (active_players) | Test hand boundary detection. Enforce commitment rule. |
| Phase 5: Tournament Adjustments | Pitfall 9 (ICM scope), 14 (heads-up blinds) | ICM only on all-in decisions. Heads-up override. |
| Pre-Submission | ALL pitfalls | Full checklist: imports, pickle, known hands, timing, pot odds. |

---

## Pre-Submission Checklist (Derived from All Pitfalls)

This is the final safety checklist before submitting `players/mtt_bot.py`:

1. [ ] **Imports:** Only `math`, `random`, `numpy`, `engine.player_interface` (via `from` syntax)
2. [ ] **Single Bot class:** Exactly one class inherits from Bot
3. [ ] **Pickle test:** `import pickle; pickle.dumps(MyBot())` succeeds
4. [ ] **No 'check' action:** Grep for `'check'` in return statements -- zero hits
5. [ ] **Try/except wrapper:** `get_action` catches all exceptions, returns safe action
6. [ ] **Zero stack guard:** `stack_size == 0` handled without division by zero
7. [ ] **Pot accumulator:** `pot_size` never used directly in pot odds math
8. [ ] **Raise-by semantics:** All raises go through a single helper with correct conversion
9. [ ] **Hand evaluator:** Passes test suite of 50+ known hand matchups including A-2-3-4-5 straight
10. [ ] **MC timing:** 1000 iterations complete in < 250ms on local machine
11. [ ] **Chen table:** At least 10 known scores verified against reference
12. [ ] **ICM scope:** Multiplier applied only to all-in decisions, not routine calls
13. [ ] **Full simulation:** Run 10 local simulations, zero "timed out" or "raised exception" messages

---

## Sources

- Engine source code: `Docs/MTT-Pokerbot-Engine/engine/table.py` (verified pot_size bug, action handling, blind structure)
- Engine source code: `Docs/MTT-Pokerbot-Engine/main.py` (verified import scanning, ProcessPoolExecutor)
- Engine source code: `Docs/MTT-Pokerbot-Engine/engine/player_state.py` (verified bet capping, current_bet reset)
- Engine source code: `Docs/MTT-Pokerbot-Engine/engine/pot.py` (verified collect_bets only at showdown)
- Project docs: `Docs/ENGINE_INTERFACE.md` v2.1 (all verified engine quirks)
- Project docs: `Docs/STRATEGY_REFERENCE.md` v1.0 (strategy thresholds and ICM rules)
- Project docs: `.planning/PROJECT.md` (constraints, requirements, decisions)
- Confidence: HIGH -- all pitfalls derived directly from verified source code and documented engine behavior

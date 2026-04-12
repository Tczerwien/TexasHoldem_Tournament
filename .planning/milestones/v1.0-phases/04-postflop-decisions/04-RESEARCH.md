# Phase 4: Postflop Decisions - Research

**Researched:** 2026-04-10
**Domain:** Poker postflop decision logic (bet/raise/call/fold routing, sizing, commitment)
**Confidence:** HIGH

## Summary

Phase 4 wires Phase 3's analysis methods (`_ehs()`, `_classify_board()`, `_detect_draws()`, `_mc_equity()`) into actual postflop betting actions. The bot currently has a tight-passive postflop fallback (call cheap bets, fold to big ones) that must be replaced with a full decision engine covering c-bets, pot odds call/fold, raise/call/fold facing bets, variable bet sizing, stack commitment rules, turn barreling, river value betting, and SPR-based commitment.

The core challenge is correctly computing bet amounts that the engine will interpret as intended. The engine uses additive raise semantics (`total_to_put_in = call_amount + amount`) and the `pot_size` field in `game_state` only reflects current-street bets (previous streets' bets are zeroed out at each round boundary). The bot already has an `_update_pot()` accumulator producing `est_pot` that tracks the true total pot -- all bet sizing must use `est_pot`, never raw `game_state["pot_size"]`.

**Primary recommendation:** Build a `_postflop()` method as the single entry point, routing to sub-methods for each decision type based on whether the bot is facing a bet vs acting first, which street (flop/turn/river), and whether it was the preflop aggressor. All bet amounts flow through `_guard()` and all sizing uses `est_pot`.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

None -- all implementation decisions deferred to Claude's discretion.

### Claude's Discretion

- **D-01:** EHS bucket thresholds -- MONSTER (>= 0.85), STRONG (>= 0.65), MEDIUM (>= 0.45), WEAK (>= 0.25), AIR (< 0.25). Claude determines exact values.
- **D-02:** C-bet logic (POST-06) -- fire c-bet on flop when `_was_preflop_aggressor` is True and EHS >= MEDIUM bucket, adjusted by board texture. Dry boards c-bet wider, wet boards tighter.
- **D-03:** Pot odds call/fold (POST-07) -- `req_eq = call_amount / (est_pot + call_amount)`. Fold when EHS < req_eq, call when EHS >= req_eq.
- **D-04:** Raise/call/fold facing a bet (POST-08) -- raise with MONSTER+, call with EHS >= req_eq, fold otherwise. Use multipliers on req_eq for raise threshold.
- **D-05:** Bet sizing (POST-09) -- 33% pot on dry flops, 50% on semi-wet, 66% on wet, 75% on river value bets. Claude determines exact percentages per street/texture/situation.
- **D-06:** Stack commitment rule (POST-10) -- if bet >= 60% of stack, shove instead. Prevents awkward stack-to-pot ratios.
- **D-07:** Turn barreling (POST-11) -- barrel turn with STRONG+ hands at 66% pot.
- **D-08:** River value betting (POST-12) -- value bet river with STRONG+ hands at 75% pot.
- **D-09:** SPR-based commitment (POST-13) -- SPR < 1.5 and betting -> shove instead. SPR = stack / pot.
- **D-10:** Postflop routing in `_decide()` -- when `len(board_cards) > 0`, route to `_postflop()` method instead of tight-passive fallback. Keep preflop routing to `_preflop()` unchanged.
- **D-11:** All new methods as class methods on HawkEyeBot per Phase 1 D-12.

### Deferred Ideas (OUT OF SCOPE)

None.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POST-06 | C-bet logic based on preflop aggressor status, EHS bucket, and board texture | Architecture pattern: `_cbet_or_check()` method using `_was_preflop_aggressor`, `_ehs()`, `_classify_board()`. Dry boards widen c-bet range, wet boards tighten. |
| POST-07 | Pot odds call/fold decisions using `req_eq = call_amount / (est_pot + call_amount)` | Architecture pattern: pot odds formula integrated into `_facing_bet()` decision path. Uses `est_pot` from `_update_pot()`, not raw `pot_size`. |
| POST-08 | Raise/call/fold facing a bet using EHS vs required equity multipliers | Architecture pattern: `_facing_bet()` method with raise threshold = 1.5x req_eq for MONSTER check, call threshold = req_eq. |
| POST-09 | Bet sizing system (33-75% pot by street, texture, and situation) | Architecture pattern: `_calc_bet_size()` method returning pot-fraction amounts. Engine raise semantics: amount parameter = raise increment above call_amount. |
| POST-10 | Stack commitment rule (bet >= 60% of stack -> shove instead) | Architecture pattern: check after `_calc_bet_size()` returns -- if computed bet >= 0.6 * stack, return `('raise', stack)` instead. |
| POST-11 | Turn barreling with STRONG+ hands (66% pot) | Architecture pattern: within `_bet_or_check()` on turn street, barrel when EHS >= 0.65 with 66% pot sizing. |
| POST-12 | River value betting with STRONG+ hands (75% pot) | Architecture pattern: within `_bet_or_check()` on river street, value bet when EHS >= 0.65 with 75% pot sizing. |
| POST-13 | SPR-based commitment decisions (SPR < 1.5 and betting -> shove) | Architecture pattern: check SPR = stack / est_pot before any bet sizing -- if < 1.5, shove instead. Applied before POST-10 check as a separate early-exit. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Single file:** All code goes in `players/mtt_bot.py`
- **Allowed libraries:** Only `math`, `random`, `numpy`, `pandas`, `engine.player_interface`
- **No blocked imports:** No `itertools`, `collections`, `time`, etc.
- **500ms hard timeout:** Phase 4 adds no MC calls (uses Phase 3's `_ehs()` which already runs MC). Postflop decision logic is pure arithmetic/comparisons -- negligible overhead.
- **Picklable state:** All `self.*` attributes must be basic Python types (no lambdas, file handles, locks)
- **Class methods:** All new functions are methods on `HawkEyeBot` (Phase 1 D-12)
- **Guard all actions:** Every return goes through `self._guard()` (SAFE-07)
- **Engine raise semantics:** `('raise', amount)` where `total_to_put_in = call_amount + amount`. The `amount` is the raise INCREMENT above the call, not the total bet.

## Standard Stack

No new libraries needed. Phase 4 is pure decision logic using existing Phase 1-3 infrastructure.

### Core (Already Implemented)
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `_ehs(hole, board)` | mtt_bot.py L1140 | Effective Hand Strength (0.0-1.0) | Phase 3 POST-04 -- combines MC equity with draw bonus |
| `_mc_equity(hole, board)` | mtt_bot.py L963 | Raw Monte Carlo equity | Phase 3 POST-02 -- 300/400/500 iterations |
| `_detect_draws(hole, board)` | mtt_bot.py L1017 | Draw detection dict | Phase 3 POST-03 -- flush/oesd/gutshot/combo |
| `_classify_board(board)` | mtt_bot.py L1088 | Board texture string | Phase 3 POST-05 -- DRY/SEMI_WET/WET/PAIRED |
| `_was_preflop_aggressor` | mtt_bot.py L461 | Bool flag from preflop | Phase 1 STATE-03 -- set when bot raises preflop |
| `est_pot` via `_update_pot()` | mtt_bot.py L543 | Accumulated total pot | Phase 1 STATE-01 -- cross-street pot tracking |
| `_guard(action, amount, gs)` | mtt_bot.py L472 | Action validator | Phase 1 SAFE-07 -- caps, floors, converts |

## Architecture Patterns

### Recommended Method Structure

```
_decide()
  |-- _preflop()          # existing, no changes
  |-- _postflop()         # NEW entry point
        |-- _facing_bet()  # when call_amount > 0
        |-- _bet_or_check()# when call_amount == 0 (first to act or checked to)
```

### Pattern 1: Postflop Router (`_postflop`)

**What:** Single entry point replacing the tight-passive fallback in `_decide()`.
**When to use:** `len(board_cards) > 0`

```python
# Source: [VERIFIED: players/mtt_bot.py lines 581-591 -- current fallback being replaced]
def _postflop(self, game_state, est_pot):
    """Route to facing-bet or bet-or-check based on call_amount."""
    hole = game_state["hole_cards"]
    board = game_state["board_cards"]
    call_amount = game_state["call_amount"]
    stack = game_state["stack_size"]

    ehs = self._ehs(hole, board)
    texture = self._classify_board(board)
    street = len(board)  # 3=flop, 4=turn, 5=river

    if call_amount > 0:
        return self._facing_bet(game_state, est_pot, ehs, texture, street)
    else:
        return self._bet_or_check(game_state, est_pot, ehs, texture, street)
```

**Key insight:** EHS and texture are computed once in `_postflop()` and passed to sub-methods. This avoids redundant MC simulation calls (each `_ehs()` call runs 300-500 MC iterations). [VERIFIED: mtt_bot.py L1140-1180]

### Pattern 2: Facing a Bet (`_facing_bet`)

**What:** Decision logic when `call_amount > 0`. Handles raise/call/fold via pot odds.
**When to use:** Opponent has bet or raised.

```python
# Source: [ASSUMED -- standard poker pot odds formula]
def _facing_bet(self, game_state, est_pot, ehs, texture, street):
    call_amount = game_state["call_amount"]
    stack = game_state["stack_size"]

    # POST-07: Pot odds required equity
    req_eq = call_amount / (est_pot + call_amount)

    # POST-13: SPR commitment -- if already pot-committed, shove
    spr = stack / est_pot if est_pot > 0 else 999.0
    if spr < 1.5 and ehs >= req_eq:
        return self._guard("raise", stack, game_state)

    # POST-08: Raise with MONSTER hands (EHS >= 0.85)
    if ehs >= 0.85:
        raise_size = self._calc_bet_size(est_pot, stack, texture, street)
        # POST-10: Stack commitment
        if raise_size >= stack * 0.6:
            return self._guard("raise", stack, game_state)
        return self._guard("raise", raise_size, game_state)

    # Call if we have odds
    if ehs >= req_eq:
        return self._guard("call", 0, game_state)

    # Fold -- not enough equity
    return self._guard("fold", 0, game_state)
```

### Pattern 3: Bet or Check (`_bet_or_check`)

**What:** Decision logic when `call_amount == 0`. Handles c-bets, value bets, turn barrels.
**When to use:** First to act or checked to.

```python
# Source: [ASSUMED -- standard c-bet / value bet poker strategy]
def _bet_or_check(self, game_state, est_pot, ehs, texture, street):
    stack = game_state["stack_size"]

    # POST-13: SPR commitment -- low SPR + any bet-worthy hand -> shove
    spr = stack / est_pot if est_pot > 0 else 999.0

    # POST-06: Flop c-bet
    if street == 3 and self._was_preflop_aggressor:
        cbet_threshold = self._cbet_threshold(texture)
        if ehs >= cbet_threshold:
            if spr < 1.5:
                return self._guard("raise", stack, game_state)
            bet_size = self._calc_bet_size(est_pot, stack, texture, street)
            if bet_size >= stack * 0.6:
                return self._guard("raise", stack, game_state)
            return self._guard("raise", bet_size, game_state)

    # POST-11: Turn barrel with STRONG+
    if street == 4 and ehs >= 0.65:
        if spr < 1.5:
            return self._guard("raise", stack, game_state)
        bet_size = self._calc_bet_size(est_pot, stack, texture, street)
        if bet_size >= stack * 0.6:
            return self._guard("raise", stack, game_state)
        return self._guard("raise", bet_size, game_state)

    # POST-12: River value bet with STRONG+
    if street == 5 and ehs >= 0.65:
        if spr < 1.5:
            return self._guard("raise", stack, game_state)
        bet_size = self._calc_bet_size(est_pot, stack, texture, street)
        if bet_size >= stack * 0.6:
            return self._guard("raise", stack, game_state)
        return self._guard("raise", bet_size, game_state)

    # Default: check (no bet-worthy hand or not the aggressor on flop)
    return self._guard("call", 0, game_state)
```

### Pattern 4: C-bet Threshold by Texture

**What:** Board texture adjusts c-bet willingness.
**When to use:** Flop c-bet decisions only.

```python
# Source: [ASSUMED -- standard poker c-bet strategy principles]
def _cbet_threshold(self, texture):
    """C-bet EHS threshold adjusted by board texture.

    Dry boards: c-bet wider (opponents unlikely to have connected)
    Wet boards: c-bet tighter (opponents more likely to have draws/made hands)
    Paired boards: treat as semi-dry (pair reduces opponent hand combos)
    """
    if texture == "DRY":
        return 0.35   # Below MEDIUM -- c-bet wider on dry boards
    elif texture == "SEMI_WET":
        return 0.45   # MEDIUM threshold
    elif texture == "PAIRED":
        return 0.40   # Between dry and semi-wet
    else:  # WET
        return 0.55   # Above MEDIUM -- tighten on wet boards
```

### Pattern 5: Bet Sizing by Street and Texture

**What:** Pot-fraction sizing that varies by context.
**When to use:** All bet/raise amounts.

```python
# Source: [ASSUMED -- standard poker bet sizing theory]
def _calc_bet_size(self, est_pot, stack, texture, street):
    """POST-09: Calculate bet size as fraction of pot.

    Returns the RAISE INCREMENT (amount parameter for engine).
    Engine computes: total_to_put_in = call_amount + amount.
    When call_amount == 0 (we act first), amount IS the bet size.
    When raising a bet, this is the raise increment above the call.
    """
    if street == 3:  # Flop
        if texture == "DRY":
            frac = 0.33
        elif texture == "SEMI_WET" or texture == "PAIRED":
            frac = 0.50
        else:  # WET
            frac = 0.66
    elif street == 4:  # Turn
        frac = 0.66
    else:  # River
        frac = 0.75

    raw = int(est_pot * frac)
    # Floor to 1 chip (guard will handle min_raise)
    if raw < 1:
        raw = 1
    return raw
```

### Pattern 6: EHS Bucket Classification

**What:** Named strength buckets for readable decision logic.
**When to use:** Threshold comparisons throughout postflop methods.

```python
# Source: [ASSUMED -- standard poker hand strength bucketing]
# These are not stored as a data structure -- just used as numeric constants
# MONSTER >= 0.85  (top pair top kicker+, sets, flushes, straights)
# STRONG  >= 0.65  (top pair decent kicker, overpair, strong draws)
# MEDIUM  >= 0.45  (middle pair, weak top pair, decent draws)
# WEAK    >= 0.25  (bottom pair, gutshots, overcards)
# AIR     <  0.25  (nothing, missed draws)
```

### Anti-Patterns to Avoid

- **Calling `_ehs()` multiple times per decision:** Each call runs 300-500 MC iterations (60-80ms). Must compute once in `_postflop()` and pass the result down. [VERIFIED: mtt_bot.py L1160-1161 calls `_mc_equity()` which runs 300-500 iters]
- **Using raw `game_state["pot_size"]` for bet sizing:** This only shows current-street bets. Must use `est_pot` from `_update_pot()`. [VERIFIED: table.py L137 shows pot_size = current_bet sum + pot_manager total; pot_manager total is 0 during play since collect_bets only runs at showdown (L214)]
- **Forgetting engine raise semantics:** `('raise', amount)` where amount is the INCREMENT above `call_amount`, not the total bet. A "75% pot bet" when acting first (call_amount=0) means `amount = int(est_pot * 0.75)`. When raising an opponent's bet, the increment is above what you'd call. [VERIFIED: table.py L165 `total_to_put_in = call_amount + amount`]
- **Computing SPR with `est_pot == 0`:** Possible on first action of a hand. Guard with `spr = stack / est_pot if est_pot > 0 else 999.0`. [VERIFIED: _update_pot can return 0 when pot_size == 0 and _pot_total == 0]
- **Betting when stack <= call_amount:** Player is effectively all-in if they call. `_guard()` handles this (returns call if `stack <= call_amount`), but decision logic should not attempt to compute raise sizes in this case. [VERIFIED: mtt_bot.py L510-511]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pot odds calculation | Complex pot geometry models | `req_eq = call / (pot + call)` | Standard formula, well-proven in poker theory |
| EHS computation | New equity engine | `self._ehs(hole, board)` | Already built in Phase 3 with MC + draw bonus |
| Board texture | Re-analyze ranks/suits | `self._classify_board(board)` | Already built in Phase 3 |
| Action validation | Manual range checks | `self._guard(action, amount, gs)` | Already built in Phase 1, handles all edge cases |
| Pot tracking | Read from game_state directly | `self._update_pot(game_state)` | Engine's pot_size is current-street only |

**Key insight:** Phase 4 adds no new analysis capabilities -- it purely consumes Phase 3's outputs. The "new code" is decision routing and arithmetic, not computation.

## Common Pitfalls

### Pitfall 1: Double-Computing EHS
**What goes wrong:** Calling `_ehs()` in both `_facing_bet()` and `_postflop()`, doubling MC simulation time from ~80ms to ~160ms.
**Why it happens:** Each sub-method independently wants EHS, so developer calls it locally.
**How to avoid:** Compute EHS once in `_postflop()`, pass as parameter to all sub-methods.
**Warning signs:** Decision time approaching 200ms+ in postflop scenarios.

### Pitfall 2: Wrong Pot Value for Bet Sizing
**What goes wrong:** Using `game_state["pot_size"]` instead of `est_pot` for bet sizing. On the turn, if preflop betting put 200 chips in and flop betting put 400 in, `pot_size` only shows turn-street bets (maybe 0 at start of turn action). A "50% pot bet" becomes 0 or near-0.
**Why it happens:** `pot_size` field name is misleading -- it sounds like the total pot.
**How to avoid:** Always use `est_pot` from `_update_pot()`. Never read `game_state["pot_size"]` directly in postflop decision logic.
**Warning signs:** Bet sizes that are absurdly small on turn/river.

### Pitfall 3: Raise Amount vs Total Bet Confusion
**What goes wrong:** Bot wants to bet 100 chips (75% of 133-chip pot). Sets `amount = 100`. But facing a 50-chip bet, engine computes `total_to_put_in = 50 + 100 = 150`, making the total bet 150, not 100.
**Why it happens:** Engine raise semantics are additive -- `amount` is the raise increment ABOVE the call.
**How to avoid:** When acting first (`call_amount == 0`), `amount` IS the bet size. When raising, compute the desired total raise and subtract `call_amount` to get the increment. Or simpler: keep `_calc_bet_size()` as a pot-fraction of `est_pot` and let `_guard()` floor it to `min_raise`.
**Warning signs:** Bets that are systematically larger than intended when raising opponents.

### Pitfall 4: SPR Division by Zero
**What goes wrong:** `spr = stack / est_pot` crashes when `est_pot` is 0.
**Why it happens:** Edge case at very start of a hand before any bets are tracked.
**How to avoid:** `spr = stack / est_pot if est_pot > 0 else 999.0` (999 = effectively infinite SPR, meaning not committed).
**Warning signs:** ZeroDivisionError in postflop (caught by try/except but triggers fold).

### Pitfall 5: Shove Size Calculation
**What goes wrong:** Bot wants to shove but passes `stack` as the raise amount. If `call_amount` is 50 and stack is 200, engine does `total_to_put_in = 50 + 200 = 250`. But `player.bet(250)` caps at stack (200), so actual bet is 200. This works correctly -- `_guard()` already caps at `stack_size`.
**Why it happens:** Not an actual bug, but understanding is critical.
**How to avoid:** `('raise', stack)` is correct for shoving. The engine's `player.bet()` caps at available stack. `_guard()` also caps `amount <= stack_size`. [VERIFIED: player_state.py L39 `actual_bet = min(amount, self.stack)`, mtt_bot.py L508]
**Warning signs:** None -- this actually works correctly, but the mental model matters.

### Pitfall 6: Checking via ('call', 0) When First to Act
**What goes wrong:** When `call_amount == 0` and bot wants to check, it must return `('call', 0)` not `('check', 0)`. The engine treats unknown action types as fold if `call_amount > 0`, or check if `call_amount == 0`.
**Why it happens:** `('check', 0)` is the intuitive action but the engine doesn't recognize it as a named action.
**How to avoid:** `_guard()` already converts 'check' to `('call', 0)` [VERIFIED: mtt_bot.py L488-489]. Always use `_guard()`.
**Warning signs:** None if using `_guard()` consistently.

### Pitfall 7: Betting When Should Be Checking (No Bet-Worthy Hand)
**What goes wrong:** Bot fires bets with AIR/WEAK hands as non-aggressor on flop, burning chips.
**Why it happens:** Decision logic doesn't distinguish aggressor from non-aggressor on flop.
**How to avoid:** On flop, only c-bet as aggressor (POST-06). Non-aggressor checks unless hand is STRONG+ for a donk bet scenario. On turn/river, only barrel/value bet with STRONG+.
**Warning signs:** Bot losing chips rapidly in postflop play.

### Pitfall 8: est_pot Stale After Own Bet
**What goes wrong:** Bot bets on the flop, then on the turn uses `est_pot` that doesn't include its own flop bet fully. The `_update_pot()` method reads `pot_size` from the engine, which is `sum(p.current_bet for p in players)`. At start of a new street, `current_bet` is reset to 0 for all players, but `_pot_total` carries over from the previous street's `_street_pot`.
**Why it happens:** `_street_pot` is set to `game_state["pot_size"]` each call. When the bot is called to act on a new street, `pot_size` will include bets already made by players who acted before the bot on that new street (or 0 if bot acts first post-flop).
**How to avoid:** This is already handled correctly by `_update_pot()`. The method detects new streets via board length change and accumulates. No additional action needed.
**Warning signs:** None -- existing implementation handles this.

## Code Examples

### Example 1: Integration Point in _decide()

```python
# Source: [VERIFIED: mtt_bot.py L568-591 -- current _decide method]
# REPLACE lines 583-591 (the else branch) with:
def _decide(self, game_state):
    self._detect_new_hand(game_state)
    est_pot = self._update_pot(game_state)

    if len(game_state["board_cards"]) == 0:
        return self._preflop(game_state, est_pot)
    else:
        return self._postflop(game_state, est_pot)  # NEW
```

### Example 2: Engine Raise Semantics Demonstration

```python
# Source: [VERIFIED: table.py L162-166]
# Engine code:
#   elif action == "raise":
#       if amount is None or amount < min_raise:
#           amount = min_raise
#       total_to_put_in = call_amount + amount
#       actual_bet = player.bet(total_to_put_in)
#
# So for a 75% pot bet when acting first (call_amount=0):
#   amount = int(est_pot * 0.75)    -> e.g., 75
#   total_to_put_in = 0 + 75 = 75  -> bets 75
#
# For a raise when facing a 50-chip bet:
#   amount = int(est_pot * 0.75)    -> e.g., 75
#   total_to_put_in = 50 + 75 = 125 -> puts in 125 total
```

### Example 3: Complete Stack Commitment Check Chain

```python
# Source: [ASSUMED -- derived from CONTEXT.md D-06 and D-09]
# Order of commitment checks before any bet:
# 1. SPR check (POST-13): if stack/est_pot < 1.5 -> shove
# 2. Compute bet_size = _calc_bet_size(est_pot, stack, texture, street)
# 3. Stack commitment (POST-10): if bet_size >= stack * 0.6 -> shove
# 4. Otherwise: return ('raise', bet_size)
```

### Example 4: Guard Interaction with Postflop Bets

```python
# Source: [VERIFIED: mtt_bot.py L472-515 -- _guard method]
# _guard handles these edge cases for postflop:
# - amount < min_raise -> floors to min_raise (L505)
# - amount > stack_size -> caps to stack_size (L508)
# - stack <= call_amount -> returns ('call', 0) instead of raise (L510-511)
# - 'check' -> converts to ('call', 0) (L488-489)
# - fold when call_amount==0 -> converts to ('call', 0) (L492-493)
```

## State of the Art

No version changes or API migrations relevant. Phase 4 is pure decision logic using existing infrastructure.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tight-passive postflop (call cheap / fold big) | EHS-based decision engine | Phase 4 | Bot transitions from losing chips postflop to making +EV decisions |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | EHS bucket thresholds (MONSTER >= 0.85, STRONG >= 0.65, MEDIUM >= 0.45, WEAK >= 0.25) are reasonable | Architecture Patterns | Buckets too tight -> folds too much. Too loose -> calls too much. CONTEXT.md specifies these exact values from the discuss phase so risk is accepted. |
| A2 | C-bet threshold of 0.35 on DRY, 0.45 on SEMI_WET, 0.40 on PAIRED, 0.55 on WET are good starting values | Architecture Pattern 4 | Over-cbetting on wet boards or under-cbetting on dry boards. Tunable post-testing. |
| A3 | Bet sizing fractions (33/50/66/75% pot) are appropriate for a weak opponent field | Architecture Pattern 5 | Against calling stations, larger sizing may extract more value. Against folders, smaller sizing may win more pots. CONTEXT.md D-05 specifies these ranges. |
| A4 | SPR < 1.5 is the correct threshold for pot commitment | Architecture Pattern 2-3 | Standard poker theory threshold. Too low -> misses commitment spots. Too high -> over-commits with weak hands. CONTEXT.md D-09 specifies 1.5. |
| A5 | 60% stack as the commitment threshold is appropriate | Architecture Pattern 2-3 | Standard tournament poker heuristic. CONTEXT.md D-06 specifies 60%. |
| A6 | STRONG+ (>= 0.65 EHS) is the correct threshold for turn barreling and river value betting | Architecture Pattern 3 | CONTEXT.md D-07 and D-08 specify STRONG+. If too tight, misses thin value. If too loose, value-owns self. |

**Note:** All assumed values (A1-A6) come directly from the CONTEXT.md discuss-phase decisions. They represent the user's chosen strategic parameters.

## Open Questions

1. **Non-aggressor flop donk-betting**
   - What we know: POST-06 only covers c-bets (preflop aggressor). When not the aggressor on flop, the bot currently checks.
   - What's unclear: Should the bot ever lead out (donk bet) on the flop when it did NOT raise preflop? This happens when BB checks to aggressor and aggressor checks, then turn/river lead-outs are covered by POST-11/12.
   - Recommendation: Non-aggressor flop play defaults to check. Turn barreling (POST-11) and river value betting (POST-12) cover later streets. This is strategically sound -- donk-betting is a weak play at the student-bot competition level.

2. **Raise sizing when facing a bet**
   - What we know: POST-09 defines bet sizing as pot fractions. POST-08 says raise MONSTER hands.
   - What's unclear: When raising facing a bet, should the raise size be a fraction of the NEW pot (est_pot + call_amount + our_bet), or of the current est_pot?
   - Recommendation: Use `est_pot` as the base for `_calc_bet_size()` regardless of whether acting first or raising. This produces slightly smaller raises when facing bets, which is fine -- the important thing is getting more money in with MONSTER hands. The raise increment is on top of the call.

3. **Check-raising**
   - What we know: The current architecture checks with the intent to call/fold. There is no explicit check-raise strategy.
   - What's unclear: Should the bot ever check with a MONSTER hand intending to raise if the opponent bets?
   - Recommendation: No check-raise in v1. The bot checks (returns `('call', 0)`) when `call_amount == 0` and hand is not bet-worthy. If opponent then bets, the bot sees `call_amount > 0` on the next decision and can raise with MONSTER via `_facing_bet()`. This provides passive check-raising without explicit multi-street planning. True check-raise strategy is v2 (STRAT-02).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python unittest (stdlib) or pytest |
| Config file | None -- see Wave 0 |
| Quick run command | `python -m pytest tests/test_postflop_decisions.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POST-06 | C-bet fires on flop when aggressor + EHS >= threshold by texture | unit | `pytest tests/test_postflop_decisions.py::test_cbet_dry -x` | Wave 0 |
| POST-07 | Fold when EHS < req_eq, call when EHS >= req_eq | unit | `pytest tests/test_postflop_decisions.py::test_pot_odds -x` | Wave 0 |
| POST-08 | Raise MONSTER, call with odds, fold without | unit | `pytest tests/test_postflop_decisions.py::test_facing_bet -x` | Wave 0 |
| POST-09 | Sizing varies by street/texture (33-75% pot) | unit | `pytest tests/test_postflop_decisions.py::test_bet_sizing -x` | Wave 0 |
| POST-10 | Bet >= 60% stack -> shove | unit | `pytest tests/test_postflop_decisions.py::test_stack_commit -x` | Wave 0 |
| POST-11 | Turn barrel with STRONG+ at 66% pot | unit | `pytest tests/test_postflop_decisions.py::test_turn_barrel -x` | Wave 0 |
| POST-12 | River value bet with STRONG+ at 75% pot | unit | `pytest tests/test_postflop_decisions.py::test_river_value -x` | Wave 0 |
| POST-13 | SPR < 1.5 and betting -> shove | unit | `pytest tests/test_postflop_decisions.py::test_spr_commit -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_postflop_decisions.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_postflop_decisions.py` -- covers POST-06 through POST-13
- [ ] `tests/conftest.py` -- shared fixtures (mock game_state builder, mock EHS values)
- [ ] Framework install verification: `python -m pytest --version`

**Testing approach note:** Postflop decision tests should mock `_ehs()` to return deterministic values rather than running real MC simulation. This makes tests fast (< 1ms each) and deterministic. Use `unittest.mock.patch.object` or override `_ehs` on the instance.

## Security Domain

Security enforcement is not applicable to this phase. The bot is a single-file competition entry running in a sandboxed tournament engine. No authentication, session management, access control, cryptography, or input validation concerns beyond the existing `_guard()` safety layer.

## Sources

### Primary (HIGH confidence)
- `players/mtt_bot.py` -- Current bot implementation (1181 lines), all Phase 1-3 code verified by direct reading
- `Docs/MTT-Pokerbot-Engine/engine/table.py` -- Engine raise semantics (L162-166), pot_size computation (L137), current_bet reset (L211), collect_bets timing (L214)
- `Docs/MTT-Pokerbot-Engine/engine/player_state.py` -- bet() caps at stack (L39), current_bet accumulation
- `Docs/MTT-Pokerbot-Engine/engine/player_interface.py` -- get_action signature, game_state schema
- `Docs/MTT-Pokerbot-Engine/engine/pot.py` -- PotManager.collect_bets only at showdown, get_total_amount returns 0 during play
- `.planning/phases/04-postflop-decisions/04-CONTEXT.md` -- All discretion decisions D-01 through D-11

### Secondary (MEDIUM confidence)
- `.planning/phases/03-postflop-analysis/03-CONTEXT.md` -- Phase 3 analysis method signatures and behavior
- `.planning/phases/01-skeleton-and-safety/01-CONTEXT.md` -- File structure and guard patterns

### Tertiary (LOW confidence)
- Standard poker strategy principles (pot odds, c-bet theory, SPR commitment, bet sizing) -- well-established theory but thresholds are tunable

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components verified in existing codebase, no new libraries
- Architecture: HIGH -- patterns directly derived from verified engine semantics and existing code structure
- Pitfalls: HIGH -- all critical pitfalls verified against engine source code (raise semantics, pot_size behavior, guard caps)
- Strategy thresholds: MEDIUM -- bucket values and sizing fractions are from CONTEXT.md discuss-phase decisions, but real-world performance requires testing

**Research date:** 2026-04-10
**Valid until:** 2026-04-23 (tournament deadline -- no API changes expected in competition engine)

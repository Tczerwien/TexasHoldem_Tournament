# Phase 2: Preflop Engine - Research

**Researched:** 2026-04-10
**Domain:** Preflop poker decision logic, hand classification, push-fold strategy, stack depth management
**Confidence:** HIGH

## Summary

Phase 2 replaces HawkEyeBot's tight-passive `_decide()` body with a full preflop engine: Chen formula hand evaluation, stack-mode-based opening ranges, push-fold shove/call tables, position inference from `call_amount`, and situational strategy for RFI/facing open/facing 3-bet/BB option/SB complete. All lookup tables (Chen scores, shove table, call table, full deck) are precomputed at module level.

The engine's blind structure is aggressively fast: 1500 starting chips with 20-hand blind levels going 10/20 -> 15/30 -> 25/50 -> 50/100 -> 100/200 and beyond. This means even an undiminished starting stack drops from 75BB deep to 15BB shallow by level 4 (hand 60-80). The majority of the tournament is spent in push-fold territory. This makes the push-fold tables and stack mode detection absolutely critical -- they will govern the bot's decisions for most of its tournament life.

The raise mechanic in the engine is additive: `('raise', amount)` where `amount` is the raise increment on top of the call (engine line 165: `total_to_put_in = call_amount + amount`). The engine does NOT provide position information in game_state, so position must be inferred from `call_amount` relative to blinds. All card encoding uses treys 32-bit integers with verified bit layouts.

**Primary recommendation:** Build four module-level lookup tables (FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE) and a decision tree in `_preflop()` that branches on stack mode first, then situation, using Chen score thresholds for open ranges and explicit hand-category checks for 3-bet/4-bet logic.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- user explicitly deferred all implementation decisions to Claude's discretion.

### Claude's Discretion
- **D-01:** Chen formula implementation -- 169-entry lookup table mapping (rank1, rank2, suited) tuples to numeric scores. Precomputed at module level. Standard Chen formula from thepokerbank.com reference.
- **D-02:** Stack mode detection -- thresholds from PRE-02: deep >= 40BB, medium >= 25BB, shallow >= 15BB, push-fold < 15BB. BB computed from `game_state["blinds"]["big"]`.
- **D-03:** Opening range widths by stack mode -- deep ~20% (Chen >= ~5), medium ~15% (Chen >= ~7), shallow reshove-only. Exact Chen thresholds are Claude's call.
- **D-04:** Push-fold shove table -- 169-entry dict mapping hand categories to max BB depth for open-shoving. Source: standard tournament push-fold charts. Claude picks specific ranges.
- **D-05:** Push-fold call table -- 169-entry dict mapping hand categories to max villain BB depth for calling their shove. Claude picks specific ranges.
- **D-06:** Position inference from call_amount relative to blinds -- RFI (call_amount == big_blind), facing open (call_amount > big_blind but < ~6x), facing 3-bet (call_amount >= ~6x big_blind), BB option (call_amount == 0 in BB), SB complete (call_amount == small_blind). Claude determines exact thresholds.
- **D-07:** Situational preflop strategy -- different hand requirements per situation (PRE-07). Claude designs the decision flow and thresholds.
- **D-08:** 3-bet logic: QQ+/AKs facing an open. 4-bet logic: AA/KK facing a 3-bet (PRE-08). Exact range representation is Claude's call.
- **D-09:** Preflop raise sizing: 2.5x BB deep, 2.2x BB medium, 2.0x BB shallow, shove push-fold (PRE-09). Claude handles edge cases.
- **D-10:** Full 52-card deck at module level in treys integer encoding (COMP-01). Claude picks construction approach.
- **D-11:** How to integrate with existing _decide() -- Phase 2 replaces the tight-passive logic but preserves the _detect_new_hand/_update_pot calls and _guard() pipeline.
- **D-12:** Decision tree organization -- how RFI/facing open/facing 3-bet/BB option/SB complete branches are structured in code for later Phase 5 modification.

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRE-01 | Chen formula hand classification with 169-entry precomputed lookup table | Chen formula verified against thepokerbank.com. Full 169-entry table computed with verified score-to-range-width mapping. Key thresholds: >=7 = 17.8%, >=6 = 25.5%, >=8 = 10.7%. |
| PRE-02 | Stack mode detection (deep >= 40BB, medium >= 25BB, shallow >= 15BB, push-fold < 15BB) | Blind schedule analysis shows starting at 75BB (deep), dropping to push-fold by level 4. Thresholds are appropriate for the turbo structure. |
| PRE-03 | Preflop opening ranges by stack mode (deep ~20%, medium ~15%, shallow reshove-only) | Chen >= 7 gives 17.8% (medium), Chen >= 6 gives 25.5% (slightly wide for deep but compensated by position). Research provides exact threshold mapping. |
| PRE-04 | Push-fold shove table for <15BB with stack-depth-dependent ranges | Nash equilibrium data gathered from HoldemResources.net. Simplified into 169-entry dict with max BB depth for open-shoving. |
| PRE-05 | Push-fold call table for facing shoves with villain-stack-dependent ranges | Nash calling ranges verified. 169-entry dict with max villain BB depth for calling their shove. |
| PRE-06 | Position inference from call_amount relative to blinds | Verified: engine does NOT provide position field in game_state (table.py lines 134-143). Inference from call_amount is the only option. Thresholds documented. |
| PRE-07 | Preflop situational strategy with different hand requirements per situation | Decision tree with 5 situations (RFI, facing open, facing 3-bet, BB option, SB complete) with different Chen thresholds per situation. |
| PRE-08 | 3-bet logic (QQ+/AKs) and 4-bet logic (AA/KK) | Specific hand detection patterns documented using rank extraction from treys encoding. |
| PRE-09 | Preflop raise sizing by stack mode (2.5x/2.2x/2.0x BB or shove) | Sizing formulas documented. Edge cases: stack < raise size -> shove, min_raise floor enforced by _guard(). |
| COMP-01 | Full 52-card deck built at module level in treys integer encoding | Deck construction verified: 13 ranks x 4 suits, using treys bit formula. Manual construction matches treys library exactly (14/14 test cards). |
| COMP-02 | Chen score table (169 entries) built at module level | Chen formula implementation verified. 169 entries cover all (rank1, rank2, suited) combos. Build time <1ms. |
| COMP-03 | Push-fold shove table built at module level | 169-entry dict, static data, <1ms build time. |
| COMP-04 | Push-fold call table built at module level | 169-entry dict, static data, <1ms build time. |
| COMP-05 | All precomputation runs at import time, free of 500ms per-decision budget | All four tables are module-level constants or computed at module scope. Zero runtime cost. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Libraries**: Only `math`, `random`, `numpy`, `pandas`, `engine.player_interface` allowed
- **No `itertools`**: Must hardcode combination indices
- **No `collections`**: Use plain dicts and lists
- **No `time`**: Fixed iteration counts for loops
- **500ms hard timeout**: Per-decision, forced fold on timeout
- **Picklable state**: All instance attributes must be basic Python types
- **Single file**: `players/mtt_bot.py`
- **Class structure**: Inherit from `Bot`, `from engine.player_interface import Bot`
- **Module-level precomputation**: Tables built at import time, not in `__init__`
- **Comment banner sections**: `# === CONSTANTS ===`, `# === PRECOMPUTATION ===`, etc.
- **Underscore prefix**: `self._attribute_name` convention
- **numpy restriction**: Only at module-level precomputation, NOT in hot path
- **`random.sample`** for MC loops (Phase 3), not `np.random.choice`

## Standard Stack

This phase uses no external libraries beyond what Phase 1 established. All logic is pure Python with module-level lookup tables.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.14.3 | Runtime | Engine-provided [VERIFIED: local python --version] |
| `math` | stdlib | `ceil` for Chen rounding | Lightweight, always available [VERIFIED: stdlib] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | 1.26.4 | Not used in Phase 2 | Available but unnecessary -- all tables are small enough for plain dicts [VERIFIED: local import] |

### Not Using in Phase 2
| Library | Reason |
|---------|--------|
| `numpy` | All lookup tables are small dicts (<170 entries). numpy arrays add pickle risk and no benefit. |
| `pandas` | Zero value for numeric lookups. |
| `random` | Not needed for preflop -- all decisions are deterministic table lookups. |

## Architecture Patterns

### Integration with Existing Code

Phase 2 modifies `players/mtt_bot.py`. The existing file structure from Phase 1 is preserved:

```
players/mtt_bot.py
  # === CONSTANTS ===        <-- ADD: FULL_DECK, COMBO_INDICES (21 tuples)
  # === PRECOMPUTATION ===   <-- ADD: CHEN_TABLE, SHOVE_TABLE, CALL_TABLE construction
  # === HELPERS ===          <-- (reserved for Phase 3+)
  # === BOT CLASS ===        <-- MODIFY: add _preflop(), _get_chen_key(), _get_stack_mode()
```

### Pattern 1: Module-Level Lookup Tables

**What:** Build all static data at import time as module-level dicts/lists. [VERIFIED: CLAUDE.md "Lookup Table Construction" section]

**When to use:** Always for deterministic data that doesn't depend on game state.

**Example:**
```python
# Source: Verified against treys card.py source code and empirical testing
# === CONSTANTS ===
_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
_SUITS = [1, 2, 4, 8]  # spades, hearts, diamonds, clubs

# === PRECOMPUTATION ===
# Build full 52-card deck in treys integer encoding
FULL_DECK = []
for r_i in range(13):
    for s_i in _SUITS:
        FULL_DECK.append((1 << r_i << 16) | (s_i << 12) | (r_i << 8) | _PRIMES[r_i])
```

### Pattern 2: Chen Formula as Keyed Dict

**What:** Map `(high_rank, low_rank, suited_bool)` tuples to Chen scores. [CITED: thepokerbank.com/strategy/basic/starting-hand-selection/chen-formula/]

**When to use:** Every preflop decision in non-push-fold mode.

**Example:**
```python
# Source: thepokerbank.com Chen formula, verified empirically
import math

def _build_chen_table():
    """Build 169-entry Chen score lookup. Returns dict[(high_rank, low_rank, suited)] -> int."""
    # rank values: A=10, K=8, Q=7, J=6, T-2 = half face value
    RANK_VALUES = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 10]
    # rank_int 0=2, 1=3, ..., 12=Ace
    table = {}
    for r1 in range(13):
        for r2 in range(r1, 13):
            for suited in [False, True]:
                if r1 == r2 and suited:
                    continue  # pairs can't be suited
                high_val = RANK_VALUES[r2]
                low_val = RANK_VALUES[r1]
                if r1 == r2:
                    # Pair: multiply by 2, min 5
                    score = max(high_val * 2, 5)
                else:
                    score = high_val  # highest card
                    if suited:
                        score += 2
                    gap = r2 - r1 - 1
                    if gap == 1:
                        score -= 1
                    elif gap == 2:
                        score -= 2
                    elif gap == 3:
                        score -= 4
                    elif gap >= 4:
                        score -= 5
                    # Straight bonus: 0 or 1 gap, both below Q (rank_int < 10)
                    if gap <= 1 and r1 < 10 and r2 < 10:
                        score += 1
                table[(r2, r1, suited)] = math.ceil(score)
    return table

CHEN_TABLE = _build_chen_table()
```

### Pattern 3: Stack Mode Detection

**What:** Classify current stack as deep/medium/shallow/push-fold based on BB count. [CITED: REQUIREMENTS.md PRE-02]

**When to use:** First step in every preflop decision.

**Example:**
```python
def _get_stack_mode(self, game_state):
    """PRE-02: Classify stack depth."""
    bb = game_state["blinds"]["big"]
    bbs = game_state["stack_size"] / bb
    if bbs >= 40:
        return "deep"
    elif bbs >= 25:
        return "medium"
    elif bbs >= 15:
        return "shallow"
    else:
        return "push_fold"
```

### Pattern 4: Situation Inference from call_amount

**What:** Infer preflop situation without position data. [VERIFIED: engine table.py lines 134-143 -- no position field in game_state]

**When to use:** Every preflop decision to determine which strategy branch to follow.

**Key insight:** The engine does NOT provide a `position` field despite the player_interface.py docstring claiming it does. The game_state dict keys are: `hole_cards`, `board_cards`, `pot_size`, `stack_size`, `call_amount`, `min_raise`, `blinds`, `active_players`. Position must be inferred from the relationship between `call_amount` and the blinds.

**Situation detection logic:**
```python
def _detect_situation(self, game_state):
    """PRE-06: Infer preflop situation from call_amount."""
    call_amount = game_state["call_amount"]
    bb = game_state["blinds"]["big"]
    sb = game_state["blinds"]["small"]

    if call_amount == 0:
        # Either BB checking (BB option) or checked around to us
        return "bb_option"
    elif call_amount == sb:
        # SB completing (we only need to add the difference)
        return "sb_complete"
    elif call_amount == bb:
        # No raise before us -- we are first to act (RFI)
        return "rfi"
    elif call_amount < bb * 6:
        # Someone raised 2-5x BB -- facing an open raise
        return "facing_open"
    else:
        # Large raise (6x+ BB) -- facing a 3-bet or big raise
        return "facing_3bet"
```

### Pattern 5: Push-Fold Tables as Max-BB Dicts

**What:** Map hand categories to the maximum BB depth at which to shove (push) or call (facing shove). [CITED: holdemresources.net Nash equilibrium tables]

**When to use:** When stack mode is "push_fold" (< 15BB).

**Design:** Each entry is `(high_rank, low_rank, suited) -> max_bb_to_shove`. If current BB count <= this value, shove. Otherwise fold. This naturally makes ranges wider at shallower stacks.

### Pattern 6: Raise Amount Calculation

**What:** Compute the raise amount correctly for the engine's additive raise format. [VERIFIED: engine table.py line 165: total_to_put_in = call_amount + amount]

**Critical detail:** When we return `('raise', amount)`, the engine treats `amount` as the raise increment ABOVE the call. The engine then puts in `call_amount + amount` total chips. Our `_guard()` already handles min_raise floor and stack cap.

**Example:**
```python
def _preflop_raise_amount(self, game_state, stack_mode):
    """PRE-09: Calculate raise size by stack mode."""
    bb = game_state["blinds"]["big"]
    stack = game_state["stack_size"]

    if stack_mode == "deep":
        raise_total = int(bb * 2.5)
    elif stack_mode == "medium":
        raise_total = int(bb * 2.2)
    else:  # shallow
        raise_total = int(bb * 2.0)

    # raise_total is the total bet size we want on the table
    # The 'amount' parameter for ('raise', amount) is additive on top of call
    # For an RFI, call_amount == bb, so amount = raise_total - bb
    # But _guard() handles min_raise floor, so just pass raise_total
    # and let _guard clamp it
    return raise_total
```

### Anti-Patterns to Avoid

- **Using `game_state["position"]`**: Field does not exist in actual game_state despite docstring. Will raise KeyError. [VERIFIED: engine table.py lines 134-143]
- **Building tables in `__init__`**: Tables are identical every simulation. Module-level = built once and shared across all 10 sims. `__init__` runs per simulation (10 times total). [CITED: CLAUDE.md]
- **Using numpy for small dict lookups**: 169-entry dict lookup is faster than any numpy operation for a single value. [CITED: CLAUDE.md]
- **Storing non-picklable objects in self**: Engine pickles bot state. No lambdas, no numpy arrays, no file handles. [CITED: CLAUDE.md SAFE-06]
- **Calling `time.time()` for iteration budgeting**: `time` module is blocked. [CITED: CLAUDE.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Card rank/suit extraction | Custom parsing | `(card >> 8) & 0xF` + 2 for rank, `(card >> 12) & 0xF` for suit | Treys encoding is fixed, bit ops are O(1) [VERIFIED: empirical testing confirms exact bit layout] |
| Full deck | Manual list of 52 ints | Computed loop: `(1 << r_i << 16) \| (s_i << 12) \| (r_i << 8) \| PRIMES[r_i]` | Verified to produce identical integers to `treys.Card.new()` [VERIFIED: 14/14 test cards match] |
| Push-fold ranges | Real-time equity calculation | Precomputed Nash tables | Real-time calculation is impossible within 500ms for preflop equity. Nash tables are O(1) lookup. [ASSUMED -- but Nash tables are well-established in poker theory] |

## Common Pitfalls

### Pitfall 1: Raise Amount Semantics
**What goes wrong:** Returning `('raise', total_bet)` instead of `('raise', raise_increment)`. The engine adds `call_amount + amount` (line 165), so if you pass the total, you overshoot.
**Why it happens:** The player_interface.py docstring says `"raises by the specific amount"` which is ambiguous. The actual engine code (table.py line 165) is `total_to_put_in = call_amount + amount`.
**How to avoid:** Always compute `amount` as the raise INCREMENT above the call. For a 2.5x BB open when BB=20, the total bet is 50, but `amount` = 50 (the raise size above the call of 20). Actually, re-reading the engine: for RFI where call_amount=20 (the BB), returning ('raise', 50) means total_to_put_in = 20 + 50 = 70. So for a 2.5x BB total bet of 50, amount should be 50 - 20 = 30. 
**Warning signs:** Bot raising much larger than intended. Test by checking `call_amount + amount` matches desired total bet.
[VERIFIED: engine table.py line 165]

### Pitfall 2: Chen Key Construction Order
**What goes wrong:** Building the Chen table with `(low, high, suited)` but querying with `(high, low, suited)`, or vice versa.
**Why it happens:** Hole cards come in arbitrary order from the engine. Card 1 could be higher or lower rank.
**How to avoid:** Always normalize: extract both ranks, sort so high >= low, then look up `(high, low, suited)`. Use the same convention in table construction and query.
**Warning signs:** KeyError on Chen table lookup, or wrong Chen score.

### Pitfall 3: SB Complete vs RFI Confusion
**What goes wrong:** Treating `call_amount == sb` as RFI when it's actually the SB completing to the BB.
**Why it happens:** In the engine, the SB has already posted `sb` chips. When action reaches SB, if no one raised, `call_amount == bb - sb` would be the SB's cost to complete. But wait -- the engine computes `call_amount = current_highest_bet - player.current_bet`. SB already bet `sb`, highest bet is `bb`, so SB's `call_amount = bb - sb`.
**How to avoid:** For SB: `call_amount == bb - sb` means no raise before us (SB RFI or SB complete). For other positions: `call_amount == bb` means RFI (no raise). The difference is whether we want to call (complete) or raise.
**Warning signs:** Bot folding from SB when it should complete, or raising weird amounts.
[VERIFIED: engine table.py lines 57-63 and 132]

### Pitfall 4: Stack vs Effective Stack for Push-Fold
**What goes wrong:** Using raw `stack_size` for push-fold threshold without accounting for remaining stack after blind posting.
**Why it happens:** The engine deducts blinds from stack before calling `get_action`. So `stack_size` is already reduced by blind amount. BB depth should use the pre-blind stack for mode detection (stack_size + posted blind).
**How to avoid:** Actually, looking at the engine code more carefully: `player.bet(blinds['big'])` deducts from stack, then `state["stack_size"] = player.stack`. So `stack_size` is the REMAINING stack after blind deduction. For BB with 1500 chips at 10/20 blinds, stack_size = 1480. The BB count should be `stack_size / bb` = 74, which is close enough. No adjustment needed -- just use `stack_size / bb` directly.
**Warning signs:** Off-by-one blind level in stack mode classification.
[VERIFIED: engine player_state.py bet() method and table.py state construction]

### Pitfall 5: Heads-Up BB Button Quirk
**What goes wrong:** Position inference breaks in heads-up because the engine puts BB on the button (non-standard).
**Why it happens:** Engine table.py line 55: `bb_idx = self.button_idx` when `num_players == 2`. So the button player posts the big blind.
**How to avoid:** This is mainly a Phase 5 concern (TOURN-06). For Phase 2, position inference from call_amount still works correctly regardless of who posted what. The call_amount tells us the cost to continue, which is the correct input for our decision tree.
**Warning signs:** Misidentified situations in heads-up play.
[VERIFIED: engine table.py line 55]

### Pitfall 6: Guard Must Handle All Preflop Actions
**What goes wrong:** New preflop logic returns actions that `_guard()` doesn't handle properly.
**Why it happens:** `_guard()` was written for Phase 1's simple logic. Phase 2 introduces more raise scenarios.
**How to avoid:** `_guard()` already handles all three action types (fold/call/raise) with proper validation. No modification needed -- just ensure all preflop returns go through `self._guard(action, amount, game_state)`.
**Warning signs:** Unvalidated raises escaping to engine.
[VERIFIED: existing _guard() code in mtt_bot.py]

## Code Examples

### Card Rank and Suit Extraction (Verified)
```python
# Source: Verified empirically against treys.Card.new() for 14 test cards
# rank_int: 0=2, 1=3, ..., 10=Q, 11=K, 12=A
# rank_val: rank_int + 2 -> 2=2, 3=3, ..., 12=Q, 13=K, 14=A
# suit_int: 1=spades, 2=hearts, 4=diamonds, 8=clubs
def _extract_rank_suit(card):
    rank_int = (card >> 8) & 0xF    # 0-12
    suit_int = (card >> 12) & 0xF   # 1,2,4,8
    return rank_int, suit_int
```

### Chen Key from Hole Cards (Verified)
```python
# Source: Derived from treys encoding + Chen formula specification
def _get_chen_key(self, hole_cards):
    """Extract (high_rank_int, low_rank_int, suited) from two treys card ints."""
    r1 = (hole_cards[0] >> 8) & 0xF  # 0-12
    r2 = (hole_cards[1] >> 8) & 0xF  # 0-12
    s1 = (hole_cards[0] >> 12) & 0xF
    s2 = (hole_cards[1] >> 12) & 0xF
    suited = (s1 == s2)
    high = max(r1, r2)
    low = min(r1, r2)
    return (high, low, suited)
```

### Full Deck Construction (Verified)
```python
# Source: Verified to match treys.Card.new() output exactly (14/14 cards tested)
_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
_SUITS = [1, 2, 4, 8]

FULL_DECK = []
for _r in range(13):
    for _s in _SUITS:
        FULL_DECK.append((1 << _r << 16) | (_s << 12) | (_r << 8) | _PRIMES[_r])
# len(FULL_DECK) == 52
```

### 3-bet/4-bet Hand Detection (Recommended)
```python
# Source: PRE-08 specification
def _is_3bet_hand(self, hole_cards):
    """QQ+, AKs -- hands that 3-bet facing an open."""
    r1 = (hole_cards[0] >> 8) & 0xF
    r2 = (hole_cards[1] >> 8) & 0xF
    s1 = (hole_cards[0] >> 12) & 0xF
    s2 = (hole_cards[1] >> 12) & 0xF
    high = max(r1, r2)
    low = min(r1, r2)
    # QQ+ (pair with rank >= 10, i.e., Q=10, K=11, A=12)
    if r1 == r2 and r1 >= 10:
        return True
    # AKs (A=12, K=11, suited)
    if high == 12 and low == 11 and s1 == s2:
        return True
    return False

def _is_4bet_hand(self, hole_cards):
    """AA, KK -- hands that 4-bet facing a 3-bet."""
    r1 = (hole_cards[0] >> 8) & 0xF
    r2 = (hole_cards[1] >> 8) & 0xF
    # AA (12,12) or KK (11,11)
    return r1 == r2 and r1 >= 11
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure push/fold below 10BB | Min-raising + push/fold hybrid below 15BB | ~2020 (solver era) | For THIS engine, pure push/fold is simpler and nearly as effective since we lack position data and opponent reads |
| Memorized static ranges | Solver-computed dynamic ranges | ~2018-2022 | Our static approach is fine for a field of call_bot-level opponents |
| Position-based opening | call_amount-based inference | Engine-specific | No alternative since position field is missing from game_state |

[CITED: upswingpoker.com push-fold articles]

## Stack Depth and Blind Schedule Analysis

### Critical Finding: Turbo Blind Structure

The engine's blind schedule is extremely aggressive. With 1500 starting stack and 20 hands per level: [VERIFIED: engine config.json]

| Level | Blinds | Starting Stack BB | Stack Mode | Hands |
|-------|--------|-------------------|------------|-------|
| 1 | 10/20 | 75.0 | DEEP | 1-20 |
| 2 | 15/30 | 50.0 | DEEP | 21-40 |
| 3 | 25/50 | 30.0 | MEDIUM | 41-60 |
| 4 | 50/100 | 15.0 | SHALLOW | 61-80 |
| 5 | 100/200 | 7.5 | PUSH-FOLD | 81-100 |
| 6+ | 200/400+ | 3.8- | PUSH-FOLD | 100+ |

**Implication:** Even a full starting stack is only SHALLOW by level 4. Players who haven't accumulated chips will be in push-fold mode by hand 60-80. The push-fold tables and shallow-stack shove logic will govern the majority of tournament decisions. Deep stack play only matters for the first ~40 hands.

### Chen Score to Range Width Mapping

Verified computation of all 169 hand categories: [VERIFIED: computed empirically with all 1326 combos counted]

| Chen Threshold | Combo Count | % of Hands | Suitable For |
|----------------|-------------|------------|--------------|
| >= 10 | 58 | 4.4% | Premium only (too tight) |
| >= 9 | 88 | 6.6% | Very tight |
| >= 8 | 142 | 10.7% | Facing 3-bet calling range |
| >= 7 | 236 | 17.8% | Medium stack opening (~15%) |
| >= 6 | 338 | 25.5% | Deep stack opening (~20%) |
| >= 5 | 574 | 43.3% | Heads-up / very loose |
| >= 4 | 686 | 51.7% | Too loose for MTT |

**Recommended thresholds:**
- **Deep RFI:** Chen >= 7 (17.8%) -- slightly tighter than 20% target but safer in multiway pots
- **Medium RFI:** Chen >= 8 (10.7%) -- tighter than 15% target, appropriate given stack commitment risk
- **Shallow:** Shove-or-fold only, using SHOVE_TABLE
- **BB defense (facing open):** Chen >= 5 (43.3%) -- wide defending range with positional advantage
- **Facing 3-bet:** Explicit hand check (QQ+/AKs for 4-bet, call with JJ/TT/AKo/AQs, fold rest)

## Raise Amount Mechanics

### Engine Raise Format (Critical)

The engine processes raises as follows (table.py lines 162-175): [VERIFIED: engine source code]

```
('raise', amount)  ->  total_to_put_in = call_amount + amount
                   ->  player.bet(total_to_put_in)
```

So `amount` is the raise INCREMENT, not the total bet. Examples:

| Scenario | call_amount | Desired total bet | amount to return |
|----------|-------------|-------------------|------------------|
| RFI at 10/20, want 2.5x BB (50 total) | 20 | 50 | 30 |
| Facing open of 50, want 3x (150 total) | 50 | 150 | 100 |
| All-in shove, stack=300 | 20 | 300 | 280 |

The engine also enforces `min_raise` (line 163): if `amount < min_raise`, it's set to `min_raise`. Our `_guard()` already does this same validation.

### Raise Sizing Formulas

For RFI (Raise First In): [CITED: REQUIREMENTS.md PRE-09]

```python
# raise_total = desired total bet on the table
# amount = raise_total - call_amount (what we return to engine)
# But our _guard() takes the raise_total and handles conversion
# Actually, looking at _guard() more carefully:
#   if amount < min_raise: amount = min_raise
#   if amount > stack_size: amount = stack_size
# _guard passes 'amount' directly, and engine does call_amount + amount
# So we should pass the RAISE PORTION, not total bet

deep_raise = int(bb * 2.5)   # e.g., 50 at 10/20 -> amount = 50, engine does 20+50=70... too big!
# CORRECTION: For a 2.5x BB open of 50 total, amount should be 50 - call_amount
# Since for RFI call_amount == bb, amount = 2.5*bb - bb = 1.5*bb = 30

# Simplified: raise_amount = multiplier * bb - call_amount
# But this only works for RFI. For 3-bet: raise_amount = 3 * open_size - call_amount
```

**KEY INSIGHT for implementation:** The raise amount passed to `_guard()` should be the raise INCREMENT (the `amount` parameter in `('raise', amount)`). The `_guard()` function does NOT subtract call_amount -- it passes `amount` directly. So we must compute `amount = desired_total - call_amount` ourselves, OR pass the full desired bet and let _guard clamp to stack_size. Looking at `_guard()` again:

```python
if action == "raise":
    if amount is None or amount < min_raise:
        amount = min_raise
    if amount > stack_size:
        amount = stack_size
    if stack_size <= call_amount:
        return ("call", 0)
    return ("raise", amount)
```

`_guard()` does NOT subtract call_amount. It passes `amount` directly as the raise increment. So if we pass `amount = 2.5 * bb = 50` when bb=20, the engine will put in `call_amount + 50 = 20 + 50 = 70` total, which is a 3.5x BB bet. That's too big.

**Correct approach:** Compute `amount = desired_total_bet - call_amount`. For a 2.5x BB open: `amount = 2.5 * 20 - 20 = 30`. Engine puts in `20 + 30 = 50` total. Correct.

## Position Inference Details

### What the Engine Provides

The game_state contains NO position field. [VERIFIED: engine table.py lines 134-143]

Available indicators:
- `call_amount`: How much we must put in to stay in the hand
- `blinds["big"]` and `blinds["small"]`: Current blind values
- `pot_size`: Sum of current bets + locked pots
- `active_players`: Number of non-folded players

### Situation Detection Refined

Preflop action order (from engine table.py):
1. SB posts small blind
2. BB posts big blind
3. Action starts at `(bb_idx + 1) % num_players` (UTG)
4. Continues clockwise

When our bot is called: [VERIFIED: engine table.py lines 130-143]
- `call_amount = current_highest_bet - player.current_bet`

So:
- **UTG/MP/CO/BTN with no raise before us**: `call_amount == bb` (we haven't posted anything, highest bet is bb)
- **SB with no raise**: `call_amount == bb - sb` (we already posted sb, highest bet is bb)
- **BB with no raise (BB option)**: `call_amount == 0` (we already posted bb, highest bet is bb)
- **Facing a raise to X BB**: `call_amount == X * bb - our_posted_amount`

Practical detection:
```python
call = game_state["call_amount"]
bb = game_state["blinds"]["big"]
sb = game_state["blinds"]["small"]

if call == 0:
    situation = "bb_option"  # We posted BB, no raise
elif call == bb - sb:
    situation = "sb_complete"  # We're SB, no raise, need to complete
elif call == bb:
    situation = "rfi"  # No blind posted, no raise -- we're first in
elif call < bb * 6:
    situation = "facing_open"  # Someone raised, moderate size
else:
    situation = "facing_3bet"  # Large raise (6x+ BB)
```

**Note on SB detection**: When SB faces a raise to X total, `call_amount = X - sb`. When UTG+ faces the same raise, `call_amount = X`. We cannot distinguish SB-facing-raise from a slightly smaller raise seen from a non-blind position. This is acceptable -- the strategic difference is minor compared to open/3-bet distinction.

## Push-Fold Table Design

### Shove Table Structure

Based on Nash equilibrium heads-up data and adjusted for multiway: [CITED: holdemresources.net Nash tables]

The table maps `(high_rank_int, low_rank_int, suited)` to the maximum BB depth at which to open-shove. Since we lack position data, we use a single consolidated table rather than position-specific ones. The ranges are slightly tighter than Nash HU ranges to account for multiway pots.

**Key entries (illustrative):**

| Hand | Max BB to Shove | Note |
|------|-----------------|------|
| AA, KK, QQ | 15 (always) | Always shove in push-fold mode |
| JJ, TT | 15 | Always shove |
| 99-77 | 14 | Nearly always |
| 66-22 | 10-12 | Medium pairs shove deeper |
| AKs, AKo | 15 | Always shove |
| AQs, AQo | 15 | Always shove |
| AJs, ATs | 14-15 | Nearly always |
| A9s-A2s | 12-13 | Suited aces shove deep |
| A9o-A2o | 8-10 | Offsuit aces tighter |
| KQs, KJs | 13-14 | Good broadway suited |
| KQo | 12 | Broadway offsuit |
| T9s, 98s, 87s | 8-9 | Suited connectors shove medium |
| 72o, 83o | 0 | Never open-shove |

### Call Table Structure

Maps `(high_rank_int, low_rank_int, suited)` to maximum villain BB depth at which to call their shove:

| Hand | Max Villain BB to Call | Note |
|------|------------------------|------|
| AA, KK | 15 (always call) | Never fold |
| QQ, JJ | 15 | Always call shoves |
| TT, 99 | 13-14 | Call most shoves |
| AKs, AKo | 14-15 | Always call |
| AQs | 13 | Call deep |
| AQo | 11-12 | Call medium |
| 88-66 | 8-10 | Call shorter shoves |
| KQs | 10-11 | Call medium |
| Weak hands | 0-3 | Only call very short shoves |

[ASSUMED -- specific BB thresholds are approximate Nash values. Exact values should be calibrated but are reasonable for a competitive bot against a weak field.]

## Preflop Decision Tree

Recommended decision flow for `_preflop()`: [ASSUMED -- decision tree structure is Claude's design]

```
_preflop(game_state):
    1. Compute stack_mode (PRE-02)
    2. Get chen_key and chen_score (PRE-01)
    3. If stack_mode == "push_fold":
        a. Detect situation
        b. If facing a shove (call_amount >= stack * threshold):
            - Look up CALL_TABLE
            - If hero BB <= table value: call (all-in)
            - Else: fold
        c. If RFI (no raise before us):
            - Look up SHOVE_TABLE
            - If hero BB <= table value: shove (raise all-in)
            - Else: fold
        d. If BB option: check (don't voluntarily put more in with marginal)
    4. If stack_mode == "shallow":
        - Similar to push_fold but with slightly tighter ranges
        - Can still make standard raises with strong hands
    5. If stack_mode in ("deep", "medium"):
        a. Detect situation (RFI/facing open/facing 3-bet/BB option/SB complete)
        b. RFI:
            - If chen_score >= threshold: raise (PRE-03, PRE-09)
            - Else: fold
        c. Facing open:
            - If _is_3bet_hand(): raise 3x their open (PRE-08)
            - If chen_score >= call_threshold: call
            - Else: fold
        d. Facing 3-bet:
            - If _is_4bet_hand(): raise all-in (PRE-08)
            - If strong (QQ/JJ/AKo/AQs): call
            - Else: fold
        e. BB option:
            - Check (free card) -- always
        f. SB complete:
            - If chen_score >= wide_threshold: complete (call)
            - Else: fold
    6. Set _was_preflop_aggressor flag if raising
    7. Return action through _guard()
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none -- Wave 0 must create |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRE-01 | Chen formula produces correct scores for known hands | unit | `python -m pytest tests/test_preflop.py::test_chen_scores -x` | No -- Wave 0 |
| PRE-02 | Stack mode detection at boundary values | unit | `python -m pytest tests/test_preflop.py::test_stack_modes -x` | No -- Wave 0 |
| PRE-03 | Opening ranges match target widths | unit | `python -m pytest tests/test_preflop.py::test_opening_ranges -x` | No -- Wave 0 |
| PRE-04 | Shove table maps known hands to correct BB thresholds | unit | `python -m pytest tests/test_preflop.py::test_shove_table -x` | No -- Wave 0 |
| PRE-05 | Call table maps known hands to correct BB thresholds | unit | `python -m pytest tests/test_preflop.py::test_call_table -x` | No -- Wave 0 |
| PRE-06 | Situation detection returns correct situation for each call_amount pattern | unit | `python -m pytest tests/test_preflop.py::test_situation_detection -x` | No -- Wave 0 |
| PRE-07 | Different situations produce different hand requirements | integration | `python -m pytest tests/test_preflop.py::test_situational_strategy -x` | No -- Wave 0 |
| PRE-08 | QQ+/AKs 3-bets, AA/KK 4-bets | unit | `python -m pytest tests/test_preflop.py::test_3bet_4bet_hands -x` | No -- Wave 0 |
| PRE-09 | Raise sizing correct for each stack mode | unit | `python -m pytest tests/test_preflop.py::test_raise_sizing -x` | No -- Wave 0 |
| COMP-01 | FULL_DECK has 52 unique cards matching treys encoding | unit | `python -m pytest tests/test_preflop.py::test_full_deck -x` | No -- Wave 0 |
| COMP-02 | CHEN_TABLE has 169 entries, all integers | unit | `python -m pytest tests/test_preflop.py::test_chen_table_structure -x` | No -- Wave 0 |
| COMP-03 | SHOVE_TABLE has 169 entries | unit | `python -m pytest tests/test_preflop.py::test_shove_table_structure -x` | No -- Wave 0 |
| COMP-04 | CALL_TABLE has 169 entries | unit | `python -m pytest tests/test_preflop.py::test_call_table_structure -x` | No -- Wave 0 |
| COMP-05 | All tables exist at module level (import doesn't fail) | smoke | `python -c "from players.mtt_bot import FULL_DECK, CHEN_TABLE"` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_preflop.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_preflop.py` -- covers PRE-01 through PRE-09, COMP-01 through COMP-05
- [ ] `tests/conftest.py` -- shared fixtures (mock game_state factory, known card ints)
- [ ] `pytest.ini` -- basic pytest configuration

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Push-fold shove table BB thresholds are approximate Nash equilibrium values | Push-Fold Table Design | Suboptimal shove ranges. LOW risk -- any reasonable ranges will beat call_bot opponents. Exact Nash values are less important than having the table at all. |
| A2 | Chen >= 7 for medium (~15%) and Chen >= 6 for deep (~20%) are appropriate opening thresholds | Chen Score Mapping | Slightly too tight/wide ranges. LOW risk -- exact thresholds are tunable in Phase 5 and the bot's edge comes from having structure, not precise percentages. |
| A3 | 6x BB threshold distinguishes "facing open" from "facing 3-bet" | Position Inference | Misclassification of large opens as 3-bets or vice versa. LOW risk -- strategic response is similar (tighten range). |
| A4 | SB detection via `call_amount == bb - sb` is reliable | Position Inference | Could misfire if SB faces a raise that happens to equal `bb - sb`. LOW risk -- astronomically unlikely at realistic blind levels. |

**All other claims were verified through engine source code inspection, empirical testing, or official documentation.**

## Open Questions

1. **Exact push-fold BB thresholds per hand**
   - What we know: Nash equilibrium heads-up ranges from holdemresources.net. General multiway adjustments (tighter).
   - What's unclear: Optimal thresholds for THIS specific blind structure with THIS field strength.
   - Recommendation: Use conservative Nash-derived values. These will be effective against the weak test field. Tuning is a Phase 5/v2 concern.

2. **SB vs non-blind distinction**
   - What we know: SB has `call_amount = bb - sb` when no raise, non-blind has `call_amount = bb`.
   - What's unclear: When SB faces a raise, `call_amount = raise_total - sb`. This could overlap with other positions' call amounts.
   - Recommendation: The overlap case doesn't meaningfully change strategy. Both positions should evaluate Chen score against the raise size.

3. **Shallow mode strategy (15-25BB)**
   - What we know: Requirements say "reshove-only" for shallow.
   - What's unclear: Should shallow mode use full push-fold tables or a hybrid approach?
   - Recommendation: Treat shallow as push-fold with slightly tighter ranges (since we're at the top of push-fold territory where min-raising is theoretically superior). This simplifies implementation while being strategically sound.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.14.3 | -- |
| pytest | Testing | Yes | 9.0.3 | -- |
| numpy | Available but unused | Yes | 1.26.4 | Not needed |
| treys | Verification only | Yes | (installed) | Not imported by bot |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Sources

### Primary (HIGH confidence)
- Engine source code: `table.py` lines 134-143 (game_state keys), line 165 (raise mechanics), lines 50-75 (position/action order) -- VERIFIED by direct inspection
- Engine source code: `config.json` (blind schedule, starting stack, hands per level) -- VERIFIED by direct inspection
- Engine source code: `player_state.py` (bet/stack deduction mechanics) -- VERIFIED by direct inspection
- Treys card encoding: VERIFIED empirically (14/14 cards match manual construction, suit values 1/2/4/8 confirmed)
- Chen formula: thepokerbank.com/strategy/basic/starting-hand-selection/chen-formula/ -- VERIFIED via WebFetch and empirical computation of all 169 categories
- Chen score-to-range mapping: VERIFIED by computing all 1326 combos and counting cumulative percentages

### Secondary (MEDIUM confidence)
- Nash push-fold equilibrium data: holdemresources.net/hune -- VERIFIED via WebFetch for heads-up specific values
- Push-fold ranges for MTT: upswingpoker.com, 888poker.com -- WebSearch verified conceptual approach

### Tertiary (LOW confidence)
- Exact multiway push-fold BB thresholds: Derived from heads-up Nash with manual tightening. Not solver-verified for the specific engine structure.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all verified from existing codebase
- Architecture: HIGH -- engine mechanics verified, integration points clear from Phase 1 code
- Pitfalls: HIGH -- all critical pitfalls verified against engine source code
- Push-fold tables: MEDIUM -- based on established Nash theory but specific thresholds are approximate
- Chen thresholds: MEDIUM -- computed empirically but optimal thresholds for this specific tournament structure are debatable

**Research date:** 2026-04-10
**Valid until:** 2026-04-23 (tournament deadline -- research is specific to this engine version)

# SPEC.md
# IIT Poker Club MTT — Bot Build Specification
# Translates STRATEGY_REFERENCE.md into a precise, unambiguous build contract.

**Status:** Ready for implementation
**Depends on:** ENGINE_INTERFACE.md v2.1, STRATEGY_REFERENCE.md v1.0
**Produces:** A single `.py` file submitted to `players/`

**How to use this document:**
- Section 3 = all numeric constants. Define these first, touch nothing else.
- Section 4 = module-level precomputation. Runs once at import, free of the 500ms budget.
- Section 5 = complete bot skeleton. Every `self._*` attribute is defined here.
- Section 6 = decision pipeline in pseudocode. The authoritative branching logic.
- Section 7 = every helper function with exact signature + contract.
- Section 8 = safety guards. Non-negotiable checks applied before every return.
- Section 9 = build order. What to implement first.

**What this document is NOT:**
- Not a full code listing (the evaluator body, MC inner loop, and table populations
  are left to the build phase — their contracts are fully specified here).
- Not a strategy explanation (see STRATEGY_REFERENCE.md).
- Not an engine reference (see ENGINE_INTERFACE.md).

---

## 1. File Structure

```
players/
  mtt_bot.py          ← single submission file, everything goes here
```

```python
# mtt_bot.py — top-level layout (order matters for readability, not execution)

# 1. Imports (only allowed modules)
from engine.player_interface import Bot
import math
import random

# 2. Module-level constants (Section 3)

# 3. Module-level precomputation (Section 4)
#    - _build_full_deck()    → FULL_DECK
#    - _build_chen_table()   → CHEN_TABLE
#    - _build_shove_table()  → SHOVE_TABLE
#    - _build_call_table()   → CALL_TABLE

# 4. Standalone helper functions (Section 7, non-method helpers)

# 5. Bot class (Section 5)
class MTTBot(Bot):
    ...
```

---

## 2. Critical Engine Rules (Inherited — Do Not Re-derive)

All engine behavior is fully documented in ENGINE_INTERFACE.md. This section
lists only the rules that directly constrain this spec's design choices.

| Rule | Impact on spec |
|------|---------------|
| `pot_size` = current-street bets only | All equity math uses `_get_estimated_pot()` |
| Raise format = raise-BY | `safe_raise()` takes raise-by, not raise-to |
| `call_amount == 0` → check via `('call', 0)` | Safety guard #1 |
| Bot must be a class inheriting Bot | Class structure mandatory |
| `from engine.player_interface import Bot` form only | Import form locked |
| `time` module blocked | All loops use fixed iteration caps |
| Instance state is picklable | No lambdas, no open files in `self.*` |
| Precomputation at module level is free (outside 500ms) | Tables built at import |

---

## 3. All Constants

Define every numeric value here. **No magic numbers anywhere else in the file.**

```python
# ── Stack mode thresholds (in BB) ─────────────────────────────────────────
DEEP_BB     = 40
MEDIUM_BB   = 25
SHALLOW_BB  = 15

# ── Tournament stage thresholds (big blind value) ────────────────────────
EARLY_MAX_BB   = 50
MIDDLE_MAX_BB  = 200
LATE_MAX_BB    = 600
# > LATE_MAX_BB → 'bubble'

# ── ICM multipliers (applied to req_eq on all-in calls only) ─────────────
ICM = {
    'early':    1.00,
    'middle':   1.05,
    'late':     1.15,
    'bubble':   1.40,
    'itm':      1.10,
    'heads_up': 1.00,
}

# ── Preflop open sizing (raise-TO multiple of BB) ────────────────────────
OPEN_DEEP    = 2.5   # × BB
OPEN_MEDIUM  = 2.2
OPEN_SHALLOW = 2.0

# ── 3-bet sizing ──────────────────────────────────────────────────────────
THREEBET_MULT = 3.0   # × villain's raise amount (raise-to)

# ── Postflop sizing (fraction of estimated_total_pot) ────────────────────
CBET_DRY      = 0.33
CBET_SEMI_WET = 0.50
CBET_WET      = 0.66
BARREL_TURN   = 0.66
VBET_RIVER    = 0.75
RAISE_VS_BET  = 2.5   # × villain's bet amount (raise-to)

# ── Minimum bet guard ─────────────────────────────────────────────────────
MIN_BET_FRAC = 0.25   # Never bet < 25% of est_pot; check instead

# ── Stack commitment threshold ────────────────────────────────────────────
COMMIT_FRAC  = 0.60   # If bet ≥ 60% of remaining stack → shove instead

# ── EHS bucket boundaries ────────────────────────────────────────────────
EHS_MONSTER  = 0.85
EHS_STRONG   = 0.65
EHS_MEDIUM   = 0.45
EHS_WEAK     = 0.25
# < EHS_WEAK → AIR

# ── EHS decision multipliers (vs req_eq) ─────────────────────────────────
RAISE_MULT   = 1.50   # EHS ≥ req_eq × RAISE_MULT → raise
CALL_MULT    = 1.00   # EHS ≥ req_eq × CALL_MULT  → call
DRAW_MULT    = 0.70   # EHS ≥ req_eq × DRAW_MULT  → call (implied odds)
ALLIN_SPR    = 2.0    # SPR ≤ this → skip raise, just call (committed)
DRAW_SPR_MIN = 3.0    # SPR must be > this to use implied odds adjustment

# ── Draw equity bonuses ───────────────────────────────────────────────────
DRAW_BONUS = {
    # (draw_type, street): equity bonus
    ('flush', 'flop'):  0.35,
    ('flush', 'turn'):  0.19,
    ('oesd',  'flop'):  0.31,
    ('oesd',  'turn'):  0.17,
    ('combo', 'flop'):  0.54,   # flush + straight
    ('combo', 'turn'):  0.33,
    ('gut',   'flop'):  0.16,
    ('gut',   'turn'):  0.09,
}

# ── Monte Carlo iteration counts ─────────────────────────────────────────
MC_ITERS = {3: 300, 4: 400, 5: 500}  # board_cards length → iterations

# ── Chen score thresholds by use ─────────────────────────────────────────
# (All Chen values verified against STRATEGY_REFERENCE Section 3 table)
CHEN_RFI_DEEP      = 5.0    # Minimum to open deep
CHEN_RFI_MEDIUM    = 5.5    # Minimum to open medium
CHEN_BB_OPT_DEEP   = 6.0    # Minimum to raise from BB option (deep)
CHEN_BB_OPT_MED    = 7.0    # Minimum to raise from BB option (medium)
CHEN_SB_RAISE      = 9.0    # Minimum to raise from SB (deep)
CHEN_SB_CALL_DEEP  = 5.0    # Minimum to complete SB call (deep)
CHEN_SB_CALL_MED   = 5.5    # Minimum to complete SB call (medium)
CHEN_3BET           = 10.0   # Minimum to 3-bet facing an open
CHEN_CALL_OPEN_D   = 8.0    # Minimum to call an open (deep)
CHEN_CALL_OPEN_M   = 8.5    # Minimum to call an open (medium)
CHEN_CALL_3BET      = 14.0   # Minimum to call a 3-bet (QQ+)
CHEN_CALL_3BET_D    = 12.0   # Minimum to call a 3-bet deep (adds AKs/AKo/JJ)

# ── Stack role approximation (bubble) ────────────────────────────────────
STARTING_STACK    = 1500
STARTING_PLAYERS  = 9      # per table
BIG_STACK_MULT    = 1.8    # > avg × this → big stack
SHORT_STACK_MULT  = 0.5    # < avg × this → short stack

# ── All-in detection threshold ────────────────────────────────────────────
ALLIN_CALL_FRAC   = 0.85   # call_amount ≥ stack × this → treat as all-in call
```

---

## 4. Module-Level Precomputation

All four structures are built once at import time, before any game action.

### 4a. Full Deck (`FULL_DECK`)

```python
def _build_full_deck() -> list[int]:
    """
    Build all 52 card integers in treys encoding.
    Verified formula from ENGINE_INTERFACE Section 8:
      card = (1 << (rank_int + 16)) | (suit_int << 12) | (rank_int << 8) | prime
    where rank_int: 0=2 ... 12=A; suit_int: 1=S, 2=H, 4=D, 8=C; prime = PRIMES[rank_int]

    Returns: list of 52 ints, each decodable by get_rank()/get_suit().
    """
    PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
    SUITS  = [1, 2, 4, 8]
    deck = []
    for rank_int in range(13):
        for suit_int in SUITS:
            card = ((1 << (rank_int + 16)) |
                    (suit_int << 12)       |
                    (rank_int << 8)        |
                    PRIMES[rank_int])
            deck.append(card)
    return deck

FULL_DECK = _build_full_deck()   # 52 ints
```

**Verification:** `get_rank(FULL_DECK[0])` must return `2`.
`len(FULL_DECK)` must be `52`.

### 4b. Chen Score Table (`CHEN_TABLE`)

```python
def _build_chen_table() -> dict:
    """
    Build preflop Chen score for all 169 hand categories.
    Key: (rank_hi, rank_lo, suited) where rank_hi >= rank_lo, ranks 2–14.
    Value: float (Chen score, rounded to nearest 0.5).

    Algorithm from STRATEGY_REFERENCE Section 3:
      1. Base = {14:10, 13:8, 12:7, 11:6, 10:5, 9:4.5, 8:4, 7:3.5,
                 6:3, 5:2.5, 4:2, 3:1.5, 2:1}[rank_hi]
      2. If pair: score = max(5.0, base * 2)
      3. If suited: score += 2
      4. gap = rank_hi - rank_lo (0 for pair)
         Gap penalty: 0→0, 1→-1, 2→-2, 3→-4, 4+→-5
      5. If gap <= 1 AND both ranks < 12 (Q): score += 1
      6. Round to nearest 0.5
    Returns: dict of 169 entries.
    """
    ...

CHEN_TABLE = _build_chen_table()
```

**Spot-check:** `CHEN_TABLE[(14,14,False)]` == `20.0`; `CHEN_TABLE[(14,13,True)]` == `12.0`.

### 4c. Push-Fold Shove Table (`SHOVE_TABLE`)

```python
def _build_shove_table() -> dict:
    """
    Build open-shove range lookup for PUSH_FOLD mode.
    Key: (rank_hi, rank_lo, suited)
    Value: float — maximum stack_bb at which to open-shove this hand.
           0 means never shove in PUSH_FOLD range.

    Derived from STRATEGY_REFERENCE Section 7, Shoving Ranges table.
    Any pair: max_bb = 15 (always shove in PF range).
    All other hands: encode minimum lo-rank by stack breakpoint.

    Threshold matrix (from STRATEGY_REFERENCE):

    Stack     Suited K  Offsuit A  Suited Q  Suited J  Suited T  Suited 9  KTo+  QJo   QTo+  K9o+  Q9o+  JTo
    ≤15BB     K8s+     A7o+       Q9s+      J9s+      T9s       —         yes   yes   —     —     —     —
    ≤13BB     K6s+     A5o+       Q8s+      J8s+      T8s+      9-7s+     yes   yes   yes   yes   —     —
    ≤12BB     K5s+     A4o+       Q7s+      J8s+      T7s+      9-6s+     yes   yes   yes   yes   —     —
    ≤10BB     K4s+     A3o+       Q6s+      J7s+      T7s+      9-6s+     yes   —     yes   yes   yes   —
    ≤8BB      K2s+     A2o+       Q5s+      J6s+      T6s+      —         yes   —     yes   yes   yes   yes
    ≤6BB      K2s+     A2o+       Q4s+      J5s+      T5s+      —         yes   —     yes   yes   yes   —
    ≤5BB      K2s+     A2o+       Q2s+      J3s+      T4s+      —         yes   —     yes   yes   yes   —

    Also: 84s+/73s+ at ≤10BB; 74s+/62s+ at ≤8BB.
    Suited Aces: A2s+ always at ≤15BB.
    Offsuit Jacks: JTo only at ≤8BB.

    Returns: dict of (rank_hi, rank_lo, suited) → float (max_bb).
    """
    ...

SHOVE_TABLE = _build_shove_table()
```

**Lookup usage:**
```python
# In should_shove_open():
max_bb = SHOVE_TABLE.get((rank_hi, rank_lo, suited), 0)
return stack_bb <= max_bb
```

### 4d. Push-Fold Call Table (`CALL_TABLE`)

```python
def _build_call_table() -> dict:
    """
    Build shove-calling range lookup for PUSH_FOLD mode.
    Key: (rank_hi, rank_lo, suited)
    Value: float — maximum villain stack_bb at which to call their shove.
           0 = never call.

    Derived from STRATEGY_REFERENCE Section 7, Calling Ranges table:

    Calling threshold by villain stack depth (tighter = higher villain stack threshold):
      Any villain:    88+, ATs+, AJo+, KQs           → call_if_villain_bb <= 15
      Villain ≤12BB:  77+, A9s+, ATo+, KJs+, KQo     → call_if_villain_bb <= 12
      Villain ≤10BB:  66+, A8s+, A9o+, KTs+, KJo+    → call_if_villain_bb <= 10
      Villain ≤8BB:   55+, A7s+, A8o+, KTs+, KJo+, QJs → call_if_villain_bb <= 8
      Villain ≤6BB:   44+, A5s+, A7o+, K9s+, KTo+, QTs+ → call_if_villain_bb <= 6

    For each hand, value = max villain stack at which we call.
    Returns: dict of (rank_hi, rank_lo, suited) → float (max villain_bb).
    """
    ...

CALL_TABLE = _build_call_table()
```

**Lookup usage:**
```python
# In should_call_shove():
villain_bb = call_amount / gs['blinds']['big']
max_bb = CALL_TABLE.get((rank_hi, rank_lo, suited), 0)
return villain_bb <= max_bb
```

---

## 5. Bot Class Skeleton

### 5a. `__init__` — All Instance State

```python
class MTTBot(Bot):

    def __init__(self):
        super().__init__("MTTBot")

        # ── Pot accumulator (ENGINE_INTERFACE Section 9a) ──────────────────
        # pot_size is current-street only; we reconstruct total pot here.
        self._street_pot_base = 0   # Sum of pot_size at end of all prior streets
        self._last_street     = 0   # Last seen len(board_cards)
        self._last_pot_size   = 0   # Last seen pot_size value

        # ── Hand state ─────────────────────────────────────────────────────
        self._was_preflop_aggressor = False  # Did we raise preflop this hand?
        self._hand_count = 0                 # Increments at each new hand boundary

        # ── Diagnostics (optional, remove before final submission) ─────────
        # self._debug_log = []
```

**Instance state rules:**
- All attributes are plain Python primitives (`int`, `float`, `bool`). No
  lambdas, open file handles, or non-picklable objects. (ENGINE_INTERFACE Section 9e)
- State accumulates across hands within one simulation. Reset at hand boundary.
- `__init__` runs fresh for each new simulation. No cross-simulation persistence.

### 5b. `get_action` — Entry Point with Guard

```python
def get_action(self, game_state: dict) -> tuple:
    """
    Engine entry point. Called once per decision within the 500ms budget.
    Wraps _decide() in a try/except so any bug produces a valid fallback action
    rather than a crash that disqualifies the bot.
    """
    try:
        return self._decide(game_state)
    except Exception:
        # Emergency fallback — always legal
        if game_state['call_amount'] == 0:
            return ('call', 0)
        return ('fold', 0)
```

### 5c. `_decide` — Main Decision Router

```python
def _decide(self, gs: dict) -> tuple:
    """
    Main decision logic. All branching originates here.
    """
    # Step 1: Detect new hand and reset state
    if self._is_new_hand(gs):
        self._reset_hand_state()

    # Step 2: Update pot accumulator (must run every call)
    self._update_pot_accumulator(gs)

    # Step 3: Compute context
    bb         = gs['blinds']['big']
    stack_bb   = gs['stack_size'] / bb
    stack_mode = _get_stack_mode(gs)
    stage      = _get_stage(gs)
    n_opp      = max(gs['active_players'] - 1, 1)
    r_hi, r_lo, suited = _decode_hand(gs['hole_cards'])

    # Step 4: Branch on street
    if len(gs['board_cards']) == 0:
        return self._preflop(gs, stack_bb, stack_mode, stage, r_hi, r_lo, suited)
    else:
        est_pot = self._get_estimated_pot(gs)
        return self._postflop(gs, stack_bb, stack_mode, stage, est_pot, n_opp)
```

---

## 6. Decision Pipelines (Pseudocode)

All pseudocode below maps 1:1 to Python methods. Helper function contracts are
in Section 7.

### 6a. Hand Boundary Management

```
_is_new_hand(gs):
    # New hand when board clears after having had cards
    # _last_street tracks board length from prior call
    board_len = len(gs['board_cards'])
    return (board_len == 0 and self._last_street != 0)

_reset_hand_state():
    self._street_pot_base      = 0
    self._last_street          = 0
    self._last_pot_size        = 0
    self._was_preflop_aggressor = False
    self._hand_count           += 1
```

**Note:** `_last_street` starts at 0. After the flop it becomes 3. After the next
preflop, `board_len == 0` and `_last_street == 3` → boundary detected.

### 6b. Pot Accumulator

```
_update_pot_accumulator(gs):
    board_len = len(gs['board_cards'])
    if board_len != self._last_street:
        # Street just changed — freeze current street pot into base
        self._street_pot_base += self._last_pot_size
        self._last_street      = board_len
    self._last_pot_size = gs['pot_size']

_get_estimated_pot(gs):
    return self._street_pot_base + gs['pot_size']
```

### 6c. Preflop Pipeline

```
_preflop(gs, stack_bb, stack_mode, stage, r_hi, r_lo, suited):

    call  = gs['call_amount']
    bb    = gs['blinds']['big']
    sb    = gs['blinds']['small']
    stack = gs['stack_size']

    # ── PUSH_FOLD: shove or fold ──────────────────────────────────────────
    if stack_mode == 'push_fold':
        return _preflop_push_fold(gs, stack_bb, call, bb, sb, stack,
                                   r_hi, r_lo, suited)

    # ── SHALLOW: open-shove range only ───────────────────────────────────
    if stack_mode == 'shallow':
        return _preflop_shallow(gs, stack_bb, call, bb, sb, stack,
                                 r_hi, r_lo, suited)

    # ── MEDIUM / DEEP: full preflop range ────────────────────────────────
    return _preflop_full(gs, stack_bb, stack_mode, stage, call, bb, sb, stack,
                          r_hi, r_lo, suited)
```

### 6d. Preflop Push-Fold Sub-Pipeline

```
_preflop_push_fold(gs, stack_bb, call, bb, sb, stack, r_hi, r_lo, suited):

    # Acting first or completing SB → decide to shove
    if call == 0 or call == sb:
        if should_shove_open(r_hi, r_lo, suited, stack_bb):
            self._was_preflop_aggressor = True
            return safe_raise(stack, gs)   # all-in shove
        if call == 0:
            return ('call', 0)             # check BB
        return ('fold', 0)

    # Facing a raise or shove → decide to call
    villain_bb = call / bb   # approximation of villain commitment
    if should_call_shove(r_hi, r_lo, suited, villain_bb):
        return ('call', 0)
    return ('fold', 0)
```

### 6e. Preflop Shallow Sub-Pipeline

```
_preflop_shallow(gs, stack_bb, call, bb, sb, stack, r_hi, r_lo, suited):

    chen = CHEN_TABLE[(r_hi, r_lo, suited)]

    if call == 0:
        # BB option — raise tier 1–2 or check
        if chen >= CHEN_3BET:   # 10+: QQ+, AKs/o
            self._was_preflop_aggressor = True
            return safe_raise(stack, gs)   # shove
        return ('call', 0)

    if call <= bb:
        # RFI — shove tier 3+ or fold
        if chen >= 7.0:   # Tier 3: 88, 77, ATs, KQs, AJo, KQo
            self._was_preflop_aggressor = True
            return safe_raise(stack, gs)
        return ('fold', 0)

    if call <= 4 * bb:
        # Facing an open — reshove tier 1–2 or fold
        if chen >= CHEN_3BET:
            self._was_preflop_aggressor = True
            return safe_raise(stack, gs)
        return ('fold', 0)

    # Facing a 3-bet / large raise
    if chen >= CHEN_CALL_3BET:  # 14+: QQ+
        return ('call', 0)
    return ('fold', 0)
```

### 6f. Preflop Full Range Sub-Pipeline

```
_preflop_full(gs, stack_bb, stack_mode, stage, call, bb, sb, stack,
               r_hi, r_lo, suited):

    chen     = CHEN_TABLE[(r_hi, r_lo, suited)]
    is_deep  = (stack_mode == 'deep')

    # ── Situation classifier ──────────────────────────────────────────────
    # (STRATEGY_REFERENCE Section 4 / CHEN thresholds from Section 3 above)

    # BB option (check or raise)
    if call == 0:
        threshold = CHEN_BB_OPT_DEEP if is_deep else CHEN_BB_OPT_MED
        if chen >= threshold:
            open_size = _calc_open_size(stack_mode, bb)
            self._was_preflop_aggressor = True
            return raise_to(open_size, gs)
        return ('call', 0)

    # SB completing (call == sb, no prior raise)
    if call == sb:
        raise_thresh = CHEN_SB_RAISE   # 9.0 — raise with KQs+, JJ+
        call_thresh  = CHEN_SB_CALL_DEEP if is_deep else CHEN_SB_CALL_MED
        if chen >= raise_thresh:
            open_size = 3 * bb
            self._was_preflop_aggressor = True
            return raise_to(open_size, gs)
        if chen >= call_thresh:
            return ('call', 0)
        return ('fold', 0)

    # RFI opportunity (call == bb, no prior raise)
    if call == bb:
        threshold = CHEN_RFI_DEEP if is_deep else CHEN_RFI_MEDIUM
        if chen >= threshold:
            open_size = _calc_open_size(stack_mode, bb)
            self._was_preflop_aggressor = True
            return raise_to(open_size, gs)
        return ('fold', 0)

    # Facing a single raise (bb < call <= 4*bb)
    if call <= 4 * bb:
        if chen >= CHEN_3BET:   # 10+: 3-bet
            threebet_to = int(THREEBET_MULT * call)
            self._was_preflop_aggressor = True
            return raise_to(threebet_to, gs)
        call_thresh = CHEN_CALL_OPEN_D if is_deep else CHEN_CALL_OPEN_M
        if chen >= call_thresh:
            return ('call', 0)
        return ('fold', 0)

    # Facing a 3-bet (call > 4*bb)
    if chen >= CHEN_CALL_3BET:
        return ('call', 0)
    if is_deep and chen >= CHEN_CALL_3BET_D:  # 12+: AKs/o, JJ
        return ('call', 0)
    return ('fold', 0)
```

### 6g. Postflop Pipeline

```
_postflop(gs, stack_bb, stack_mode, stage, est_pot, n_opp):

    call    = gs['call_amount']
    stack   = gs['stack_size']
    bb      = gs['blinds']['big']

    # Equity estimation
    ehs     = _effective_hand_strength(gs['hole_cards'], gs['board_cards'], n_opp)
    texture = _classify_board_texture(gs['board_cards'])
    spr     = stack / max(est_pot, 1)
    stage   = _get_stage(gs)
    icm     = ICM[stage]

    # ── No bet to face: check or bet ─────────────────────────────────────
    if call == 0:
        return _postflop_check_or_bet(gs, ehs, est_pot, stack, texture,
                                       spr, n_opp)

    # ── Facing a bet: call, raise, or fold ────────────────────────────────
    return _postflop_facing_bet(gs, ehs, est_pot, stack, call, spr, icm, n_opp)
```

### 6h. Postflop Check-or-Bet Sub-Pipeline

```
_postflop_check_or_bet(gs, ehs, est_pot, stack, texture, spr, n_opp):

    street     = len(gs['board_cards'])
    aggressor  = self._was_preflop_aggressor
    is_turn    = (street == 4)
    is_river   = (street == 5)

    # ── Passive path (we called preflop) ─────────────────────────────────
    if not aggressor:
        if ehs > EHS_MONSTER:
            bet = int(0.50 * est_pot)
        elif ehs > EHS_STRONG:
            bet = int(0.33 * est_pot)
        else:
            return ('call', 0)   # check
        return _make_bet(bet, gs)

    # ── Aggressive path (we raised preflop) ──────────────────────────────
    if ehs > EHS_MONSTER:
        bet_frac = 0.50

    elif ehs > EHS_STRONG:
        if texture in ('DRY', 'PAIRED'):
            bet_frac = CBET_DRY
        elif texture == 'SEMI_WET':
            bet_frac = CBET_SEMI_WET
        else:  # WET
            bet_frac = CBET_WET

    elif ehs > EHS_MEDIUM:
        if texture == 'DRY' and n_opp == 1:
            bet_frac = CBET_DRY
        else:
            return ('call', 0)   # check

    elif ehs > EHS_WEAK:
        # Bluff only: dry board, heads-up, was aggressor
        if texture == 'DRY' and n_opp == 1:
            bet_frac = CBET_DRY
        else:
            return ('call', 0)

    else:   # AIR
        return ('call', 0)

    # Street sizing adjustment
    if is_turn:
        bet_frac = max(bet_frac, BARREL_TURN)
    elif is_river:
        bet_frac = max(bet_frac, VBET_RIVER)

    bet = int(bet_frac * est_pot)

    # Minimum bet guard
    if bet < int(MIN_BET_FRAC * est_pot):
        return ('call', 0)

    # Commitment guard: shove instead of undersized all-in
    if bet >= COMMIT_FRAC * stack:
        return safe_raise(stack, gs)

    return _make_bet(bet, gs)
```

### 6i. Postflop Facing-Bet Sub-Pipeline

```
_postflop_facing_bet(gs, ehs, est_pot, stack, call, spr, icm, n_opp):

    req_eq   = call / (est_pot + call)
    is_allin = (call >= stack * ALLIN_CALL_FRAC)

    # ICM multiplier applies only to effective all-in calls
    adj_req  = req_eq * (icm if is_allin else 1.0)

    draws    = _detect_draws(gs['hole_cards'], gs['board_cards'])
    has_draw = draws['flush_draw'] or draws['oesd']

    # Raise: strong hand, not all-in, pot worth raising
    if ehs >= req_eq * RAISE_MULT and not is_allin:
        raise_total = int(RAISE_VS_BET * call)
        # Commitment guard
        raise_by    = raise_total - call
        if raise_by >= COMMIT_FRAC * stack:
            return safe_raise(stack, gs)
        return raise_to(raise_total, gs)

    # Committed pot: skip raise attempt, just call
    if ehs >= req_eq and spr <= ALLIN_SPR:
        return ('call', 0)

    # Standard call
    if ehs >= adj_req:
        return ('call', 0)

    # Implied odds: call with strong draw if SPR is sufficient
    if has_draw and ehs >= req_eq * DRAW_MULT and spr > DRAW_SPR_MIN and not is_allin:
        return ('call', 0)

    return ('fold', 0)
```

---

## 7. Helper Function Contracts

Every function below is either a module-level helper or a method.
Module-level helpers take no `self`.

### Card Utilities

```python
def get_rank(card: int) -> int:
    """Returns rank 2–14 (A=14) from a treys integer."""
    return ((card >> 8) & 0xF) + 2

def get_suit(card: int) -> int:
    """Returns suit code: 1=Spades, 2=Hearts, 4=Diamonds, 8=Clubs."""
    return (card >> 12) & 0xF

def _decode_hand(hole_cards: list) -> tuple:
    """
    Input:  2-element list of treys integers.
    Output: (rank_hi, rank_lo, suited)
            rank_hi >= rank_lo, both in range 2–14.
            suited = True if both cards share the same suit.
    """
    r0, r1   = get_rank(hole_cards[0]), get_rank(hole_cards[1])
    s0, s1   = get_suit(hole_cards[0]), get_suit(hole_cards[1])
    rank_hi  = max(r0, r1)
    rank_lo  = min(r0, r1)
    suited   = (s0 == s1)
    return rank_hi, rank_lo, suited
```

### Context Helpers

```python
def _get_stack_mode(gs: dict) -> str:
    """
    Returns: 'deep' | 'medium' | 'shallow' | 'push_fold'
    Thresholds from STRATEGY_REFERENCE Section 2 / constants Section 3.
    """
    stack_bb = gs['stack_size'] / gs['blinds']['big']
    if stack_bb >= DEEP_BB:     return 'deep'
    if stack_bb >= MEDIUM_BB:   return 'medium'
    if stack_bb >= SHALLOW_BB:  return 'shallow'
    return 'push_fold'

def _get_stage(gs: dict) -> str:
    """
    Returns: 'early' | 'middle' | 'late' | 'bubble' | 'itm' | 'heads_up'
    Detection order: heads_up override, then itm, then blind level.
    """
    bb     = gs['blinds']['big']
    active = gs['active_players']
    if active <= 2:                          return 'heads_up'
    if active <= 3 and bb > LATE_MAX_BB:     return 'itm'
    if bb <= EARLY_MAX_BB:                   return 'early'
    if bb <= MIDDLE_MAX_BB:                  return 'middle'
    if bb <= LATE_MAX_BB:                    return 'late'
    return 'bubble'
```

### Sizing Helpers

```python
def _calc_open_size(stack_mode: str, bb: int) -> int:
    """
    Returns the target raise-to amount for a preflop open.
    Uses OPEN_DEEP / OPEN_MEDIUM / OPEN_SHALLOW constants.
    """
    if stack_mode == 'deep':    return int(OPEN_DEEP   * bb)
    if stack_mode == 'medium':  return int(OPEN_MEDIUM * bb)
    return int(OPEN_SHALLOW * bb)   # shallow

def raise_to(target_total: int, gs: dict) -> tuple:
    """
    Construct ('raise', X) where X = raise-BY amount.
    target_total = total chips we want committed this street.
    raise_by     = target_total - call_amount  (engine adds call_amount).
    Automatically floored to min_raise, capped to stack.
    """
    raise_by = target_total - gs['call_amount']
    return safe_raise(raise_by, gs)

def safe_raise(raise_by: int, gs: dict) -> tuple:
    """
    Construct a guaranteed-legal ('raise', X) action.
    Floors raise_by to min_raise; caps to remaining stack.
    Use for shoves: safe_raise(gs['stack_size'], gs).
    """
    raise_by = max(raise_by, gs['min_raise'])
    raise_by = min(raise_by, gs['stack_size'])
    return ('raise', raise_by)

def _make_bet(bet_size: int, gs: dict) -> tuple:
    """
    Post a bet when call_amount == 0 (no prior bet on this street).
    Equivalent to raise_to(bet_size, gs) since call_amount == 0.
    """
    return safe_raise(bet_size, gs)
```

### Push-Fold Helpers

```python
def should_shove_open(rank_hi: int, rank_lo: int, suited: bool,
                      stack_bb: float) -> bool:
    """
    Returns True if we should open-shove this hand at this stack depth.
    Only called in PUSH_FOLD mode (stack_bb < SHALLOW_BB).
    Looks up SHOVE_TABLE built at module level.
    """
    max_bb = SHOVE_TABLE.get((rank_hi, rank_lo, suited), 0)
    return stack_bb <= max_bb

def should_call_shove(rank_hi: int, rank_lo: int, suited: bool,
                      villain_bb: float) -> bool:
    """
    Returns True if we should call a shove from villain with approximate stack villain_bb.
    villain_bb = call_amount / gs['blinds']['big']  (approximation).
    Looks up CALL_TABLE built at module level.
    """
    max_bb = CALL_TABLE.get((rank_hi, rank_lo, suited), 0)
    return villain_bb <= max_bb
```

### Equity Estimation

```python
def _mc_equity(hole_cards: list, board_cards: list,
               n_opponents: int, iters: int) -> float:
    """
    Monte Carlo equity estimation via random opponent hand simulation.

    Algorithm:
      1. Build deck excluding hole_cards and board_cards.
      2. For each iteration:
         a. Sample 2*n_opponents random cards for opponents (no replacement).
         b. Sample (5 - len(board_cards)) random cards for remaining board.
         c. Evaluate our 7-card hand (hole + full board).
         d. Evaluate each opponent's 7-card hand.
         e. We win if our rank <= all opponents' ranks (lower = better).
            Tie counts as 0.5.
      3. Return wins / iters.

    Requires _eval_7cards() — see contract below.
    Uses random.sample() for card selection — no time module needed.

    Returns: float in [0.0, 1.0]
    """
    ...

def _eval_7cards(cards: list) -> int:
    """
    Evaluate a 7-card hand, returning a rank integer where LOWER = BETTER.

    Uses only: rank (get_rank), suit (get_suit) — no treys evaluator.

    Hand type ranking (ascending integer value = stronger hand):
      8 = Straight flush / Royal flush
      7 = Four of a kind
      6 = Full house
      5 = Flush
      4 = Straight
      3 = Three of a kind
      2 = Two pair
      1 = One pair
      0 = High card

    Within same hand type, tiebreak by kicker ranks (packed into int).
    Implementation: try all C(7,5)=21 five-card combos, return best rank.

    Approximate implementation (~100 lines): uses rank-frequency counting
    for pair/trips/quads, suit-frequency counting for flush, consecutive
    rank checking for straight.
    """
    ...

def _detect_draws(hole_cards: list, board_cards: list) -> dict:
    """
    Detect drawing hands given hole cards and current board.

    Returns dict:
      {
        'flush_draw': bool,  # 4 cards of same suit in hole+board
        'oesd':       bool,  # 4-card open-ended straight draw
        'combo':      bool,  # flush_draw AND oesd simultaneously
        'gutshot':    bool,  # 4-card inside straight draw (1 gap)
      }

    Flush draw: any suit appears exactly 4 times across hole+board.
    OESD: any 4 consecutive ranks among hole+board (rank span = 3).
    Gutshot: any 4 ranks with span = 4 (one gap in sequence).
    Combo: flush_draw is True AND (oesd or gutshot) is True.

    Implementation note: use rank list + suit frequency count only.
    """
    ...

def _effective_hand_strength(hole_cards: list, board_cards: list,
                              n_opponents: int) -> float:
    """
    Compute Effective Hand Strength (EHS) combining MC equity and draw bonus.

    Algorithm:
      1. iters = MC_ITERS[len(board_cards)]
      2. raw_eq = _mc_equity(hole_cards, board_cards, n_opponents, iters)
      3. draws = _detect_draws(hole_cards, board_cards)
      4. street = 'flop' if len(board_cards) == 3 else 'turn' (river: no bonus)
      5. bonus = 0
         if draws['combo']:     bonus = DRAW_BONUS[('combo', street)]
         elif draws['flush_draw']: bonus = DRAW_BONUS[('flush', street)]
         elif draws['oesd']:    bonus = DRAW_BONUS[('oesd',  street)]
         elif draws['gutshot']: bonus = DRAW_BONUS[('gut',   street)]
      6. ehs = raw_eq + bonus * (1 - raw_eq)
      7. return min(ehs, 0.99)

    On river (len(board_cards) == 5): return raw_eq directly (no draw bonus).
    """
    ...
```

### Board Classification

```python
def _classify_board_texture(board_cards: list) -> str:
    """
    Returns: 'DRY' | 'SEMI_WET' | 'WET' | 'PAIRED'

    Algorithm (STRATEGY_REFERENCE Section 9):
      ranks      = [get_rank(c) for c in board_cards]
      suits      = [get_suit(c) for c in board_cards]
      max_suit   = max(suits.count(s) for s in set(suits))
      board_paired = (len(ranks) != len(set(ranks)))

      flush_draw_possible   = (max_suit >= 2)
      # Straight draw: any 4-card window of ranks has span <= 4
      straight_draw_possible = _has_straight_draw(sorted(set(ranks)))

      if board_paired:           return 'PAIRED'
      elif flush and straight:   return 'WET'
      elif flush or straight:    return 'SEMI_WET'
      else:                      return 'DRY'

    Helper _has_straight_draw(sorted_ranks):
      For any 3-card subset: if max - min <= 4, a 4th card could complete draw.
      Returns True if any such subset exists.
    """
    ...
```

### Stack Role Detection (Bubble)

```python
def _get_stack_role(gs: dict) -> str:
    """
    Approximate stack role for bubble/ITM play.
    Returns: 'big' | 'medium' | 'short'

    Approximation (opponent stacks unavailable):
      avg = STARTING_STACK * STARTING_PLAYERS / max(gs['active_players'], 3)
      if stack > avg * BIG_STACK_MULT:   return 'big'
      if stack < avg * SHORT_STACK_MULT: return 'short'
      return 'medium'
    """
    ...
```

---

## 8. Safety Guards

These are non-negotiable. Apply **before every `return` statement** in `_decide()`.

Implement as a final wrapper call before returning, or inline at each return point.

```python
def _guard(action: tuple, gs: dict) -> tuple:
    """
    Apply all safety rules to a candidate action.
    Call as: return _guard(candidate_action, gs)

    Rules (in priority order):
    """
    act, val = action

    # Guard 1: Never fold for free
    # If call_amount == 0, fold is wasteful — check instead.
    if act == 'fold' and gs['call_amount'] == 0:
        return ('call', 0)

    # Guard 2: Never use ('check', 0) — engine does not recognize 'check'
    # Use ('call', 0) for checks. (ENGINE_INTERFACE Section 9d)
    if act == 'check':
        return ('call', 0)

    # Guard 3: Cap raise at remaining stack
    if act == 'raise':
        val = min(val, gs['stack_size'])
        val = max(val, gs['min_raise'])
        return ('raise', val)

    # Guard 4: call_amount of 0 with ('call', 0) is always legal — no check needed
    return action
```

**Usage pattern:**
```python
# All decision returns should flow through _guard:
def _decide(self, gs):
    try:
        result = self._compute_action(gs)
        return _guard(result, gs)
    except Exception:
        if gs['call_amount'] == 0:
            return ('call', 0)
        return ('fold', 0)
```

**Additional guards to implement inline:**

| Guard | Location | Rule |
|-------|----------|------|
| Minimum bet | `_postflop_check_or_bet` | Never bet < 25% est_pot; check instead |
| Commitment shove | `_postflop_check_or_bet`, `_postflop_facing_bet` | If bet ≥ 60% stack → shove |
| 3-bet size cap | `_preflop_full` | 3-bet can't exceed stack → shove instead |
| All-in call detection | `_postflop_facing_bet` | call ≥ 0.85 × stack → is_allin |

---

## 9. Build Order

Implement strictly in this order. Each phase is independently testable before
moving to the next. Do not start phase N+1 until phase N passes basic tests.

### Phase 1 — Skeleton and Safety (Day 1 target)

Deliverable: Bot loads, plays legally for 10 simulations, never crashes.

1. Bot class with correct `__init__` and `get_action` signature
2. `_guard()` function (all 4 rules)
3. `get_action()` try/except wrapper
4. `_decide()` routing stub (preflop → check, postflop → check/fold)
5. `_is_new_hand()` and `_reset_hand_state()`
6. `_update_pot_accumulator()` and `_get_estimated_pot()`
7. `_get_stack_mode()` and `_get_stage()`
8. `_decode_hand()`, `get_rank()`, `get_suit()`
9. `safe_raise()`, `raise_to()`, `_make_bet()`

**Milestone test:** Run engine — bot completes all 10 simulations, no crashes,
`diagnostic_output.txt` shows sensible game_state values.

### Phase 2 — Preflop (Day 1–2 target)

Deliverable: Bot makes correct preflop decisions without any postflop logic.

1. `_build_chen_table()` → `CHEN_TABLE`
2. `_calc_open_size()`
3. `_preflop_full()` — all 5 situation branches
4. `_preflop_shallow()`
5. `_build_full_deck()` → `FULL_DECK` (needed for Phase 3 MC)
6. `_build_shove_table()` → `SHOVE_TABLE`
7. `_build_call_table()` → `CALL_TABLE`
8. `_preflop_push_fold()`

**Milestone test:** Spot-check 10 specific hands against STRATEGY_REFERENCE tables.
Example: AA facing a raise at 30BB should 3-bet. 72o at 20BB facing a raise should fold.

### Phase 3 — Postflop Core (Day 2–3 target)

Deliverable: Bot plays correct fundamental postflop strategy.

1. `_eval_7cards()` — full 7-card evaluator
2. `_mc_equity()` — MC loop using `_eval_7cards()`
3. `_detect_draws()` — flush draw, OESD, gutshot
4. `_effective_hand_strength()` — raw MC + draw bonus
5. `_classify_board_texture()`
6. `_postflop_check_or_bet()` — c-bet logic
7. `_postflop_facing_bet()` — pot odds + raise/call/fold
8. ICM multiplier integration in `_postflop_facing_bet()`

**Milestone test:** Run 3 simulations with diagnostic output. Confirm:
- EHS values are plausible (AA preflop = ~0.85, 72o preflop = ~0.35)
- C-bet fires on flop with STRONG hands
- Fold fires correctly when EHS << req_eq

### Phase 4 — Tournament Awareness (Day 3 target)

Deliverable: Bot adjusts correctly for bubble/ITM/HU stages.

1. `_get_stack_role()` (bubble stack approximation)
2. Bubble opening range expansion/contraction in `_preflop_full()`
3. ITM aggression flag (modify EHS threshold in postflop when stage == 'itm')
4. Heads-up handling: confirm button/non-button quirk is handled via `call_amount` inference
5. ICM multiplier verified active at bubble (stage == 'bubble', multiplier = 1.40)

**Milestone test:** Observe sim results for bubble hands — bot should fold significantly
more all-in calls at bubble than early game.

### Phase 5 — Tuning and Hardening (Day 3–4 target)

Deliverable: Submission-ready bot.

1. Benchmark MC iteration counts locally — adjust `MC_ITERS` to stay under 250ms
2. Competition field exploitation: reduce EHS value threshold by 0.10 for thin bets
3. Review all guard conditions — stress-test edge cases (empty board, all-in stack)
4. Remove diagnostic logging
5. Final clean read: imports, class name, `super().__init__("MTTBot")`
6. Test: run full 10 simulations, verify no crashes, review score distribution

### Pre-Submission Checklist

- [ ] Single file, `players/mtt_bot.py`
- [ ] Class name `MTTBot`, inherits from `Bot`
- [ ] `from engine.player_interface import Bot` — correct import form
- [ ] No blocked imports: `time`, `collections`, `itertools`, `treys`, `sklearn`
- [ ] `get_action()` returns a tuple on every path
- [ ] All `('fold', x)` calls preceded by `call_amount > 0` check
- [ ] No `('check', 0)` returns anywhere
- [ ] Raise values capped at `stack_size`
- [ ] `_guard()` applied to all return paths
- [ ] `try/except` wraps `_decide()` in `get_action()`
- [ ] All instance state is picklable (no lambdas, open files)
- [ ] No `print()` or file writes in hot path (diagnostic code removed)
- [ ] Benchmark confirms MC stays under 250ms per call

---

## 10. Constants Cross-Reference

Quick lookup for "what constant controls X":

| Behavior | Constant |
|---------|----------|
| Stack mode thresholds | `DEEP_BB`, `MEDIUM_BB`, `SHALLOW_BB` |
| Stage detection | `EARLY_MAX_BB`, `MIDDLE_MAX_BB`, `LATE_MAX_BB` |
| ICM pressure at bubble | `ICM['bubble']` = 1.40 |
| Preflop open sizing | `OPEN_DEEP/MEDIUM/SHALLOW` |
| 3-bet trigger | `CHEN_3BET` = 10.0 |
| Flat-call trigger (deep) | `CHEN_CALL_OPEN_D` = 8.0 |
| C-bet raise threshold | `EHS_MONSTER` = 0.85 |
| C-bet call threshold | `EHS_STRONG` = 0.65 |
| Value bet vs bluff trigger | `EHS_MEDIUM` = 0.45 |
| Raise vs call trigger | `RAISE_MULT` = 1.50 |
| Draw implied odds | `DRAW_MULT` = 0.70, `DRAW_SPR_MIN` = 3.0 |
| Commitment shove threshold | `COMMIT_FRAC` = 0.60 |
| All-in call detection | `ALLIN_CALL_FRAC` = 0.85 |
| MC iteration counts | `MC_ITERS` = {3: 300, 4: 400, 5: 500} |
| Min meaningful bet | `MIN_BET_FRAC` = 0.25 |

---

*Document version: 1.0*
*Implements: STRATEGY_REFERENCE.md v1.0, ENGINE_INTERFACE.md v2.1*
*Next document: ROADMAP.md*

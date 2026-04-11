# Phase 5: Tournament Awareness - Research

**Researched:** 2026-04-10
**Domain:** Tournament stage detection, ICM pressure, stack-role adjustments, heads-up play
**Confidence:** HIGH

## Summary

Phase 5 adds tournament-aware decision-making to HawkEyeBot. The bot must detect which tournament stage it is in (early/middle/late/bubble/ITM/heads-up) from `active_players` and `blinds`, then adjust preflop thresholds and postflop equity requirements accordingly. The key strategic concepts are: (1) tightening at the bubble to survive into the money via an ICM calling multiplier, (2) exploiting stack-role advantages at the bubble (big stack bullies, medium stack tightens), (3) releasing ICM pressure once in the money to fight for 1st place, (4) widening ranges dramatically in heads-up, and (5) exploiting the weak random-call/fold field by lowering value bet thresholds.

The existing code is well-structured for these modifications. `_preflop()` has clear decision branches by stack mode and situation that can be augmented with tournament stage checks. `_facing_bet()` computes `req_eq` which can be multiplied by an ICM factor. `_bet_or_check()` has EHS thresholds that can be reduced for exploitation. All changes are additive -- no existing logic needs to be rewritten, only wrapped with tournament-stage-aware conditionals.

**Primary recommendation:** Add `_get_tournament_stage()` and `_get_stack_role()` methods, then thread tournament stage into `_preflop()`, `_facing_bet()`, and `_bet_or_check()` with minimal, surgical modifications to existing decision paths.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None -- user deferred all implementation decisions to Claude's discretion.

### Claude's Discretion
- D-01: Tournament stage detection (TOURN-01) -- detect early/middle/late/bubble/ITM/heads-up from blind level and active_players
- D-02: ICM calling multiplier at bubble (TOURN-02) -- multiply required equity by 1.4x for all-in calls when at bubble
- D-03: Stack role detection (TOURN-03) -- big/medium/short stack relative to average
- D-04: Bubble play adjustments (TOURN-04) -- big stack opens wider, medium stack tightens, short stack pushes
- D-05: ITM aggression switch (TOURN-05) -- release ICM pressure when 3 players remain
- D-06: Heads-up range widening (TOURN-06) -- open 55%+ of hands, handle button-posts-BB engine quirk
- D-07: Field exploitation (TOURN-07) -- reduce EHS value bet threshold by 0.10 against weak/passive fields
- D-08: Integration approach -- add methods, modify existing preflop/postflop methods
- D-09: All new methods as class methods on HawkEyeBot

### Deferred Ideas (OUT OF SCOPE)
None -- this is the final v1 phase. All v2 items (PERF-01 through PERF-05, STRAT-01 through STRAT-04, EDGE-01 through EDGE-04) remain for post-submission optimization.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TOURN-01 | Tournament stage detection from blind level + active_players | Blind schedule analysis (11 levels, 20 hands/level), active_players from game_state, stage boundaries defined below |
| TOURN-02 | ICM calling multiplier at bubble (1.4x required equity for all-in calls) | Modifies `req_eq` in `_facing_bet()` line 1256; only applies when stage == "bubble" and call is large relative to stack |
| TOURN-03 | Big/medium/short stack role detection at bubble | `_get_stack_role()` using estimated avg_stack = total_chips / active_players; thresholds: big >= 1.5x avg, short <= 0.5x avg |
| TOURN-04 | Bubble play adjustments (big stack bullies, medium tightens, short shoves) | Modifies Chen thresholds in `_preflop()`: big stack -1, medium stack +2 to existing thresholds |
| TOURN-05 | In-money aggression switch (3 players remain) | Reset ICM multiplier to 1.0, widen Chen thresholds by -1, lower postflop value bet thresholds |
| TOURN-06 | Heads-up range widening (55%+ opening, button-posts-BB quirk) | Chen >= 3 opens ~55% of hands; engine quirk: button = BB when num_players == 2 (table.py line 55) |
| TOURN-07 | Exploit adjustments for weak/passive fields | Reduce EHS threshold in `_bet_or_check()` by 0.10 (from 0.65 to 0.55 for value betting) |
</phase_requirements>

## Standard Stack

No new libraries needed. Phase 5 uses only existing imports (`math`, `random`, `engine.player_interface.Bot`). [VERIFIED: reading mtt_bot.py lines 1-3]

All changes are to `players/mtt_bot.py` using pure Python logic -- arithmetic comparisons, dict lookups, and conditional threshold adjustments.

## Architecture Patterns

### Integration Points in Existing Code

The existing bot has a clean architecture that Phase 5 modifies surgically:

```
_decide()                          # Router (line 568)
  |-- _detect_new_hand()           # No changes
  |-- _update_pot()                # No changes
  |-- _preflop(game_state, est_pot)  # MODIFY: add tournament stage checks
  |     |-- _get_stack_mode()      # No changes
  |     |-- _detect_situation()    # No changes (heads-up handled by active_players check)
  |     +-- Chen threshold logic   # MODIFY: adjust thresholds by stage + stack role
  |-- _postflop(game_state, est_pot) # No changes to router
        |-- _facing_bet()          # MODIFY: apply ICM multiplier to req_eq
        |-- _bet_or_check()        # MODIFY: reduce EHS threshold for exploitation
```

### Pattern 1: Tournament Stage Detection
**What:** A pure function that maps `(active_players, blinds)` to a stage string.
**When to use:** Called at the top of `_preflop()` and `_postflop()` (or `_decide()`).
**Key insight:** `active_players` is the primary signal. Blind level is secondary for early/middle/late distinction when many players remain.

```python
# Source: engine game_state dict (player_interface.py line 19-27)
def _get_tournament_stage(self, game_state):
    """TOURN-01: Detect tournament stage."""
    n = game_state["active_players"]
    if n <= 2:
        return "heads_up"
    if n <= 3:
        return "itm"       # In the money (top 3 paid)
    if n <= 4:
        return "bubble"    # 4 players, 3 get paid
    # Many players: use blind level as proxy for progression
    bb = game_state["blinds"]["big"]
    if bb <= 30:
        return "early"     # Levels 0-1 (10/20, 15/30)
    if bb <= 100:
        return "middle"    # Levels 2-3 (25/50, 50/100)
    return "late"          # Levels 4+ (100/200+)
```

[VERIFIED: active_players field confirmed in table.py line 143; blinds dict confirmed in table.py line 141]

### Pattern 2: Stack Role Detection
**What:** Classify hero's stack as big/medium/short relative to estimated average.
**When to use:** At bubble (4 players) for differentiated play.

```python
# Source: config.json starting_stack = 1500, 10 players
def _get_stack_role(self, game_state):
    """TOURN-03: Stack role relative to average."""
    total_chips = 15000  # 10 * 1500 (chips are conserved)
    n = game_state["active_players"]
    avg_stack = total_chips / n
    my_stack = game_state["stack_size"]
    if my_stack >= avg_stack * 1.5:
        return "big"
    elif my_stack <= avg_stack * 0.5:
        return "short"
    else:
        return "medium"
```

[VERIFIED: config.json shows starting_stack=1500, simulation uses up to 50 test bots but max_players_per_table=9. Total chips depend on number of players entered. See Open Questions.]

### Pattern 3: Threshold Adjustment Pattern
**What:** Modify existing numeric thresholds with additive offsets rather than rewriting decision logic.
**When to use:** When tournament stage requires tighter or looser play.

```python
# Example: modifying Chen RFI threshold in _preflop()
# Existing (line 797): rfi_threshold = 6 if stack_mode == "deep" else 7
stage = self._get_tournament_stage(game_state)
rfi_threshold = 6 if stack_mode == "deep" else 7

if stage == "bubble":
    role = self._get_stack_role(game_state)
    if role == "big":
        rfi_threshold -= 1   # Open wider to bully
    elif role == "medium":
        rfi_threshold += 2   # Tighten to survive
    # short stack uses push-fold tables (already handled by stack_mode)
elif stage == "itm":
    rfi_threshold -= 1       # Release pressure, fight for 1st
elif stage == "heads_up":
    rfi_threshold = 3        # Open ~55% of hands
```

### Pattern 4: ICM Calling Multiplier
**What:** Multiply required equity by a factor when calling large bets at bubble.
**When to use:** In `_facing_bet()` when at bubble stage.

```python
# In _facing_bet(), after computing req_eq (line 1256):
req_eq = call_amount / (est_pot + call_amount)
if stage == "bubble":
    # Apply ICM pressure: require 40% more equity to call all-in
    req_eq *= 1.4
    req_eq = min(req_eq, 1.0)  # Cap at 1.0
```

### Anti-Patterns to Avoid

- **Rewriting existing decision branches:** All Phase 5 changes should be additive threshold adjustments, not rewrites of the preflop/postflop logic. The existing code works -- tournament awareness just tunes the knobs.
- **Applying ICM multiplier to small bets:** The 1.4x multiplier should only apply to significant all-in-type calls (where `call_amount >= stack * 0.3` or similar), not routine pot-odds calls. At bubble, folding to every small bet would be disastrous.
- **Hardcoding player count assumptions:** The engine config shows `max_players_per_table: 9` but the tournament could have any number of total entrants. Use `active_players` from game_state, not hardcoded counts.
- **Modifying module-level constants for tournament state:** Tournament stage changes per-hand. All tournament logic must be in instance methods, not module-level code.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Total chip count estimation | Dynamic chip counting from game events | Hardcoded constant `10 * 1500 = 15000` (or parameterized via total_starting from config) | Engine doesn't expose other player stacks; chips are conserved in tournament, so `num_entrants * starting_stack` is exact |
| Exact ICM model | Full ICM equity calculator with opponent stacks | Simple 1.4x calling multiplier at bubble | No opponent stack info available in game_state; a flat multiplier captures the core ICM concept without complexity |
| Position tracking in heads-up | Custom position tracking system | Check `active_players == 2` and adjust thresholds | Engine's heads-up quirk (button = BB) doesn't affect our strategy since we use call_amount for situation detection, not position labels |

## Common Pitfalls

### Pitfall 1: Total Chips Unknown
**What goes wrong:** Trying to compute average stack without knowing total chips in play.
**Why it happens:** `game_state` only contains hero's stack, not other players'. No field for total entrants.
**How to avoid:** Use a constant for total chips. With `starting_stack = 1500` from config, the total is `num_entrants * 1500`. The number of entrants is unknown at runtime but can be estimated: if the first hand has `active_players = N`, that's likely the total (assuming no instant eliminations in hand 1). Alternatively, hardcode 15000 (10 players) as the expected tournament size and accept the approximation.
**Warning signs:** `_get_stack_role()` returning wrong classifications because avg_stack estimate is off.

### Pitfall 2: Heads-Up Button-Posts-BB Quirk
**What goes wrong:** Position inference breaks in heads-up because the engine assigns button = BB (table.py line 55: `bb_idx = self.button_idx` when `num_players == 2`).
**Why it happens:** Standard poker has button = SB in heads-up. This engine reverses it.
**How to avoid:** The bot's `_detect_situation()` uses `call_amount` relative to blinds, NOT position labels. In heads-up: the SB (non-button) acts first preflop and sees `call_amount = BB - SB`. The BB (button) either sees `call_amount = 0` (BB option) or `call_amount > 0` (facing a raise). This matches the existing situation detection logic perfectly. No code change needed for situation detection -- only strategic adjustment (wider ranges).
**Warning signs:** Bot playing too tight in heads-up because it doesn't detect `active_players == 2`.
[VERIFIED: table.py lines 50-55, 74-75]

### Pitfall 3: ICM Multiplier Applied Too Broadly
**What goes wrong:** Applying the 1.4x multiplier to routine pot-odds calls (not just all-in situations) makes the bot fold too much at bubble.
**Why it happens:** `_facing_bet()` processes all bet-facing decisions, not just all-in calls.
**How to avoid:** Only apply the ICM multiplier when the call represents a significant portion of hero's stack (e.g., `call_amount >= stack * 0.3`). Small calls should use standard pot odds.
**Warning signs:** Bot's fold rate spikes dramatically at bubble across all bet sizes.

### Pitfall 4: Heads-Up Range Too Wide
**What goes wrong:** Opening 100% of hands in heads-up leads to auto-folding too many flops.
**Why it happens:** Chen >= 3 opens roughly 55% of hands which is appropriate, but going lower (e.g., Chen >= 1) opens nearly everything including hands with no postflop playability.
**How to avoid:** Chen >= 3 is the sweet spot. This corresponds to hands like K2o, Q5o, J7o -- playable in heads-up but not pure trash. Below Chen 3, hands like 72o, 83o, 94o have near-zero postflop equity.
**Warning signs:** Bot frequently calls preflop then folds to any flop c-bet because holding unplayable cards.

### Pitfall 5: Tournament Stage Detection Race Condition
**What goes wrong:** `active_players` reflects the current table, which might be a subset of the tournament after table merges.
**Why it happens:** The engine's `_active_players_count()` in `Table` counts players at the current table. After `_coalesce_tables()`, players may be merged. But `active_players` in game_state is per-table, not tournament-wide. With `max_players_per_table: 9`, tournaments with >9 entrants have multi-table phases.
**How to avoid:** This is a fundamental limitation. With 50 test bots, the tournament starts with 6+ tables of ~8-9 players each. `active_players` starts at 8-9 per table, not 50. The bot can't distinguish "8 players at my table" from "8 players total in tournament." For practical purposes: treat active_players as a reasonable proxy. When active_players drops below 5, it's likely late-stage. When it's 4, it's very likely bubble. When it's 3, ITM. When it's 2, heads-up. The bot should be conservative about early/middle/late distinctions but aggressive about bubble/ITM/heads-up detection.
**Warning signs:** Bot applies bubble strategy too early (when there are many players on other tables).
[VERIFIED: table.py line 143 uses `self._active_players_count()` which counts only current table players; tournament.py line 80 runs all tables in parallel]

### Pitfall 6: Overcomplicating BB Option in Heads-Up
**What goes wrong:** Adding special heads-up BB option logic when the existing logic already works.
**Why it happens:** Thinking the button-posts-BB quirk requires special handling for BB option.
**How to avoid:** In heads-up, the button/BB player sees `call_amount = 0` on BB option, which maps to `"bb_option"` in `_detect_situation()`. The existing BB option logic returns `("call", 0)` (free check). In heads-up with tournament awareness, we might want to raise more from BB option, but this is already handled by widening ranges generally for heads-up. No special BB option override needed.

## Code Examples

### Example 1: Complete _get_tournament_stage Implementation

```python
# [ASSUMED] Thresholds chosen based on tournament structure analysis:
# - 10 players start, 1500 chips each, 20 hands/level
# - active_players at current table is the only player count available
# - Bubble = 4 players (3 get paid per config.json payouts)
def _get_tournament_stage(self, game_state):
    """TOURN-01: Detect tournament stage from active_players and blinds."""
    n = game_state["active_players"]
    bb = game_state["blinds"]["big"]

    # Player-count-based stages (definitive)
    if n <= 2:
        return "heads_up"
    if n <= 3:
        return "itm"
    if n <= 4:
        return "bubble"

    # Blind-level-based stages (heuristic for larger tables)
    if bb <= 30:       # Levels 0-1: 10/20, 15/30
        return "early"
    if bb <= 100:      # Levels 2-3: 25/50, 50/100
        return "middle"
    return "late"      # Levels 4+: 100/200+
```

### Example 2: ICM Multiplier in _facing_bet

```python
# Surgical modification to _facing_bet (lines 1253-1279)
# After computing req_eq at line 1256:
req_eq = call_amount / (est_pot + call_amount) if (est_pot + call_amount) > 0 else 0.0

# TOURN-02: ICM calling multiplier at bubble
stage = self._get_tournament_stage(game_state)
if stage == "bubble" and call_amount >= stack * 0.3:
    req_eq = min(req_eq * 1.4, 1.0)
```

### Example 3: Preflop Threshold Adjustments

```python
# In _preflop(), around line 797, after determining base thresholds:
stage = self._get_tournament_stage(game_state)

# TOURN-06: Heads-up wide opening
if stage == "heads_up":
    # Override normal thresholds: open 55%+ of hands
    if situation == "rfi" or situation == "sb_complete":
        if chen_score >= 3:
            self._was_preflop_aggressor = True
            amt = self._preflop_raise_amount(game_state, stack_mode)
            return self._guard("raise", amt, game_state)
        else:
            return self._guard("fold", 0, game_state)
    # Facing raise in heads-up: call wider
    if situation in ("facing_open", "facing_3bet"):
        if chen_score >= 5:
            return self._guard("call", 0, game_state)
        else:
            return self._guard("fold", 0, game_state)

# TOURN-04/05: Adjust RFI thresholds for bubble/ITM
rfi_threshold = 6 if stack_mode == "deep" else 7

if stage == "bubble":
    role = self._get_stack_role(game_state)
    if role == "big":
        rfi_threshold -= 1    # Bully with wider range
    elif role == "medium":
        rfi_threshold += 2    # Tighten to survive
elif stage == "itm":
    rfi_threshold -= 1        # Fight for 1st place

# ... rest of existing preflop logic with modified threshold
```

### Example 4: Field Exploitation in _bet_or_check

```python
# In _bet_or_check(), reduce value bet threshold
# Existing threshold: ehs >= 0.65 for turn/river value bets (lines 1324, 1329)
# TOURN-07: Against weak fields, bet thinner for value

# Compute exploit adjustment (applied always since field is random bots)
exploit_adj = 0.10  # Reduce EHS requirement by 10%

# POST-11: Turn barrel with STRONG+ hands (modified)
if street == 4 and ehs >= (0.65 - exploit_adj):  # 0.55
    bet_size = self._calc_bet_size(est_pot, stack, texture, street)
    return _apply_commit(bet_size)

# POST-12: River value bet with STRONG+ hands (modified)
if street == 5 and ehs >= (0.65 - exploit_adj):  # 0.55
    bet_size = self._calc_bet_size(est_pot, stack, texture, street)
    return _apply_commit(bet_size)
```

## Tournament Structure Analysis

### Blind Schedule (from config.json)
[VERIFIED: config.json in engine repository]

| Level | Blinds | Start BB Depth | Hands | Cumulative Hands |
|-------|--------|----------------|-------|-----------------|
| 0 | 10/20 | 75.0 BB | 0-20 | 20 |
| 1 | 15/30 | 50.0 BB | 20-40 | 40 |
| 2 | 25/50 | 30.0 BB | 40-60 | 60 |
| 3 | 50/100 | 15.0 BB | 60-80 | 80 |
| 4 | 100/200 | 7.5 BB | 80-100 | 100 |
| 5 | 200/400 | 3.8 BB | 100-120 | 120 |
| 6+ | 300/600+ | <2.5 BB | 120+ | 140+ |

**Key observations:**
- Blinds escalate aggressively. By level 3 (hand 60), starting stack is only 15 BB (push-fold territory).
- The tournament will rarely reach level 6+ because with 10 players and aggressive blinds, eliminations happen fast.
- At bubble (4 players), average stack is 3750 chips. At level 3 (50/100) that's 37.5 BB -- deep play possible. At level 4 (100/200) it's 18.8 BB -- getting shallow.

### Payout Structure
[VERIFIED: config.json]

| Position | Payout % | Points (from project description) |
|----------|----------|-----------------------------------|
| 1st | 50% | 50 points |
| 2nd | 30% | 30 points |
| 3rd | 20% | 20 points |
| 4th+ | 0% | 0 points |

**Strategic implication:** The jump from 4th (0 pts) to 3rd (20 pts) is the largest percentage gain. Surviving the bubble is critical. But the jump from 3rd to 1st (20 -> 50 pts, 150% increase) makes aggressive ITM play highly valuable.

### Heads-Up Engine Quirk Analysis
[VERIFIED: table.py lines 50-55]

```python
# Engine code (table.py):
self.button_idx = (self.button_idx + 1) % num_players
sb_idx = (self.button_idx + 1) % num_players
bb_idx = (self.button_idx + 2) % num_players if num_players > 2 else self.button_idx
```

When `num_players == 2`:
- `button_idx` = 0 or 1 (alternates)
- `sb_idx = (button_idx + 1) % 2` = the other player
- `bb_idx = button_idx` = **button posts the big blind**

This is reversed from standard poker (where button = SB in heads-up). However:
- Preflop action starts at `(bb_idx + 1) % 2 = sb_idx` -- SB acts first (standard)
- Postflop action starts at `sb_idx` -- SB acts first (standard)
- The call_amount-based situation detection in `_detect_situation()` works correctly regardless

**Impact on bot:** None for situation detection. The bot already uses `call_amount` relative to blinds to infer position. In heads-up, the SB sees `call_amount = BB - SB` (maps to `"sb_complete"` in deep/medium mode, or used in push-fold logic). The BB sees `call_amount = 0` (maps to `"bb_option"`). Both are correct regardless of which player is on the button.

### Total Chip Count Problem

The bot cannot know the total number of tournament entrants at runtime. `active_players` is per-table, not tournament-wide. However:
- With `max_players_per_table: 9`, a table with 4 players could mean 4 total OR 4 at this table with others eliminated elsewhere
- For stack role detection, the exact total doesn't matter much -- what matters is hero's stack relative to average at the current table
- Practical solution: track `active_players` from the first hand (before any eliminations) and store as `self._initial_players`. Then `total_chips = self._initial_players * 1500`.
- Simpler alternative: Hardcode total = 15000 (10 * 1500). If more players enter, the stack role calculation will be slightly off but still directionally correct.

**Recommendation:** Track first-hand active_players as `self._initial_table_players` in `_detect_new_hand()`. Use `total_chips_estimate = self._initial_table_players * 1500` for stack role. This adapts to different table sizes without hardcoding. [ASSUMED]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed strategy regardless of tournament stage | Stage-aware threshold adjustment | Phase 5 | Bot plays differently at bubble vs ITM vs heads-up |
| Flat equity requirements for all calls | ICM-adjusted calling at bubble | Phase 5 | Bot folds marginal all-in spots at bubble, survives into money more often |
| Fixed 65% EHS for value betting | Reduced to 55% against weak fields | Phase 5 | Bot extracts more value from random/call opponents |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Chen >= 3 opens approximately 55% of hands in heads-up | Code Examples, Pattern 3 | If actual percentage is significantly different, heads-up opening range may be too wide or narrow. Mitigated: Chen scores are well-characterized, 55% is a reasonable target. |
| A2 | ICM multiplier of 1.4x is appropriate for this payout structure | Pattern 4 | If 1.4x is too aggressive, bot folds too many profitable calls at bubble. If too low, bot calls too many marginal spots. The 50/30/20 payout is steep enough that 1.4x is a standard conservative choice. |
| A3 | First-hand active_players is a reasonable proxy for total entrants at table | Total Chip Count Problem | If engine adds players mid-tournament or starts with some eliminated, the estimate is wrong. Very unlikely given engine code. |
| A4 | Blind-level thresholds (bb <= 30 = early, bb <= 100 = middle) are appropriate | Pattern 1 | If tournaments progress faster/slower than expected, stage detection may misclassify. Low risk: the player-count-based stages (bubble/ITM/HU) are definitive and most impactful. |
| A5 | All 50 test bots are random call/fold (field is weak) | Field Exploitation | If tournament field includes stronger student-built bots, the 0.10 exploit adjustment should be less aggressive. The test bots are confirmed random, but actual tournament opponents are unknown students. |
| A6 | total_chips_estimate using initial_table_players * 1500 is sufficiently accurate | Stack Role Detection | Multi-table tournaments may have different player counts per table. Acceptable approximation since exact ICM is impossible without opponent stacks anyway. |

## Open Questions

1. **Total entrant count at runtime**
   - What we know: `active_players` is per-table (table.py line 143). Starting stack is 1500 (config.json). Max 9 per table.
   - What's unclear: With 50 test bots, the tournament has 6+ tables. `active_players` on hand 1 gives the initial table size (8-9), not total tournament size (50).
   - Recommendation: Use first-hand `active_players` times 1500 for `total_chips_estimate`. This gives per-table average stack, which is what matters for strategic decisions at the current table. The tournament-wide average is unknowable and less relevant.

2. **ICM multiplier scope -- what counts as "all-in call"?**
   - What we know: CONTEXT.md says "1.4x required equity for all-in calls" at bubble.
   - What's unclear: Does "all-in call" mean only literal all-in (call_amount >= stack) or large commitment (call_amount >= 30% stack)?
   - Recommendation: Apply to calls where `call_amount >= stack * 0.3`. This captures significant commitment decisions without over-applying to small bets. A literal all-in-only trigger would miss situations where calling 60% of stack is still a major risk at bubble.

3. **Actual tournament field composition**
   - What we know: The 50 test bots are all random call/fold. The actual tournament will have student-submitted bots.
   - What's unclear: Quality of student submissions. Could range from random bots to sophisticated implementations.
   - Recommendation: Apply the exploit adjustment (TOURN-07) unconditionally for v1. The default -0.10 EHS adjustment for value betting is profitable against weak fields and only marginally sub-optimal against strong fields (we'd just be value-betting slightly thinner than necessary).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none (pytest auto-discovery) |
| Quick run command | `python -m pytest tests/ -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOURN-01 | Stage detection returns correct stage for each player count | unit | `python -m pytest tests/test_tournament.py::TestStageDetection -x` | Wave 0 |
| TOURN-02 | ICM multiplier increases req_eq at bubble, not other stages | unit | `python -m pytest tests/test_tournament.py::TestICMMultiplier -x` | Wave 0 |
| TOURN-03 | Stack role detection: big/medium/short correct vs avg | unit | `python -m pytest tests/test_tournament.py::TestStackRole -x` | Wave 0 |
| TOURN-04 | Bubble adjustments: big stack widens, medium tightens | unit | `python -m pytest tests/test_tournament.py::TestBubblePlay -x` | Wave 0 |
| TOURN-05 | ITM: multiplier reset, ranges widen | unit | `python -m pytest tests/test_tournament.py::TestITMAggression -x` | Wave 0 |
| TOURN-06 | Heads-up: opens 55%+, handles HU game_state correctly | unit | `python -m pytest tests/test_tournament.py::TestHeadsUp -x` | Wave 0 |
| TOURN-07 | Exploit adjustment lowers value bet threshold | unit | `python -m pytest tests/test_tournament.py::TestExploitAdjustment -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -q` (~1.5s)
- **Per wave merge:** `python -m pytest tests/ -v` (~2s)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_tournament.py` -- covers TOURN-01 through TOURN-07
- [ ] Regression tests confirming Phases 1-4 behavior unchanged when tournament adjustments do not apply (early stage with many players should behave identically to current code)

## Security Domain

Not applicable. This is a single-file game bot with no network I/O, no user input, no authentication, no data storage, and no cryptography. The only interface is the engine calling `get_action(game_state)` with a dict. Security enforcement is irrelevant for this domain.

## Sources

### Primary (HIGH confidence)
- `Docs/MTT-Pokerbot-Engine/engine/table.py` -- Heads-up blind posting (line 55), game_state construction (lines 134-143), betting round logic
- `Docs/MTT-Pokerbot-Engine/engine/tournament.py` -- Tournament flow, elimination, table coalescence
- `Docs/MTT-Pokerbot-Engine/engine/config.py` -- Config loading, default values
- `Docs/MTT-Pokerbot-Engine/config.json` -- Actual blind schedule, starting stack, payouts, hands per level
- `Docs/MTT-Pokerbot-Engine/engine/player_interface.py` -- Bot base class, game_state schema
- `players/mtt_bot.py` -- Current HawkEyeBot implementation (1362 lines, Phases 1-4 complete)
- `.planning/phases/05-tournament-awareness/05-CONTEXT.md` -- User decisions (all deferred to Claude)
- `.planning/REQUIREMENTS.md` -- TOURN-01 through TOURN-07 specifications

### Secondary (MEDIUM confidence)
- Tournament math analysis (blind schedule progression, average stack calculations) -- computed from verified config.json values
- Chen score to hand percentage mapping -- based on established poker math (thepokerbank.com reference in CLAUDE.md)

### Tertiary (LOW confidence)
- None. All findings derived from direct code/config analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, pure Python modifications to existing code
- Architecture: HIGH - all integration points verified by reading actual bot code (1362 lines) and engine source
- Tournament math: HIGH - blind schedule and payouts from config.json, stack calculations from first principles
- Heads-up quirk: HIGH - verified directly from table.py line 55 with full control flow trace
- Pitfalls: HIGH - derived from code analysis of engine and bot, not speculation
- Stage detection thresholds: MEDIUM - blind-level boundaries (early/middle/late) are reasonable but approximate; player-count-based stages (bubble/ITM/HU) are definitive

**Research date:** 2026-04-10
**Valid until:** 2026-04-23 (tournament deadline -- research is specific to this tournament's engine and config)

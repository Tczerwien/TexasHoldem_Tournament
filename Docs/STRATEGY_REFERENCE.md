# STRATEGY_REFERENCE.md
# IIT Poker Club MTT — Bot Strategy Reference
# All thresholds, ranges, and sizing values for implementation

**Status:** Locked for implementation
**Depends on:** ENGINE_INTERFACE.md v2.1
**Feeds into:** SPEC.md, ROADMAP.md

**Hard constraints inherited from ENGINE_INTERFACE.md:**
- `position` not in game_state — all ranges use positional inference only
- `pot_size` broken postflop — all postflop calculations use `estimated_total_pot`
- `players_remaining` not in game_state — tournament stage inferred from blinds
- Stack depth = `stack_size / blinds['big']` only (no opponent stacks)
- `active_players` includes all-in players

---

## 1. Tournament Risk Policy

### The Scoring Math

```
1st = 50 pts | 2nd = 30 pts | 3rd = 20 pts | 4th–last = 0 pts
10 simulations, aggregate score
```

Comparing strategies over 10 simulations:

| Strategy Profile | Top-3 Rate | Avg finish when ITM | Expected pts/sim | 10-sim total |
|-----------------|------------|---------------------|-----------------|--------------|
| Always 3rd (ultra-safe) | 100% | 3rd | 20.0 | 200 |
| Consistent 2nd/3rd | 70% | 2.7th | 22.0 | 220 |
| Balanced (target) | 70% | 2.0th | 28.0 | 280 |
| Balanced-aggressive (our policy) | 65% | 1.6th | 30.3 | **303** |
| Boom-bust (first or nothing) | 40% | 1.0th | 20.0 | 200 |

The dominant strategy: **maximize top-3 rate × quality of finish when in the money.**

### Breakeven Analysis

To justify aggressive play over pure survival:
- Consistent 3rd place = 20 pts/sim
- First-place hunting breaks even vs consistent 3rd at **win rate > 40%** (20/50)
- Once in top-3, fighting for 1st (50 pts vs 20 pts) is always correct — 1st is worth 2.5× third

**Policy conclusion:**
- **Early game:** Accumulate chips aggressively. Every chip you don't win now is fold equity you won't have later.
- **Bubble (4 players or blind level 8+):** Tighten dramatically. 4th = 0. This is where tournaments are won.
- **In-money (top 3):** Maximum aggression. Fight for 1st. 3rd vs 1st = 30 pts difference.

### Risk Posture By Phase

| Phase | Active players (approx) | Blind level (BB) | Risk posture | Primary goal |
|-------|------------------------|-----------------|--------------|--------------|
| Early | 9–7 | ≤50 | Aggressive TAG | Chip accumulation |
| Middle | 6–5 | ≤200 | Standard TAG | Maintain stack |
| Bubble | ≤4 or BB≥600 | 300–2000 | ICM-tight | Survive to top-3 |
| In-money | 3 | Any | Full aggression | Win the simulation |
| Heads-up | 2 | Any | Maximum aggression | Win |

---

## 2. Stack Mode Thresholds

Stack mode is the **primary** strategic state. All preflop and postflop decisions
branch on this first.

```
stack_bb = game_state['stack_size'] / game_state['blinds']['big']
```

| Mode | Stack depth | Entry condition | Core behavior |
|------|------------|-----------------|---------------|
| DEEP | ≥ 40BB | stack_bb >= 40 | Full range, postflop play, position matters |
| MEDIUM | 25–40BB | stack_bb >= 25 | Tighter EP, simplified postflop, 3-bet-or-fold |
| SHALLOW | 15–25BB | stack_bb >= 15 | Reshove zone, open only stackable hands |
| PUSH_FOLD | < 15BB | stack_bb < 15 | Shove or fold only, no postflop |

**Critical transition — the 15–20BB zone:**
At 15–20BB, never make a small raise and then fold to a reshove. Either open-shove
(hands you'd call a shove with) or min-raise/shove the same hands. The worst play
is open-raising 2x and folding to a 3-bet all-in — you donate chips.

Rule: In SHALLOW mode, only open hands where you commit if reraised.

---

## 3. Hand Classification System

All hand evaluation uses only rank and suited status — the two things derivable
from the treys decoder without a full evaluator.

### Preflop Hand Score (Chen Formula)

Used for quick preflop ranking of all 169 hand categories:

```
Step 1 — High card base score:
  A=10, K=8, Q=7, J=6, T=5, 9=4.5, 8=4, 7=3.5, 6=3, 5=2.5, 4=2, 3=1.5, 2=1

Step 2 — Pair bonus:
  If pair: score = max(5, base_score × 2)

Step 3 — Suited bonus:
  If suited: +2

Step 4 — Gap penalty:
  Connected (0 gap): 0
  1-gap: -1
  2-gap: -2
  3-gap: -4
  4+ gap: -5

Step 5 — Straight bonus:
  If gap ≤ 1 AND both cards < Queen: +1

Step 6 — Round up to nearest 0.5
```

**Chen score reference for key hands:**

| Hand | Chen Score | Category |
|------|-----------|----------|
| AA | 20 | Premium |
| KK | 16 | Premium |
| QQ | 14 | Premium |
| JJ | 12 | Premium |
| AKs | 12 | Premium |
| TT | 10 | Strong |
| AQs | 10 | Strong |
| AKo | 10 | Strong |
| 99 | 10 | Strong |
| AJs | 9 | Strong |
| ATs | 8.5 | Playable |
| KQs | 9 | Playable |
| 88 | 8 | Playable |
| AQo | 8 | Playable |
| KJs | 8 | Playable |
| 77 | 7 | Playable |
| AJo | 7 | Playable |
| KTs | 7.5 | Playable |
| QJs | 7 | Playable |
| 66 | 6 | Speculative |
| T9s | 6.5 | Speculative |
| 55 | 5 | Speculative |
| 44 | 5 | Marginal |
| 33 | 5 | Marginal |
| 22 | 5 | Marginal |

### Hand Strength Buckets (Postflop)

Used after equity estimation:

| Bucket | Equity range | Example holdings |
|--------|-------------|------------------|
| MONSTER | > 0.85 | Flush, full house, straight, quads, trips on dry board |
| STRONG | 0.65–0.85 | Overpair, top pair top kicker, two pair |
| MEDIUM | 0.45–0.65 | Middle pair, weak top pair, strong flush/straight draw |
| WEAK | 0.25–0.45 | Bottom pair, gutshot, overcards with backdoor draw |
| AIR | < 0.25 | Complete miss, no pair, no draw |

---

## 4. Position Inference (No `position` in game_state)

Since exact position is unavailable, use call_amount and board state to infer
which positional strategy to apply.

### Preflop Position Inference

```
Preflop detection (len(board_cards) == 0):

call_amount == 0:
  → BB option (no raise) OR action checked to us late
  → Apply: BB_OPTION logic (check or raise strong hands)

call_amount == blinds['small']:
  → Likely SB completing (no raise yet)
  → Apply: SB_COMPLETE logic

call_amount == blinds['big']:
  → RFI situation — limpers or just us
  → Apply: RFI_OPEN logic (position-unknown range)

call_amount > blinds['big'] AND call_amount <= 4 × blinds['big']:
  → Facing a single raise
  → Apply: FACING_OPEN logic

call_amount > 4 × blinds['big']:
  → Facing a 3-bet or large raise
  → Apply: FACING_3BET logic (very tight)
```

### Postflop Position Proxy

Without position data, postflop aggression defaults to:
- If we raised preflop: treat as in position (we have range advantage)
- If we called preflop: treat as out of position (conservative postflop)

Track whether we were the preflop aggressor using instance state:
`self._was_preflop_aggressor` — set to True when we raise preflop.

---

## 5. Preflop Opening Ranges by Stack Mode

### DEEP Mode (≥40BB) — RFI Opening Range (~20% of hands)

**Trigger:** `call_amount == blinds['big']` (no raise yet, we're opening)

Open with:

| Category | Hands | Notes |
|----------|-------|-------|
| Pairs | 44+ | 77+ is always open, 44-66 marginal |
| Suited aces | A2s+ | All suited aces |
| Suited kings | K7s+ | Drop K2s–K6s |
| Suited queens | Q9s+ | |
| Suited jacks | JTs | Connectors only |
| Suited connectors | T9s, 98s, 87s, 76s | Gap ≤ 1 only |
| Offsuit broadways | ATo+, KJo+, QJo | Drop KTo, QTo |

**Raise sizing:** 2.5 × BB

### MEDIUM Mode (25–40BB) — RFI Opening Range (~15% of hands)

Tighten from deep range: drop speculative hands.

Open with:

| Category | Hands | Change from deep |
|----------|-------|-----------------|
| Pairs | 55+ | Drop 44 |
| Suited aces | A2s+ | Same |
| Suited kings | K9s+ | Drop K7s–K8s |
| Suited queens | QTs+ | Drop Q9s |
| Suited jacks | JTs | Same |
| Suited connectors | T9s, 98s | Drop 87s, 76s |
| Offsuit broadways | AJo+, KQo | Drop ATo, KJo, QJo |

**Raise sizing:** 2.2 × BB

### SHALLOW Mode (15–25BB) — Reshove Range (~25% of hands)

At this depth, only open hands you'll call a reshove with.
Open-shove or min-raise with commit intention only.

Open with:

| Category | Hands |
|----------|-------|
| Pairs | 66+ |
| Suited aces | A7s+ |
| Offsuit aces | ATo+ |
| Suited kings | KTs+ |
| Offsuit kings | KQo |
| Premium broadways | QJs |

**Raise sizing:** Shove (all-in) OR 2.0 × BB with intent to call reshove

### PUSH_FOLD Mode (<15BB) — See Section 7

No open-raise sizing. Shove or fold only.

---

## 6. Preflop Situational Strategy

### Facing an Open Raise (call_amount > BB, ≤ 4×BB)

**Deep mode (≥40BB):**

| Action | Hand requirement |
|--------|----------------|
| 3-bet (3× the raise) | QQ+, AKs, AKo |
| Call | JJ, TT, 99, AQs, AQo, KQs |
| Fold | Everything else |

**Medium mode (25–40BB):**

| Action | Hand requirement |
|--------|----------------|
| 3-bet (all-in if < 25BB effective) | QQ+, AKs, AKo |
| Call | JJ, TT, AQs |
| Fold | Everything else |

**Shallow mode (15–25BB):**

| Action | Hand requirement |
|--------|----------------|
| Shove | JJ+, AKs, AKo |
| Fold | Everything else |
→ No flat-calling in this zone.

### Facing a 3-Bet (we raised, someone reraised)

| Effective stack | Action | Hand requirement |
|----------------|--------|-----------------|
| ≥ 40BB | 4-bet shove | AA, KK |
| ≥ 40BB | Call | QQ, AKs, AKo, JJ (IP only) |
| ≥ 40BB | Fold | Everything else |
| < 40BB | Shove | QQ+, AKs, AKo |
| < 40BB | Fold | Everything else |

### BB Option (call_amount == 0 preflop, we're last to act)

When no one raised and we're in the BB (or late position, action checked to us):

| Stack mode | Action | Hand requirement |
|-----------|--------|-----------------|
| Deep | Raise 2.5×BB | 55+, A7s+, ATo+, KJs+, KQo, QJs, JTs, T9s |
| Medium | Raise 2.2×BB | 77+, A9s+, AJo+, KQs, KQo |
| Shallow | Shove or check | 88+, A9s+, AJo+ → shove; else check |
| Push-fold | Shove | See push-fold table |

### SB Completing (call_amount == blinds['small'])

When we're likely the SB and no one raised:

| Stack mode | Action | Range |
|-----------|--------|-------|
| Deep | Complete (call) | 22+, A2s+, K7s+, Q9s+, JTs, T9s, 98s, ATo+, KJo+ |
| Deep | Raise to 3×BB | 88+, ATs+, AJo+, KQs |
| Medium | Complete or fold | 44+, A9s+, KTs+, AJo+, KQo |
| Shallow/PF | Shove or fold | Use push-fold table |

---

## 7. Push-Fold Tables (<15BB)

In PUSH_FOLD mode, decisions are binary: shove or fold.
No postflop decisions follow.

### Shoving Ranges (Acting First — No Previous Action)

Hands are expressed as minimum requirements. All hands in the row AND stronger qualify.

| Stack | Pairs | Suited Aces | Offsuit Aces | Suited Kings | Other suited | Offsuit broadways |
|-------|-------|-------------|--------------|--------------|--------------|-------------------|
| 15BB | 22+ | A2s+ | A7o+ | K8s+ | Q9s+, J9s+, T9s, 98s | KTo+, QJo |
| 13BB | 22+ | A2s+ | A5o+ | K6s+ | Q8s+, J8s+, T8s+, 97s+ | K9o+, QTo+ |
| 12BB | 22+ | A2s+ | A4o+ | K5s+ | Q7s+, J8s+, T7s+, 96s+ | K9o+, QTo+ |
| 10BB | 22+ | A2s+ | A3o+ | K4s+ | Q6s+, J7s+, T7s+, 96s+, 85s+ | K8o+, Q9o+ |
| 8BB  | 22+ | A2s+ | A2o+ | K2s+ | Q5s+, J6s+, T6s+, 85s+, 74s+ | K7o+, Q8o+, JTo |
| 6BB  | 22+ | A2s+ | A2o+ | K2s+ | Q4s+, J5s+, T5s+, 84s+, 73s+ | K5o+, Q7o+, J9o+ |
| 5BB  | 22+ | A2s+ | A2o+ | K2s+ | Q2s+, J3s+, T4s+, 84s+, 73s+, 62s+ | K4o+, Q6o+, J8o+ |
| ≤4BB | 22+ | A2s+ | A2o+ | K2s+ | Any two broadway; most hands | K2o+, Q5o+, J8o+ |

### Calling Ranges (Facing a Shove)

Calling a shove requires higher equity since we're committing our whole stack
against a defined shoving range.

| Villain stack | Our call range |
|---------------|----------------|
| Facing any shove | 88+, ATs+, AJo+, KQs |
| ≤12BB shove | 77+, A9s+, ATo+, KJs+, KQo |
| ≤10BB shove | 66+, A8s+, A9o+, KTs+, KJo+ |
| ≤8BB shove | 55+, A7s+, A8o+, KTs+, KJo+, QJs |
| ≤6BB shove | 44+, A5s+, A7o+, K9s+, KTo+, QTs+ |

**The calling gap:** You should shove ~2× as many hands as you call with.
This asymmetry is correct — the shover has fold equity, the caller does not.

### Short-Stack Decision Priority

When stack_bb < 5:
1. Any hand in top 40% → shove
2. Facing a shove with any pair or any Ax → call
3. Otherwise fold and wait one more orbit

When stack_bb < 3 (desperation zone):
- Shove any two cards from any position except the very worst offsuit combos
- Call any shove with any pair, any Ax, K9+, Q9+ suited

---

## 8. Postflop Equity Estimation

### pot_size Is Not The Real Pot

`game_state['pot_size']` only shows current-street bets.
All postflop equity calculations must use `estimated_total_pot` from the accumulator.
See ENGINE_INTERFACE.md Section 9a for the tracking implementation.

**Rule:** Never use `pot_size` directly for pot odds on any street.
Only use `pot_size` to detect bet sizes relative to current action.

### Equity Estimation Method

For v1, use the following hierarchy by street:

**Preflop:** Use Chen score threshold lookup — no equity calculation needed.

**Flop:** Monte Carlo simulation, 200–300 iterations.
  - Deal random cards for opponents and remaining board
  - Count win/tie/loss
  - `equity = (wins + 0.5 × ties) / total_iterations`

**Turn:** Monte Carlo, 300–400 iterations (fewer unknowns, faster per iteration).

**River:** Full enumeration of all C(remaining, 2) opponent hole card combinations.
  - Approximately 900–1000 combos with 2 cards known
  - More accurate than Monte Carlo, roughly same speed

### Draw Detection and Equity Adjustment

Before using raw Monte Carlo equity, check for draws and apply bonus:

| Draw type | Outs | Equity bonus | Detection |
|-----------|------|-------------|-----------|
| Flush draw | 9 | +0.35 (flop), +0.19 (turn) | 4 cards same suit in hand+board |
| OESD (open-ended straight draw) | 8 | +0.31 (flop), +0.17 (turn) | 4-card sequence in hand+board |
| Combo draw (flush + straight) | 15 | +0.54 (flop), +0.33 (turn) | Both conditions above |
| Gutshot | 4 | +0.16 (flop), +0.09 (turn) | 4-card sequence with 1 gap |

**Effective hand strength formula:**
```
if has_strong_draw:
    EHS = raw_equity + draw_bonus × (1 - raw_equity)
else:
    EHS = raw_equity
```

Cap EHS at 0.99. Do not overcredit draws — EHS is an estimate.

### Stack-to-Pot Ratio (SPR)

```
SPR = stack_size / estimated_total_pot
```

SPR determines commitment level. Use for postflop decision gating:

| SPR | Commitment level | Stack-off threshold |
|-----|-----------------|---------------------|
| < 1.0 | Fully committed | Call with any made hand (pair+) |
| 1.0–2.5 | High | Top pair top kicker+ or strong draw |
| 2.5–5.0 | Medium | Two pair or better, or nut flush draw |
| 5.0–10 | Low | Sets, straights, flushes, or two pair on dynamic board |
| > 10 | Deep | Premium made hands only for all-in commitment |

**When SPR < 1.5 and we want to bet:** Just shove instead of making an undersized bet.
The math: if a bet commits >60% of remaining stack, make it a shove.

---

## 9. Postflop Decision Rules

### Board Texture Classification

Used to determine c-bet frequency and sizing:

| Texture | Conditions | Strategy impact |
|---------|-----------|-----------------|
| DRY | No flush draw possible (suits spread); no connected ranks; no pair | Bet aggressively, small sizing |
| SEMI_WET | One draw possible (either flush OR straight, not both) | Bet selectively, medium sizing |
| WET | Both flush AND straight draws possible, OR monotone | Bet only strong hands, large sizing |
| PAIRED | Two board cards share a rank | Bet strong hands; check medium hands |

**Wetness detection (simplified):**
```
flush_draw_possible = (max suit count on board >= 2)
straight_draw_possible = (max board rank gap across any 4-card window <= 4)
board_paired = (any two board cards share rank)

if board_paired: texture = PAIRED
elif flush_draw_possible AND straight_draw_possible: texture = WET
elif flush_draw_possible OR straight_draw_possible: texture = SEMI_WET
else: texture = DRY
```

### When Checked To (We Are First to Act or All Checked)

**If we were the preflop aggressor (c-bet decision):**

| EHS | Board texture | Action | Sizing |
|-----|--------------|--------|--------|
| MONSTER (>0.85) | Any | Bet | 50% of estimated_total_pot |
| STRONG (0.65–0.85) | DRY or PAIRED | Bet | 33% of estimated_total_pot |
| STRONG (0.65–0.85) | SEMI_WET | Bet | 50% of estimated_total_pot |
| STRONG (0.65–0.85) | WET | Bet | 66% of estimated_total_pot |
| MEDIUM (0.45–0.65) | DRY, single opponent | Bet | 33% of estimated_total_pot |
| MEDIUM (0.45–0.65) | Any other | Check | — |
| WEAK/DRAW (0.25–0.45) | DRY, single opponent, was aggressor | Bet (bluff) | 33% of estimated_total_pot |
| WEAK/DRAW (0.25–0.45) | Multi-opponent or wet | Check | — |
| AIR (<0.25) | Any | Check/fold | — |

**If we were NOT the preflop aggressor (check-behind or bet decision):**

| EHS | Action |
|-----|--------|
| MONSTER | Bet 50% pot |
| STRONG | Bet 33% pot (thin value) |
| MEDIUM or below | Check |

**Never bet into 3+ opponents without STRONG or better.**

### When Facing a Bet

Let `req_eq = call_amount / (estimated_total_pot + call_amount)`

This is the break-even equity needed to call.

| Condition | Action | Notes |
|-----------|--------|-------|
| EHS >= req_eq × 1.5 | Raise to 2.5× their bet | Strong value raise |
| EHS >= req_eq × 1.2 AND SPR < 2 | Shove | Committed — get it in |
| EHS >= req_eq | Call | Correct call by pot odds |
| EHS >= req_eq × 0.7 AND draw (OESD or flush) AND SPR > 3 | Call | Implied odds adjustment |
| EHS < req_eq | Fold | Below break-even |

**Quick pot odds reference:**

| Bet size vs pot | Required equity to call |
|----------------|------------------------|
| 25% pot | 17% |
| 33% pot | 20% |
| 50% pot | 25% |
| 66% pot | 28% |
| 100% pot | 33% |
| 150% pot | 40% |

### Turn and River Adjustments

**Turn:**
- Increase aggression with strong hands (second barrel)
- If we c-bet flop and got called: bet turn with STRONG+ (66%+ pot)
- If we c-bet flop and got called: check/give up with WEAK/AIR
- If opponent bets into us: apply pot odds formula above

**River:**
- Use full enumeration for equity (more accurate than MC)
- Value bet with STRONG+: 75% pot
- Bluff only if: (a) AIR/WEAK, (b) single opponent, (c) scare card arrived (ace or card completing a draw), (d) we were aggressor on prior streets
- Bluff sizing: match our value bet size (same sizing prevents easy reads)
- River bluff frequency cap: maximum 1/3 of river bets should be bluffs

### Multi-Street Carry-Forward

Re-evaluate equity fresh each street using Monte Carlo/enumeration.
Do NOT carry forward the previous street's equity estimate.

Track `self._was_preflop_aggressor` across streets within a hand.
Reset this flag when a new hand begins (detected by `board_cards == []` and
`stack_size` different from previous `self._last_stack`).

---

## 10. Bet Sizing Reference

All sizes reference `estimated_total_pot` postflop, and `blinds['big']` preflop.

### Preflop Sizing

| Situation | Stack mode | Size |
|-----------|-----------|------|
| Open raise (RFI) | Deep ≥40BB | 2.5 × BB |
| Open raise (RFI) | Medium 25–40BB | 2.2 × BB |
| Open raise (RFI) | Shallow 15–25BB | 2.0 × BB or shove |
| Open raise (RFI) | Push-fold <15BB | All-in only |
| 3-bet vs open | Any ≥25BB | 3× the open |
| 3-bet vs open | Any <25BB | All-in |
| 4-bet vs 3-bet | Deep only | All-in (AA/KK) |
| Isolate vs limper | Deep | Pot + 1BB per limper |

**Minimum raise floor:** Always at least `min_raise` above the current bet.
The engine corrects sub-minimum raises silently, but compute correctly regardless.

### Postflop Sizing

| Situation | Size | Notes |
|-----------|------|-------|
| C-bet (dry board) | 33% of estimated_total_pot | Small, efficient |
| C-bet (semi-wet board) | 50% of estimated_total_pot | Medium |
| C-bet (wet board) | 66% of estimated_total_pot | Large, protection |
| Turn barrel (value) | 66% of estimated_total_pot | Standard |
| River value bet | 75% of estimated_total_pot | Extract max value |
| Raise vs bet | 2.5× villain's bet | Consistent sizing |
| Bluff (all streets) | Match value bet size for that street | Same sizing for balance |

**Stack commitment rule:** If any bet would commit ≥ 60% of remaining stack,
shove instead. Do not make undersized bets that leave you pot-committed but short.

**Minimum meaningful bet:** Never bet less than 25% of estimated_total_pot.
Below this threshold: check instead (the bet accomplishes nothing strategically).

---

## 11. Tournament Stage Adjustments

### Stage Detection

```python
bb = game_state['blinds']['big']
active = game_state['active_players']

# Primary: blind level proxy
if bb <= 50:   stage = 'EARLY'
elif bb <= 200: stage = 'MIDDLE'
elif bb <= 600: stage = 'LATE'
else:           stage = 'BUBBLE'

# Secondary refinement: table size
if active <= 2: stage = 'HEADS_UP'    # override
elif active <= 3 and stage == 'BUBBLE': stage = 'ITM'  # in the money
```

### ICM Calling Multiplier

Apply to the break-even equity threshold when considering an all-in call:

```
adjusted_req_eq = req_eq × icm_multiplier
```

| Stage | Multiplier | Meaning |
|-------|-----------|---------|
| EARLY | 1.00 | Pure chip-EV |
| MIDDLE | 1.05 | Slight ICM awareness |
| LATE | 1.15 | Real ICM pressure building |
| BUBBLE | 1.40 | Major tightening — need 40% more edge to call all-in |
| ITM (3-handed) | 1.10 | Slight premium for survival, then release |
| HEADS_UP | 1.00 | Pure chip-EV, no ICM |

**ICM multiplier applies ONLY to all-in calls.** Do not apply to routine calls
and folds on normal betting streets. This is specifically the threshold for
committing your entire stack.

### Bubble Play Rules (BUBBLE stage)

Bubble = blind level 7+ (BB ≥ 600) AND active_players ≤ 4 at table.

**If we have the big stack (stack > 2× avg remaining stack):**
- Raise frequency: +30% (steal aggressively — opponents are terrified)
- Open any top-35% hand from any position
- Re-raise short stacks liberally
- Target medium stacks over other big stacks

**If we have a medium stack:**
- Tighten dramatically: only open top-15% of hands
- Avoid confrontations with big stack
- Let short stack get eliminated before engaging
- Call all-ins only with top-10% of hands (apply 1.4× multiplier)

**If we have the short stack:**
- Find a spot to shove within 3 orbits
- Do not bleed out passively — blind-folding is the worst outcome
- Shove with top-40% of hands when not facing a raise
- Desperation shove any reasonable hand when < 3BB

**Big stack approximation** (opponent stacks not available):
```python
# Rough big stack detection:
avg_stack_approx = 1500 * 9 / max(active_players, 3)  # Very rough
is_big_stack = game_state['stack_size'] > avg_stack_approx * 1.8
is_short_stack = game_state['stack_size'] < avg_stack_approx * 0.5
```

This approximation is imprecise but sufficient for directional adjustments.

### In-Money Play Rules (ITM — 3 players)

Once 3 players remain:
- Release ICM pressure: play aggressively for 1st
- Target: maximize 1st-place finishes (50 pts) not just survival for 3rd (20 pts)
- The difference between finishing 1st vs 3rd = 30 pts = 1.5× the 3rd place prize

**3-handed strategy by stack role:**

| Stack role | Preflop | Postflop |
|-----------|---------|---------|
| Big stack | Open 60%+ from button; pressure medium stack | Bet strong, fold to strength from medium |
| Medium stack | Play standard TAG; avoid big stack without premium | Pot-control vs big stack; attack short stack |
| Short stack | Shove-or-fold; find spots before blinding out | All-in preflop focus |

### Heads-Up Rules

**Engine quirk:** Button posts BB (not SB). Non-button posts SB and acts first preflop.

| Stat | Target value |
|------|-------------|
| Opening range from non-button (SB acts first) | Top 55% of hands |
| Calling range from button (BB) facing raise | Top 40% of hands |
| 3-bet range | Top 15% |
| Pure chip-EV threshold | 100% — no ICM heads-up |

**Sizing heads-up:**
- Preflop: 2.5× BB
- Postflop: 50% pot (simplified — avoid overcomplicating)

---

## 12. Competition-Specific Adjustments

From simulation data (52 bots, 792 hands, sim_2.json):
- 50/52 bots never raise
- ~2% of all actions are raises
- CallBot (always-call) finishes around 40th-50th consistently

### Exploitable Tendencies of the Test Field

| Tendency | Our adjustment |
|----------|---------------|
| Never raises preflop | Open wider — 3-bets will never come |
| Calls randomly without equity | Value bet thinner — we get paid with medium hands |
| Folds randomly without pressure | Steal blinds every orbit we're late (especially on bubble) |
| No 3-bet defense | Raise preflop liberally — never punished |
| Calls postflop without drawing equity | Bet every made hand for value, all streets |

**Against the test field (random bots), EHS threshold for value betting can be reduced by ~0.10:**
- Normally bet STRONG (≥0.65) — against random callers, bet MEDIUM (≥0.55)
- This captures more thin value against opponents who call randomly

### Real Student Submissions

The actual tournament will include student-built bots of unknown quality.
Adjust conservatively: do not rely on field passivity.

**Key adjustment:** Keep the bubble play tight regardless of field quality.
The ICM cliff at 4th place is structural — it does not depend on opponent quality.

---

## 13. Preflop Hand Classification Quick Reference

For implementation, every hand can be described by three values:
`(rank_hi, rank_lo, suited)` where `rank_hi >= rank_lo`.

### Priority Tiers (for any decision)

| Tier | Hands | Chen score |
|------|-------|-----------|
| Tier 1 — Premium | AA, KK, QQ, AKs, AKo | ≥ 10 |
| Tier 2 — Strong | JJ, TT, 99, AQs, AJs, AQo | 8.5–9.5 |
| Tier 3 — Playable | 88, 77, ATs, A9s, KQs, KJs, AJo, KQo | 7–8 |
| Tier 4 — Speculative | 66, 55, A2s–A8s, K9s–KTs, QJs, QTs, JTs, ATo | 5.5–6.5 |
| Tier 5 — Marginal | 44, 33, 22, T9s, 98s, 87s, 76s, 65s, KJo | 5–5.5 |
| Tier 6 — Fold | Everything else | < 5 |

### Stack-Mode Open Thresholds by Tier

| Stack mode | Minimum tier to open |
|-----------|---------------------|
| DEEP | Tier 5 (Chen ≥ 5, positionally adjusted) |
| MEDIUM | Tier 4 (Chen ≥ 5.5) |
| SHALLOW | Tier 3 (Chen ≥ 7) |
| PUSH_FOLD | Tier 2–3 depending on stack depth (see Section 7) |

### Tier Threshold Facing a Raise

| Stack mode | Minimum tier to continue |
|-----------|------------------------|
| DEEP | Tier 2 to call, Tier 1 to 3-bet |
| MEDIUM | Tier 1–2 to 3-bet/call, fold rest |
| SHALLOW | Tier 1 shove, Tier 2 shove, fold rest |
| PUSH_FOLD | Tier 1–2 call only (see calling range table) |

---

## 14. Implementation Checklist

Every item below must be implemented for the strategy to function correctly.

### Must-Have (v1 — before submission)

- [ ] `estimated_total_pot` accumulator (Engine_Interface Section 9a)
- [ ] Stack mode detection (4 modes by BB threshold)
- [ ] Preflop hand tier classification (Chen formula or lookup)
- [ ] Push-fold shove table (<15BB)
- [ ] Push-fold call table (facing shove)
- [ ] Basic postflop equity (Monte Carlo or rule-of-2-and-4)
- [ ] C-bet logic (was_preflop_aggressor flag + EHS threshold)
- [ ] Pot odds call/fold (req_eq calculation)
- [ ] Tournament stage detection (blind level proxy)
- [ ] ICM multiplier at bubble (1.4× call threshold)
- [ ] Safety guard: never fold for free (`call_amount == 0` → check)
- [ ] Safety guard: never use `('check', 0)` — use `('call', 0)`
- [ ] Safety guard: cap raise at stack_size
- [ ] try/except wrapper on entire `_decide()` method

### Nice-to-Have (v2 — if time allows)

- [ ] Draw detection and EHS bonus
- [ ] Board texture classification
- [ ] 3-bet/4-bet logic
- [ ] Big/short stack detection for bubble play
- [ ] Turn/river sizing differentiation
- [ ] Competition-specific aggression boost (reduce EHS threshold by 0.10)

### Cut If Time Is Short

- [ ] Multi-street bluffing logic (just check/fold with air)
- [ ] River bluff frequency control
- [ ] Opponent modeling (no action_history available anyway)
- [ ] Dynamic raise sizing vs uniform sizing
- [ ] SB-specific limp range

---

*Document version: 1.0*
*Next document: SPEC.md*

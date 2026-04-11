# Feature Landscape

**Domain:** Competitive MTT Poker Bot (IIT Poker Club Tournament)
**Researched:** 2026-04-10

## Table Stakes

Features the bot must have or it loses to even basic opponents. Missing any of these means the bot bleeds chips, times out, or crashes.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Safety wrapper (try/except)** | Engine force-folds on exception or timeout. One unhandled crash = lost hand. | Low | Wrap `_decide()`, fallback to check/fold. Non-negotiable first line of defense. |
| **Never fold for free** | Folding when `call_amount == 0` wastes a free lottery ticket. Even random bots check here. | Low | `if call_amount == 0: return ('call', 0)` |
| **Never use `('check', 0)`** | Engine doesn't recognize 'check' string; folds you when call_amount > 0. | Low | Always `('call', 0)` for checks. |
| **Cap raises at stack size** | Raising more than your stack is undefined behavior. Engine may handle it, but don't rely on it. | Low | `raise_amount = min(raise_amount, stack_size - call_amount)` |
| **Correct class structure** | Engine scans for Bot subclasses. A bare function scores zero across all 10 sims. | Low | `class MyBot(Bot)` with `from engine.player_interface import Bot` |
| **Picklable instance state** | Engine uses ProcessPoolExecutor. Non-picklable attrs = silent failure. | Low | Only basic Python types (int, float, dict, list, str). No lambdas, no file handles. |
| **Pot accumulator workaround** | `pot_size` only shows current-street bets. Without accumulator, all postflop pot odds are wrong. | Medium | Track `_street_pot_accumulator` across streets. Critical for any postflop math. |
| **Preflop hand classification** | Without hand ranking, the bot plays blind. Chen formula is fast and precomputable. | Medium | 169-entry lookup table built at module level (free of 500ms budget). |
| **Stack mode detection** | Strategy must change at 40/25/15 BB thresholds. Playing deep-stack poker at 8BB = rapid elimination. | Low | Four modes: DEEP/MEDIUM/SHALLOW/PUSH_FOLD from `stack_size / blinds['big']`. |
| **Push-fold shove table (<15BB)** | At sub-15BB stacks, open-raise/fold is the worst play in poker. Shove-or-fold is mathematically required. | Medium | Precomputed table indexed by stack depth and hand. This is where most hands are played (Level 4+). |
| **Push-fold call table** | Calling a shove requires tighter ranges than shoving (no fold equity). Getting this wrong = calling too wide and busting. | Medium | Separate table from shove ranges. The "calling gap" (shove 2x more hands than you call) is fundamental. |
| **Basic preflop opening ranges** | Without opening ranges, the bot either plays too many hands (bleeds postflop) or too few (blinds eat it alive). | Medium | ~20% open in deep, ~15% medium, reshove-only in shallow. Tighten by stack mode. |
| **Pot odds call/fold decisions** | Calling without pot odds = burning chips on losing draws. Folding with correct odds = leaving value on table. | Medium | `req_eq = call_amount / (estimated_total_pot + call_amount)`. Compare to EHS. |
| **Monte Carlo equity estimation** | Without equity estimation postflop, the bot guesses. MC with 200-500 iterations is the only viable approach given library restrictions. | High | 7-card hand evaluator required (treys is blocked). C(7,5)=21 combos per evaluation. Most complex single component. |
| **Tournament stage detection** | Playing bubble poker like early-game poker = busting 4th (0 points). ICM awareness is structural, not optional. | Low | Blind level proxy: EARLY/MIDDLE/LATE/BUBBLE/ITM/HEADS_UP. |
| **ICM multiplier at bubble** | The jump from 4th (0 pts) to 3rd (20 pts) is the largest equity cliff. Calling too light here = tournament-ending. | Low | 1.4x call threshold on all-in decisions at bubble. Simple multiplier on req_eq. |

## Differentiators

Features that separate a tournament winner from a bot that merely survives. Not required to avoid losing, but provide competitive edge against other student bots.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **C-bet logic with aggressor tracking** | Continuation betting is free money against passive fields. Bots that never c-bet leave enormous value on the table when they raised preflop. | Medium | Track `_was_preflop_aggressor`. Bet 33-66% pot on flop based on board texture. Against the test field (50 passive bots), c-bets fold out opponents >80% of the time. |
| **Board texture classification** | Sizing should vary by board structure. Betting small on dry boards and large on wet boards is +EV vs flat sizing. | Medium | DRY/SEMI_WET/WET/PAIRED classification. Affects c-bet frequency and sizing. |
| **Draw detection with EHS bonus** | Without draw awareness, flush draws and OESDs are treated as weak hands and folded. These have 30-55% equity and should be played aggressively. | Medium | Detect flush draws (4 to a suit), OESDs (4-card sequences), gutshots. Apply equity bonus to raw MC estimate. |
| **Bet sizing system by context** | Uniform sizing is readable. Context-dependent sizing (street, texture, value vs bluff) extracts more value and applies more pressure. | Medium | Preflop: 2.0-2.5x BB by stack mode. Postflop: 33-75% pot by street and texture. Stack commitment rule (>60% stack = shove). |
| **Preflop situational strategy** | Distinguishing RFI, facing open, facing 3-bet, BB option, and SB complete creates correct ranges for each spot. Without this, the bot uses one range for all situations. | Medium | Position inference from `call_amount` relative to blinds. Different hand requirements for each situation. |
| **3-bet/4-bet logic** | Against student bots that do raise, re-raising with premiums builds pots when ahead. Flat-calling AA preflop against a raise is a missed opportunity. | Medium | 3-bet QQ+/AKs facing open. 4-bet shove AA/KK facing 3-bet. Simple tier-based logic. |
| **Big/short stack bubble detection** | On the bubble, big stacks should bully medium stacks, and short stacks should find shove spots. Without stack-relative awareness, the bot plays one-size-fits-all bubble poker. | Medium | Approximate average stack from `1500 * 9 / active_players`. Classify self as big/medium/short. Adjust aggression accordingly. |
| **Heads-up range widening** | Heads-up play requires opening 55%+ of hands and maximum aggression. A bot playing 9-handed ranges heads-up folds itself to death. | Low | Widen all ranges when `active_players == 2`. Account for engine quirk (button posts BB). |
| **Exploit adjustments for weak fields** | The test field (and likely many student bots) never raises and calls/folds randomly. Value betting thinner (+0.10 EHS reduction) and stealing every orbit prints chips. | Low | Reduce EHS threshold for value betting from 0.65 to 0.55. Open wider when 3-bets are absent. Steal blinds liberally. |
| **Turn/river barreling logic** | Multi-street aggression compounds fold equity. Betting flop then checking turn signals weakness. Continuing to bet with strong hands and select bluffs on turn/river wins bigger pots. | Medium | Second barrel with STRONG+ on turn (66% pot). River value bet with STRONG+ (75% pot). River bluff only with specific conditions (scare card, single opponent, was aggressor). |
| **SPR-based commitment decisions** | Stack-to-pot ratio determines whether to get all-in. Without SPR awareness, the bot makes awkward bets that leave it pot-committed but not all-in. | Low | `SPR = stack_size / estimated_total_pot`. When SPR < 1.5 and betting, just shove. When SPR < 2 and facing a bet with STRONG+, shove. |
| **In-money aggression switch** | Once in top 3, the scoring math changes: 1st (50 pts) is 2.5x 3rd (20 pts). Survival mode ITM is a massive leak. | Low | When `active_players <= 3`, release ICM pressure. Open wider, bet more aggressively, fight for 1st. ICM multiplier drops to 1.0-1.1. |

## Anti-Features

Features to explicitly NOT build. Either blocked by constraints, not worth the complexity, or actively harmful.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Opponent modeling / tracking** | `action_history` is absent from game_state. No way to observe opponent actions. Even if available, building a model per-opponent within 500ms across 52 bots is infeasible. | Use population-level assumptions: field is passive, calls randomly, never 3-bets. Adjust exploitatively based on field composition, not individual opponents. |
| **Machine learning / neural networks** | sklearn, scipy, torch are blocked by AST import scanner. numpy is allowed but training a model at runtime within 500ms is impossible. | Use precomputed lookup tables (Chen formula, push-fold charts). Mathematical heuristics outperform ML in constrained environments. |
| **GTO solver / CFR training** | Counterfactual Regret Minimization requires millions of iterations and significant compute. Cannot run at decision time. Cannot pre-train without blocked libraries. | Use simplified GTO-inspired ranges (precomputed opening ranges, push-fold tables) rather than solved equilibria. Against a weak field, exploitative > GTO anyway. |
| **Multi-file architecture** | Engine requires single .py file in `players/` directory. Multiple files = import errors = zero score. | Everything in one file. Module-level helpers, precomputed tables, single Bot class. |
| **Complex bluffing sequences** | Multi-street bluff lines (check-raise flop, barrel turn, triple barrel river) require opponent reads and hand reading. Without action_history, we can't construct bluff narratives. | Simple bluff rules: c-bet on dry boards as aggressor, river bluff with specific triggers (scare card + single opponent + was aggressor). One-and-done bluffs, not multi-street. |
| **Dynamic raise sizing based on reads** | No opponent data available. Varying sizes based on perceived tendencies is guesswork without history. | Fixed sizing formulas by context (stack mode, street, board texture). Consistent sizing prevents giving away information and is simpler to implement correctly. |
| **Limping preflop** | Limping is dominated strategy in tournament poker. It invites multiway pots where postflop edges shrink, and surrenders initiative. The only exception is SB completing in deep stacks, which the strategy already handles. | Raise or fold preflop (except SB complete in deep stacks, BB check). Never open-limp. |
| **Slow-playing monsters** | Without opponent reads, slow-playing risks giving free cards. The field calls too much anyway, so betting for value is always better than trapping. | Always bet monsters. Against a calling-station field, value betting is strictly superior to trapping. |
| **Time-based logic** | `time` module is blocked. Cannot measure elapsed time for iterative deepening or adaptive MC iterations. | Fixed iteration counts for MC simulation. Benchmark locally, set conservative caps (300 flop, 400 turn, 500 river). |
| **Position tracking from seat numbers** | `position` field is absent from game_state. Seat-based position inference would require tracking all players across hands, which is impossible without action_history. | Infer positional context from `call_amount` relative to blinds. Preflop: RFI vs facing raise vs BB option. Postflop: aggressor vs non-aggressor proxy. |

## Feature Dependencies

```
Safety Wrapper ──────────────────────────────── (no dependencies, build first)
    |
Correct Class Structure ─────────────────────── (no dependencies, build first)
    |
Card Decoder (rank/suit from treys ints) ────── (no dependencies, build first)
    |
    v
Preflop Hand Classification (Chen formula) ──── depends on: Card Decoder
    |
    v
Stack Mode Detection ────────────────────────── depends on: nothing (blinds math)
    |
    v
Tournament Stage Detection ──────────────────── depends on: nothing (blinds math)
    |
    +──> Preflop Opening Ranges ──────────────── depends on: Hand Classification, Stack Mode
    |       |
    |       +──> Preflop Situational Strategy ── depends on: Opening Ranges, Position Inference
    |       |
    |       +──> Push-Fold Shove Table ───────── depends on: Hand Classification, Stack Mode
    |       |
    |       +──> Push-Fold Call Table ────────── depends on: Hand Classification, Stack Mode
    |
    +──> Pot Accumulator ─────────────────────── depends on: nothing (state tracking)
    |       |
    |       v
    |   Pot Odds Calculation ─────────────────── depends on: Pot Accumulator
    |       |
    |       v
    |   7-Card Hand Evaluator ────────────────── depends on: Card Decoder
    |       |
    |       v
    |   Monte Carlo Equity ───────────────────── depends on: Hand Evaluator, Card Decoder
    |       |
    |       +──> EHS (Effective Hand Strength) ─ depends on: MC Equity, Draw Detection
    |       |
    |       +──> Postflop Decision Rules ─────── depends on: EHS, Pot Odds, Board Texture
    |       |       |
    |       |       +──> C-bet Logic ─────────── depends on: Aggressor Tracking, Board Texture, EHS
    |       |       |
    |       |       +──> Turn/River Barreling ── depends on: C-bet Logic, EHS
    |       |
    |       +──> Draw Detection ──────────────── depends on: Card Decoder
    |       |
    |       +──> Board Texture Classification ── depends on: Card Decoder
    |
    +──> ICM Multiplier ──────────────────────── depends on: Tournament Stage
    |
    +──> Big/Short Stack Detection ───────────── depends on: Stack Mode, Tournament Stage
    |
    +──> Bet Sizing System ───────────────────── depends on: Stack Mode, Board Texture, Pot Accumulator
    |
    +──> SPR Commitment Logic ────────────────── depends on: Pot Accumulator, Stack Mode
```

## MVP Recommendation

**Phase 1 -- Minimum Viable Bot (must ship first):**
1. Safety wrapper + correct class structure + card decoder
2. Preflop hand classification (Chen formula lookup)
3. Stack mode detection + push-fold tables (shove AND call)
4. Pot accumulator workaround
5. Basic preflop opening ranges by stack mode

**Rationale:** This bot survives. It plays correct push-fold poker (where most hands occur from Level 4+), opens reasonable ranges when deep, and never crashes. Against 50 TestBots and 1 CallBot, this alone should top-3 frequently.

**Phase 2 -- Postflop Competence:**
1. 7-card hand evaluator
2. Monte Carlo equity estimation
3. Pot odds call/fold decisions
4. C-bet logic with aggressor tracking
5. Board texture classification

**Rationale:** This bot wins postflop. Against student bots that have basic preflop play, postflop edge is the differentiator. MC equity + pot odds + c-betting creates a mathematically grounded postflop game.

**Phase 3 -- Tournament Edge:**
1. ICM multiplier at bubble
2. Draw detection with EHS bonus
3. Bet sizing system (context-dependent)
4. Big/short stack bubble detection
5. In-money aggression switch
6. Heads-up range widening
7. Exploit adjustments for weak fields

**Rationale:** This bot wins tournaments. ICM awareness at bubble prevents costly 4th-place busts. Draw detection and sizing polish extract maximum value. Exploit adjustments dominate the expected weak field.

**Defer indefinitely:**
- Opponent modeling (no data available)
- ML/neural approaches (blocked libraries)
- Complex bluffing (insufficient reads)
- Multi-file architecture (engine constraint)

## Sources

- [Upswing Poker: Push Fold Charts](https://upswingpoker.com/push-fold-tournament-strategy-charts/) -- push-fold strategy reference
- [GTO Wizard: ICM Solver](https://blog.gtowizard.com/revolutionizing-mtts-the-ultimate-icm-solver-upgrade/) -- ICM calculation approaches
- [GTO Wizard: Bubble Factor](https://blog.gtowizard.com/what-is-the-bubble-factor-in-poker-tournaments/) -- bubble factor and stack-relative ICM
- [BBZ Poker: Extreme ICM](https://bbzpoker.com/extreme-icm-bubble-strategy/) -- bubble strategy by stack size
- [Crown AI Poker: GTO vs Exploitative](https://crownaipoker.com/blog/gto-poker-bot-vs-exploitative-bot/) -- when to exploit vs play GTO
- [Upswing Poker: GTO vs Exploitative](https://upswingpoker.com/gto-vs-exploitative-play-game-theory-optimal-strategy/) -- hybrid approach consensus
- [My Poker Coaching: Push Fold Charts](https://www.mypokercoaching.com/push-fold-chart/) -- stack-depth-dependent push ranges
- [MIT Pokerbots](https://pokerbots.org/) -- student competition reference
- ENGINE_INTERFACE.md (project source) -- engine constraints and available data
- STRATEGY_REFERENCE.md (project source) -- pre-researched strategy framework

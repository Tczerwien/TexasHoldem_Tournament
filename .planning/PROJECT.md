# MTTBot — IIT Poker Club Tournament Bot

## What This Is

A competitive Texas Hold'em poker bot (HawkEyeBot) for the IIT Poker Club Multi-Table Tournament (MTT). The bot competes against all submitted student bots across 10 simulations, with points awarded to top-3 finishers (50/30/20). Built as a single 1,449-LOC Python file with 217 tests, the bot combines preflop hand evaluation, Monte Carlo postflop equity, and tournament-aware strategy adjustments to maximize aggregate points.

## Core Value

Win the tournament — maximize aggregate points across 10 simulations by combining a high top-3 rate (~65%+) with aggressive play when in the money to push for 1st place finishes.

## Current State

**v1.0 shipped** — 2026-04-12. Submission-ready bot with all 47 requirements validated.

- 1,449 LOC in `players/mtt_bot.py`
- 2,698 LOC across 6 test files (217 tests, all passing)
- ~90ms worst-case decision time (82% of 500ms budget unused)
- Preflop: Chen formula + push-fold tables + situational strategy
- Postflop: 7-card evaluator + MC equity (300-500 iter) + draw detection + c-bets + pot odds
- Tournament: stage detection, ICM bubble pressure, heads-up widening, field exploitation

## Requirements

### Validated

- [x] Bot class inheriting from `Bot` with correct import form — v1.0
- [x] Safety guards: try/except wrapper, never fold for free, never use `('check', 0)`, cap raises at stack — v1.0
- [x] Pot accumulator workaround for broken `pot_size` — v1.0
- [x] All instance state picklable (basic Python types only) — v1.0
- [x] Complete bot in single file `players/mtt_bot.py` — v1.0
- [x] Preflop hand classification via Chen formula with precomputed lookup table — v1.0
- [x] Stack mode detection (deep/medium/shallow/push-fold by BB thresholds) — v1.0
- [x] Preflop opening ranges by stack mode — v1.0
- [x] Push-fold shove/call tables (<15BB) — v1.0
- [x] Preflop situational strategy (RFI, facing open, facing 3-bet, BB option, SB complete) — v1.0
- [x] Module-level precomputation of all lookup tables (free of 500ms budget) — v1.0
- [x] 7-card hand evaluator with C(7,5)=21 combination evaluation — v1.0
- [x] Monte Carlo equity estimation (300/400/500 iterations by street) — v1.0
- [x] Draw detection (flush draw, OESD, gutshot, combo) — v1.0
- [x] Board texture classification (dry/semi-wet/wet/paired) — v1.0
- [x] C-bet logic with preflop aggressor tracking — v1.0
- [x] Pot odds call/fold decisions — v1.0
- [x] Bet sizing system (33-75% pot by street/texture/situation) — v1.0
- [x] Stack commitment rule (bet >= 60% stack -> shove) — v1.0
- [x] Tournament stage detection (early/middle/late/bubble/ITM/heads-up) — v1.0
- [x] ICM multiplier at bubble (1.4x call threshold for all-in decisions) — v1.0
- [x] Stack role classification (big/medium/short relative to average) — v1.0
- [x] Bubble play adjustments (big stack widens, medium tightens) — v1.0
- [x] ITM aggression switch (release ICM pressure, fight for 1st) — v1.0
- [x] Heads-up range widening (55%+ opening) — v1.0
- [x] Field exploitation (0.10 EHS threshold reduction for value bets) — v1.0

### Active

No active requirements. Next milestone will define new requirements.

### Out of Scope

- Opponent modeling — no action_history available in game_state
- Multi-street bluff sequences — complexity not justified for v1
- Dynamic raise sizing based on opponent tendencies — no data available
- Machine learning / neural network approaches — blocked libraries
- Multi-file architecture — single file submission required
- Time-based logic — `time` module blocked; use fixed iteration counts
- Limping preflop — dominated strategy in tournament poker
- Slow-playing monsters — against calling-station field, value betting is strictly superior

## Context

- **Tournament engine:** MTT-Pokerbot-Engine by Alex Addison, source available at `Docs/MTT-Pokerbot-Engine/`
- **Test field:** 50 TestBots (random call/fold), 1 CallBot (always call), 1 RandomBot (20/60/20 fold/call/raise). Real tournament will include unknown student submissions.
- **Engine quirks verified from source:**
  - `pot_size` only shows current-street bets (pot_manager.collect_bets() called only at showdown)
  - Button posts BB in heads-up (non-standard)
  - Turn/river draw wastes one card per street (benign)
  - `('check', 0)` is not recognized — folds you if call_amount > 0
  - `position` field advertised in docstring but NOT in actual game_state
- **Card encoding:** Treys integer format, decoded via bit operations (rank: `((card >> 8) & 0xF) + 2`, suit: `(card >> 12) & 0xF`)
- **Allowed imports:** `math`, `random`, `numpy`, `pandas`, `engine.player_interface` — AST-scanned, violations block the bot for all 10 sims

## Constraints

- **Deadline**: April 23, 2026
- **Runtime**: 500ms hard timeout per decision — forced fold on timeout
- **Libraries**: Only math, random, numpy, pandas, engine.player_interface
- **File format**: Single .py file in `players/` directory
- **Class structure**: Must inherit from `Bot`, use `from engine.player_interface import Bot`
- **State**: All instance attributes must be picklable (no lambdas, file handles, locks)
- **No time module**: Use fixed iteration counts for MC loops instead

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single Bot class + module-level helpers | Engine scans for Bot subclasses; multiple would register as separate players | ✓ Good — clean architecture, single entry point |
| Chen formula for preflop hand ranking | Fast, well-established, precomputable into 169-entry lookup table | ✓ Good — <1ms preflop decisions |
| Monte Carlo for postflop equity | Only viable approach within allowed libraries; iteration-capped for timing | ✓ Good — ~60-80ms, well within budget |
| Manual 7-card evaluator | Treys library blocked; must implement rank/suit evaluation from scratch | ✓ Good — tuple-based ranking works correctly |
| Balanced-aggressive tournament strategy | Math shows 65% top-3 rate at avg 1.6th finish = ~303 pts over 10 sims (best EV) | ✓ Good — implemented across all stages |
| Pot accumulator workaround | pot_size bug is confirmed from source; must track cross-street pot manually | ✓ Good — accurate pot tracking |
| Field exploitation (0.10 EHS reduction) | Test field is weak (random/call bots); thinner value bets extract more chips | ✓ Good — applied globally via exploit_adj |
| ICM 1.4x bubble multiplier | Survival into money is worth more than marginal chip gain at bubble | ✓ Good — significant calls require 40% more equity |

---
*Last updated: 2026-04-12 after v1.0 milestone*

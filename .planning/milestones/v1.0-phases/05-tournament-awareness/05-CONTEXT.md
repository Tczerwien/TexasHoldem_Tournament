# Phase 5: Tournament Awareness - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Tournament stage detection from blind level + active player count, ICM calling multiplier at bubble, stack-role-based adjustments (big/medium/short), in-the-money aggression switch, heads-up range widening with button-posts-BB quirk handling, and field exploitation adjustments. This is the final phase -- produces the submission-ready bot.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User deferred all implementation decisions. Guided by REQUIREMENTS.md TOURN-01 through TOURN-07:

- **D-01:** Tournament stage detection (TOURN-01) -- detect early/middle/late/bubble/ITM/heads-up from blind level and active_players. Early: blinds low + many players. Middle: blinds moderate. Late: blinds high. Bubble: 4 players left (top 3 get paid). ITM: 3 players left. Heads-up: 2 players left. Claude determines exact thresholds.
- **D-02:** ICM calling multiplier at bubble (TOURN-02) -- multiply required equity by 1.4x for all-in calls when at bubble. This makes the bot fold more marginal all-in spots to survive into the money.
- **D-03:** Stack role detection (TOURN-03) -- big/medium/short stack relative to average. Big >= 1.5x avg, short <= 0.5x avg, medium in between. Claude determines exact multipliers. Avg estimated from `total_starting_chips / active_players`.
- **D-04:** Bubble play adjustments (TOURN-04) -- big stack opens wider to bully (widen Chen threshold by -1), medium stack tightens (narrow Chen threshold by +2), short stack pushes with standard push-fold ranges.
- **D-05:** ITM aggression switch (TOURN-05) -- when 3 players remain, release ICM pressure. Reset multiplier to 1.0, widen opening ranges, play aggressively to fight for 1st place (most points at 50pts).
- **D-06:** Heads-up range widening (TOURN-06) -- open 55%+ of hands (Chen >= ~3). Handle engine quirk: button posts BB in heads-up (non-standard). This means position inference changes when active_players == 2.
- **D-07:** Field exploitation (TOURN-07) -- reduce EHS value bet threshold by 0.10 against weak/passive fields. Since the test field is mostly random/call bots, this applies by default.
- **D-08:** Integration approach -- add `_get_tournament_stage()` and `_get_stack_role()` methods. Modify preflop `_preflop()` to check tournament stage and adjust thresholds. Modify postflop `_postflop()`/`_facing_bet()` to apply ICM multiplier and exploitation adjustments.
- **D-09:** All new methods as class methods on HawkEyeBot per Phase 1 D-12.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine interface
- `Docs/MTT-Pokerbot-Engine/engine/player_interface.py` -- game_state with active_players, blinds
- `Docs/MTT-Pokerbot-Engine/engine/table.py` -- Heads-up blind posting (line 55-56: button posts BB)
- `Docs/MTT-Pokerbot-Engine/engine/config.py` -- Tournament configuration

### Existing bot code
- `players/mtt_bot.py` -- Current HawkEyeBot with Phases 1-4

### Requirements
- `.planning/REQUIREMENTS.md` -- TOURN-01 through TOURN-07

### Prior phase context
- `.planning/phases/02-preflop-engine/02-CONTEXT.md` -- Preflop decision tree (D-12) designed for Phase 5 modification

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_preflop()` -- preflop decision tree, already structured by stack mode and situation
- `_postflop()`, `_facing_bet()` -- postflop decision methods with EHS thresholds
- `game_state["active_players"]` -- player count for stage detection
- `game_state["blinds"]` -- blind levels for stage/timing detection
- `_get_stack_mode()` -- stack depth classification (deep/medium/shallow/push-fold)

### Integration Points
- `_preflop()` -- add tournament stage checks, modify Chen thresholds
- `_facing_bet()` -- apply ICM multiplier to req_eq at bubble
- `_bet_or_check()` -- apply exploit adjustment to value bet threshold

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- user deferred all to Claude. This is the final phase producing the submission-ready bot for the IIT Poker Club tournament (deadline: April 23, 2026).

</specifics>

<deferred>
## Deferred Ideas

None -- this is the final v1 phase. All v2 items (PERF-01 through PERF-05, STRAT-01 through STRAT-04, EDGE-01 through EDGE-04) remain in REQUIREMENTS.md for post-submission optimization.

</deferred>

---

*Phase: 05-tournament-awareness*
*Context gathered: 2026-04-11*

# Phase 4: Postflop Decisions - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Postflop betting decisions using Phase 3's analysis engine. C-bet logic, pot odds call/fold, bet sizing by street/texture/situation, stack commitment rule, turn barreling, river value betting, and SPR-based commitment. This phase wires the analysis tools into actual betting actions.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User deferred all implementation decisions. Guided by REQUIREMENTS.md POST-06 through POST-13:

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine interface
- `Docs/MTT-Pokerbot-Engine/engine/player_interface.py` -- game_state dict
- `Docs/MTT-Pokerbot-Engine/engine/table.py` -- raise semantics (additive amount)

### Existing bot code
- `players/mtt_bot.py` -- Current HawkEyeBot with Phase 1-3 code

### Requirements
- `.planning/REQUIREMENTS.md` -- POST-06 through POST-13

### Prior phase context
- `.planning/phases/01-skeleton-and-safety/01-CONTEXT.md` -- File structure decisions
- `.planning/phases/03-postflop-analysis/03-CONTEXT.md` -- Analysis method signatures

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_ehs(hole, board)` -- returns float 0.0-1.0 (EHS value)
- `_mc_equity(hole, board)` -- returns float 0.0-1.0
- `_detect_draws(hole, board)` -- returns dict with bool flags
- `_classify_board(board)` -- returns "DRY"/"SEMI_WET"/"WET"/"PAIRED"
- `_was_preflop_aggressor` -- bool flag set during preflop
- `est_pot` from `_update_pot()` -- total pot estimate
- `_guard()` -- validates all actions

### Integration Points
- `_decide()` -- add postflop routing when `len(board_cards) > 0`
- Replace tight-passive fallback with `_postflop()` call

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- user deferred all to Claude.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 04-postflop-decisions*
*Context gathered: 2026-04-11*

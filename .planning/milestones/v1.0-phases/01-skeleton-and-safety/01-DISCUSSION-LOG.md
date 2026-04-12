# Phase 1: Skeleton and Safety - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 01-skeleton-and-safety
**Areas discussed:** Default play style, Bot identity, Pot tracking strategy, File structure

---

## Default Play Style

| Option | Description | Selected |
|--------|-------------|----------|
| Tight-passive | Call when call_amount < X% of stack, fold otherwise. Survives 10 sims by not bleeding chips recklessly. | ✓ |
| Always call | Like CallBot -- call everything, never fold, never raise. Simple but uncompetitive. | |
| Random weighted | Fold/call/raise at fixed probabilities. Unpredictable but inconsistent. | |

**User's choice:** Tight-passive
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| No raises | Phase 1 only calls or folds. Minimal skeleton. | |
| Raise premiums only | Raise with AA/KK/QQ to extract value from weak field. | ✓ |

**User's choice:** Raise premiums only
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| 10% of stack | Conservative, very passive. | |
| 15% of stack | Moderate balance of survival and participation. | ✓ |
| 20% of stack | Looser, stays in more pots. | |

**User's choice:** 15% of stack
**Notes:** None

---

## Bot Identity

| Option | Description | Selected |
|--------|-------------|----------|
| MTTBot | Matches project name. Simple. | |
| Custom name | Creative/memorable for leaderboard. | ✓ |

**User's choice:** Custom name -- brainstormed options together

| Option | Description | Selected |
|--------|-------------|----------|
| MiesTheNuts | Mies van der Rohe + strongest poker hand. IIT reference. | |
| ScarletShove | IIT Scarlet Hawks + aggressive all-in move. | |
| PierogiPush | Polish heritage + poker push. Fun and memorable. | |
| HawkEye | Scarlet Hawks + table reading. Clean and sharp. | ✓ |

**User's choice:** HawkEye
**Notes:** Thomas is Polish, teammate is Furquan, both CS students at IIT Chicago.

| Option | Description | Selected |
|--------|-------------|----------|
| HawkEyeBot | class HawkEyeBot(Bot), display name "HawkEye". | ✓ |
| HawkEye | class HawkEye(Bot), display name same as class. | |

**User's choice:** HawkEyeBot
**Notes:** None

---

## Pot Tracking Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Board cards empty | New hand = board_cards is empty. Simple, reliable. | ✓ |
| Hole cards changed | New hand = hole_cards differ from last seen. | |
| Stack changed unexpectedly | Detect wins/losses from stack deltas. More complex, fragile. | |

**User's choice:** Board cards empty
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Additive tracking | Track pot_size per street, add to running total on street transition. | ✓ |
| Infer from stack changes | Deduce pot from own stack changes + call_amounts. | |
| You decide | Claude picks approach. | |

**User's choice:** Additive tracking
**Notes:** None

---

## File Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Sections with headers | Comment banners grouping by concern. Module-level first, class last. | ✓ |
| Everything in the class | All logic as methods. Module level only has imports. | |
| You decide | Claude picks layout. | |

**User's choice:** Sections with headers
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Underscore prefix | self._pot_total, self._hand_num. Private-style. | ✓ |
| No prefix | self.pot_total, self.hand_num. Simpler but collision risk. | |
| You decide | Claude picks convention. | |

**User's choice:** Underscore prefix
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Methods on the class | self._guard(), self._detect_new_hand(). Encapsulated, direct state access. | ✓ |
| Module-level functions | Standalone functions, pass state as args. | |
| Mix: stateless at module, stateful as methods | Pure functions at module, state-dependent as methods. | |

**User's choice:** Methods on the class
**Notes:** None

---

## Claude's Discretion

- Exact premium hand detection logic
- Guard function internals
- Section ordering within comment banners
- Error message formatting in try/except fallback

## Deferred Ideas

None -- discussion stayed within phase scope

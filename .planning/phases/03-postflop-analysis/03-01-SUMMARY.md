---
phase: 03-postflop-analysis
plan: 01
subsystem: hand-evaluator
tags: [hand-eval, postflop, tdd, eval-5, eval-7]
dependency_graph:
  requires: [COMBO_INDICES, treys-card-encoding]
  provides: [_eval_5, _eval_7]
  affects: [mc-equity-plan-02, postflop-decisions-phase-4]
tech_stack:
  added: []
  patterns: [tuple-ranking-lower-is-better, manual-rank-suit-classification, combo-indices-enumeration]
key_files:
  created:
    - tests/test_postflop.py
  modified:
    - players/mtt_bot.py
decisions:
  - "D-01: Manual rank/suit evaluator using bit extraction, not prime product lookup"
  - "D-02: Tuple-based ranking (class_id, -tiebreakers) where lower = better"
  - "D-03: Exhaustive C(7,5) enumeration via COMBO_INDICES for 7-card eval"
metrics:
  duration: 3m
  completed: "2026-04-11T05:52:00Z"
  tasks_completed: 1
  tasks_total: 1
  tests_added: 24
  tests_total: 117
---

# Phase 03 Plan 01: Hand Evaluator Summary

Manual rank/suit 5-card evaluator with tuple-based ranking (lower=better) and 7-card evaluator enumerating all 21 C(7,5) combinations via COMBO_INDICES. Wheel straight (A-2-3-4-5) correctly handled as special case.

## What Was Built

### _eval_5 (5-card hand evaluator)
- Extracts ranks via `(c >> 8) & 0xF` and suits via `(c >> 12) & 0xF` from treys encoding
- Classifies hands into 9 categories: straight flush (0), four of a kind (1), full house (2), flush (3), straight (4), three of a kind (5), two pair (6), one pair (7), high card (8)
- Returns tuple `(class_id, -tiebreaker1, ...)` where lower tuple = better hand
- Handles wheel straight (A-2-3-4-5) as straight with high=3, not high card
- Frequency-based grouping for pair/trips/quads detection
- Kicker comparison within same hand category via negated rank values

### _eval_7 (7-card hand evaluator)
- Iterates all 21 COMBO_INDICES entries to extract every possible 5-card subset
- Calls `_eval_5` on each subset, tracks best (lowest) result
- Uses sentinel `(9,)` which is worse than any real hand tuple

### Test Suite (tests/test_postflop.py)
- 21 TestEvaluator tests: 9 category classification, 2 wheel tests, 8 ordering tests, 2 tiebreaker tests
- 3 TestEval7 tests: flush finding, combo optimality, straight finding in 7 cards
- Uses mock engine pattern consistent with existing test files
- String-based `make_card("Ah")` helper for readable test construction

## Task Execution

| Task | Name | Type | Commit | Files |
|------|------|------|--------|-------|
| 1 (RED) | Failing tests for _eval_5 and _eval_7 | test | 87359cc | tests/test_postflop.py |
| 1 (GREEN) | Implement _eval_5 and _eval_7 | feat | 36b0dbd | players/mtt_bot.py |

## Verification Results

- `python -m pytest tests/test_postflop.py -x -q`: 24 passed
- `python -m pytest tests/ -x -q`: 117 passed (no regressions)
- All 9 hand categories correctly classified
- Wheel straight correctly detected
- Hand ordering: SF < quads < FH < flush < straight < trips < 2pair < pair < high card
- Kicker comparison works within same category
- _eval_7 finds best hand among 21 combinations

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- FOUND: tests/test_postflop.py
- FOUND: players/mtt_bot.py
- FOUND: .planning/phases/03-postflop-analysis/03-01-SUMMARY.md
- FOUND: 87359cc (RED commit)
- FOUND: 36b0dbd (GREEN commit)

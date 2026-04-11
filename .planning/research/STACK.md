# Technology Stack

**Project:** MTTBot -- IIT Poker Club Tournament Bot
**Researched:** 2026-04-10
**Constraint:** Single .py file, only `math`, `random`, `numpy`, `pandas`, `engine.player_interface` allowed

---

## Recommended Stack

### Core Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python 3.x | Engine-provided | Runtime | No choice -- engine dictates |
| `math` | stdlib | `log2`, `ceil`, `floor`, constants | Lightweight math ops, always available |
| `random` | stdlib | MC sampling (`random.sample`, `random.random`) | Faster than numpy for small-sample-from-large-population draws (50x faster per research). Critical for MC inner loop. |
| `numpy` | Engine-provided | Precomputation of lookup tables at module level | Vectorized table construction is fast; but numpy overhead per-call hurts for small operations in the hot path |

### Not Using

| Technology | Reason |
|------------|--------|
| `pandas` | Allowed but provides zero value for this use case. DataFrames add overhead with no benefit for numeric lookups or card manipulation. |
| `numpy` in hot path | For the MC inner loop (300-500 iterations of dealing ~5 cards from ~45), `random.sample()` is ~50x faster than `np.random.choice(replace=False)` for small samples from small populations. numpy's overhead dominates at these scales. Use numpy only at module-level precomputation time. |
| `itertools` | BLOCKED. Must implement `combinations(7,5)` manually -- only 21 combos, hardcode the indices. |
| `collections` | BLOCKED. Use plain dicts and lists instead. |
| `time` | BLOCKED. Use fixed iteration caps for MC loops. |

---

## Algorithm Stack -- Detailed

### 1. Hand Evaluator: Cactus Kev / Treys-Style Prime Product Lookup

**Algorithm:** Reimplementation of the treys/deuces evaluator using prime number products and precomputed lookup tables.

**Why this approach:**
- The treys library uses this exact algorithm and achieves ~250k evals/sec in pure Python
- Only requires dict lookups and integer multiplication -- no external dependencies
- Lookup tables are deterministic and can be built at module-level import time (free of 500ms budget)
- The engine already encodes cards in treys integer format, so bit extraction is trivial

**How it works:**

1. **Card encoding (already done by engine):** Each card is a 32-bit integer. Rank extracted via `(card >> 8) & 0xF`, suit via `(card >> 12) & 0xF`. Each card also embeds a prime number in its lowest bits.

2. **Prime product:** Each rank maps to a prime: `{2:2, 3:3, 4:5, 5:7, 6:11, 7:13, 8:17, 9:19, T:23, J:29, Q:31, K:37, A:41}`. The product of 5 primes uniquely identifies a hand's rank combination.

3. **Two lookup tables (built at module level):**
   - `FLUSH_LOOKUP[prime_product] -> rank` (1287 entries for flush hands)
   - `UNSUITED_LOOKUP[prime_product] -> rank` (4888 entries for non-flush hands)
   - Total: ~6175 dict entries, negligible memory (~100KB)

4. **5-card evaluation (O(1) per hand):**
   ```
   def evaluate_5(cards):
       # Check flush: AND all suit bits
       if (c1 & c2 & c3 & c4 & c5) & 0xF000:
           prime_product = prime(c1) * prime(c2) * ... * prime(c5)
           return FLUSH_LOOKUP[prime_product]
       else:
           prime_product = prime(c1) * prime(c2) * ... * prime(c5)
           return UNSUITED_LOOKUP[prime_product]
   ```

5. **7-card evaluation (21 x O(1) = O(21)):**
   - Generate all C(7,5) = 21 five-card subsets
   - Evaluate each, return minimum rank (best hand)
   - Without itertools: hardcode 21 index tuples as a constant list

**Complexity:** O(1) per 5-card eval, O(21) per 7-card eval. At 300 MC iterations with 2 evaluations each (hero + villain): 300 * 2 * 21 = 12,600 dict lookups per decision. At ~250k lookups/sec in pure Python, this takes ~50ms.

**Confidence:** HIGH -- this is the exact algorithm treys uses, and the engine already provides cards in treys encoding format.

**Alternative considered:** Manual rank/suit classification (check for flush, straight, pairs, etc. using conditionals). This is 5-10x slower because of Python branching overhead vs. a single dict lookup. The lookup table approach is strictly superior.

**Precomputation cost:** Building the two lookup tables takes ~10ms at import time. Trivial.

---

### 2. 7-Card Combination Generation: Hardcoded Index Tuples

**Why:** `itertools.combinations` is blocked. C(7,5) = 21 is small enough to enumerate statically.

**Implementation:**
```python
# Module-level constant -- all 21 ways to choose 5 from 7
COMBO_INDICES = [
    (0,1,2,3,4), (0,1,2,3,5), (0,1,2,3,6), (0,1,2,4,5),
    (0,1,2,4,6), (0,1,2,5,6), (0,1,3,4,5), (0,1,3,4,6),
    (0,1,3,5,6), (0,1,4,5,6), (0,2,3,4,5), (0,2,3,4,6),
    (0,2,3,5,6), (0,2,4,5,6), (0,3,4,5,6), (1,2,3,4,5),
    (1,2,3,4,6), (1,2,3,5,6), (1,2,4,5,6), (1,3,4,5,6),
    (2,3,4,5,6)
]
```

**Complexity:** O(1) -- it's a constant. No generation overhead.

**Confidence:** HIGH -- trivial enumeration.

---

### 3. Monte Carlo Equity Estimation: `random.sample` Inner Loop

**Why Monte Carlo:** With blocked libraries, there is no way to do exact equity calculation (which would need enumeration of all opponent hand combos). MC sampling with fixed iteration caps is the only viable approach.

**Why `random.sample` over numpy:**
- Population: ~45 remaining cards (52 - 2 hole - 3/4/5 board)
- Sample size: 2 (opponent hole) + 0/1/2 (remaining board) = 2-4 cards
- At this scale, `random.sample(remaining_deck, k)` is ~50x faster than `np.random.choice(remaining, k, replace=False)` because numpy's overhead (array creation, type checking, shuffle algorithm) dominates
- `random.sample` uses an O(k) selection algorithm internally, drawing only `k` random numbers

**Iteration counts (from SPEC.md, benchmarked against 500ms budget):**
| Street | Unknown cards | Iterations | Why |
|--------|--------------|------------|-----|
| Flop (3 board) | 2 turn + 1 river + 2 villain = 5 | 300 | Most unknowns, slowest per-iter |
| Turn (4 board) | 1 river + 2 villain = 3 | 400 | Fewer unknowns, faster per-iter |
| River (5 board) | 2 villain = 2 | 500 | Fewest unknowns, fastest. Could enumerate C(45,2)=990 for exact equity but MC is fast enough |

**MC inner loop structure (optimized):**
```
def mc_equity(hole, board, n_opponents, iters):
    known = set(hole + board)
    remaining = [c for c in FULL_DECK if c not in known]
    cards_needed = (5 - len(board)) + 2 * n_opponents
    wins = 0
    ties = 0
    for _ in range(iters):
        drawn = random.sample(remaining, cards_needed)
        # Split: first cards complete the board, rest are opponent holes
        full_board = board + drawn[:5 - len(board)]
        opp_start = 5 - len(board)
        all_seven_hero = hole + full_board
        hero_rank = evaluate_7(all_seven_hero)
        best = True
        for i in range(n_opponents):
            opp_hole = drawn[opp_start + 2*i : opp_start + 2*i + 2]
            opp_rank = evaluate_7(opp_hole + full_board)
            if opp_rank < hero_rank:  # lower rank = better
                best = False
                break
            elif opp_rank == hero_rank:
                ties += 1  # simplified
        if best:
            wins += 1
    return (wins + ties * 0.5) / iters
```

**Performance budget:**
- Per iteration: `random.sample` (~2us) + 2 * `evaluate_7` (~100us each for 21 dict lookups) = ~202us
- 300 iterations on flop: ~60ms
- 400 iterations on turn: ~70ms (slightly fewer lookups per iter since board is longer but same 7-card eval)
- Total MC time: 60-80ms, well within 250ms allocation, leaving 200ms+ buffer

**Confidence:** HIGH -- `random.sample` performance is well-documented, treys-style evaluation speed is benchmarked.

**Optimization: Simplify to 1 opponent for MC.** Even with multiple active_players, simulating against 1 random opponent gives a good equity proxy and halves evaluation time. Multi-opponent MC is quadratically more expensive and not worth the accuracy gain for this bot.

---

### 4. Preflop: Chen Formula with Precomputed Lookup Table

**Why Chen formula:**
- Well-established, deterministic, no randomness needed
- Maps all 169 hand categories (13x13 grid of rank pairs, suited/unsuited) to a numeric score
- Precomputable into a 169-entry dict at module level
- Directly usable for range thresholds (e.g., "open with Chen >= 5.0")

**Algorithm:**
1. Base = highest card value: A=10, K=8, Q=7, J=6, T=5, 9=4.5, ..., 2=1
2. Pairs: score = max(5, base * 2)
3. Suited: +2
4. Gap penalty: 0-gap=0, 1-gap=-1, 2-gap=-2, 3-gap=-4, 4+-gap=-5
5. Straight bonus: if gap <= 1 and both ranks < Q: +1
6. Round to nearest 0.5

**Output range:** 1.0 (72o) to 20.0 (AA)

**Complexity:** O(1) lookup per hand (dict access)

**Confidence:** HIGH -- formula is published, well-known, trivially implementable.

---

### 5. Push-Fold Tables: Precomputed Dict Lookup

**Why:** Below 15BB, push-fold is the only correct strategy. Shove/fold ranges are well-established in poker theory and can be encoded as lookup tables mapping `(rank_hi, rank_lo, suited) -> max_stack_bb_to_shove`.

**Implementation:** Two dicts built at module level:
- `SHOVE_TABLE`: 169 entries, value = max BB depth to open-shove
- `CALL_TABLE`: 169 entries, value = max villain BB depth to call their shove

**Complexity:** O(1) lookup. No computation at decision time.

**Confidence:** HIGH -- ranges from SPEC.md are already specified.

---

### 6. Deck Construction: Treys-Compatible Integer Encoding

**Why build our own deck:** The engine provides hole/board cards in treys integer format, but we need a full 52-card deck for MC sampling (to exclude known cards and deal random remainders).

**Implementation:**
```python
PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
SUITS = [1, 2, 4, 8]  # spades, hearts, diamonds, clubs
FULL_DECK = []
for rank_int in range(13):  # 0=2, 12=A
    for suit_int in SUITS:
        card = (1 << (rank_int + 16)) | (suit_int << 12) | (rank_int << 8) | PRIMES[rank_int]
        FULL_DECK.append(card)
```

**Verification:** `get_rank(FULL_DECK[0])` must return 2, `len(FULL_DECK)` must be 52.

**Confidence:** HIGH -- formula verified against engine source and tested card encodings.

---

### 7. Lookup Table Construction: Build at Module Level

All expensive computation happens once at import time, before the 500ms clock starts:

| Table | Entries | Build Time | Build Method |
|-------|---------|------------|--------------|
| `FULL_DECK` | 52 ints | <1ms | Loop over 13 ranks x 4 suits |
| `CHEN_TABLE` | 169 entries | <1ms | Chen formula over 169 hand categories |
| `SHOVE_TABLE` | 169 entries | <1ms | Hardcoded thresholds from strategy reference |
| `CALL_TABLE` | 169 entries | <1ms | Hardcoded thresholds from strategy reference |
| `FLUSH_LOOKUP` | ~1287 entries | ~5ms | Enumerate all flush hand prime products |
| `UNSUITED_LOOKUP` | ~4888 entries | ~5ms | Enumerate all non-flush hand prime products |
| `COMBO_INDICES` | 21 tuples | 0ms | Hardcoded constant |

**Total precomputation:** <15ms at import. Negligible.

**numpy role in precomputation:** numpy can accelerate the lookup table construction if needed (e.g., vectorized prime product computation), but at these sizes plain Python loops are fast enough. numpy is available as a safety net but unlikely to be needed.

---

## Performance Budget Analysis

### 500ms Decision Budget Breakdown

| Phase | Time | Method |
|-------|------|--------|
| Parse game_state | <1ms | Dict access |
| Stack/stage detection | <1ms | Arithmetic comparisons |
| Preflop (table lookup) | <1ms | Dict lookup for Chen/shove/call tables |
| Postflop MC equity | 60-80ms | 300-500 iterations of sample + evaluate |
| Draw detection | <2ms | Suit/rank counting on 5-7 cards |
| Board texture classification | <1ms | Rank/suit analysis |
| Decision logic | <2ms | Threshold comparisons |
| Pot accumulator update | <1ms | Simple arithmetic |
| Safety guards | <1ms | Bounds checking |
| **Total worst case** | **~90ms** | |
| **Safety buffer** | **~410ms** | 82% of budget unused |

**Key insight:** The 500ms budget is generous. Even with a pure Python evaluator, we have massive headroom. The bot will never timeout unless there is a bug (infinite loop, etc.).

---

## Critical Implementation Details

### Prime Extraction from Treys Cards

The treys integer format embeds a prime number in the lowest bits. To get the prime for hand evaluation:

```python
def card_prime(card_int):
    return card_int & 0x3F  # lowest 6 bits contain the prime
```

This is faster than looking up rank and then mapping to prime -- the prime is already in the card integer.

### Flush Detection Optimization

Instead of extracting suits and comparing, use bitwise AND on the suit bits:

```python
def is_flush(c1, c2, c3, c4, c5):
    return (c1 & c2 & c3 & c4 & c5 & 0xF000) != 0
```

If all 5 cards share a suit, the AND of their suit bits will be non-zero. Single CPU instruction, no branching.

### Set Operations for MC Deck Filtering

```python
known = set(hole_cards + board_cards)  # O(n) construction, n <= 7
remaining = [c for c in FULL_DECK if c not in known]  # O(52) with O(1) set lookup
```

Building `remaining` each MC call is ~5us. Acceptable since it happens once per decision, not per iteration.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Hand evaluator | Prime product lookup (treys-style) | Manual conditional classification (flush/straight/pair checks) | 5-10x slower due to Python branching overhead. Lookup tables are O(1) with no conditionals. |
| MC sampling | `random.sample()` | `numpy.random.Generator.choice(replace=False)` | numpy has array creation overhead that dominates at small sample sizes (2-5 cards from 45). random.sample is ~50x faster here. |
| MC iterations | Fixed caps (300/400/500) | Time-based adaptive (`time` module) | `time` module is BLOCKED. Fixed caps are predictable and benchmarkable. |
| Preflop evaluation | Chen formula lookup | Monte Carlo preflop equity | MC on preflop is wasteful -- 2 cards vs unknown is too noisy at 300 iters. Chen gives deterministic, precomputed scores that correlate well with actual equity. |
| River equity | MC 500 iterations | Exact enumeration C(45,2) = 990 | Exact enumeration is feasible on river (990 opponent combos x 21 eval each = 20,790 evals = ~80ms). Worth considering as an upgrade, but MC at 500 iters is sufficient and simpler. |
| Push-fold ranges | Precomputed tables | Real-time ICM calculation | ICM requires opponent stack info (unavailable) and is computationally expensive. Table-based ranges are proven and instant. |
| numpy in hot path | Avoid | Use for batch evaluation | numpy's per-call overhead (~10us for array creation) nullifies vectorization gains when individual operations are simple dict lookups. Only worth it for batch sizes >1000. |

---

## What NOT to Do

| Anti-Pattern | Why Dangerous |
|--------------|---------------|
| Use numpy in the MC inner loop | Array creation overhead dominates. `random.sample` + dict lookup is faster for this scale. |
| Implement hand evaluation with if/elif chains | O(n) branching is 5-10x slower than O(1) dict lookup. The lookup tables are small and fast. |
| Use pandas for anything | Zero value-add. DataFrames are for tabular data analysis, not real-time card evaluation. |
| Try to enumerate all opponent hand combos on flop | C(45,2) * C(43,2) * C(41,1) = too many combos. MC sampling is the only viable approach preflop/flop. |
| Build lookup tables inside `__init__` | Tables are the same for every instance. Module-level = built once and shared. `__init__` runs once per simulation (10 times total) -- wasteful. |
| Store numpy arrays in instance state | Pickling numpy arrays may fail depending on engine's pickle protocol. Stick to plain Python types for all `self.*` attributes. |
| Use `np.random.choice` with `replace=False` | For sampling 2-5 items from a 45-item list, Python's `random.sample` is ~50x faster due to numpy's overhead. |

---

## Installation / Setup

```python
# No installation needed. All allowed modules are built-in or engine-provided.
# The complete bot is a single file: players/mtt_bot.py

from engine.player_interface import Bot
import math
import random
# import numpy as np  -- available but not needed in the hot path
```

---

## Sources

- Treys evaluator algorithm: [ihendley/treys on GitHub](https://github.com/ihendley/treys) -- HIGH confidence
- Cactus Kev's poker hand evaluator: [suffe.cool/poker/evaluator.html](http://suffe.cool/poker/evaluator.html) -- HIGH confidence
- numpy.random.choice performance: [numpy/numpy#2764](https://github.com/numpy/numpy/issues/2764) -- HIGH confidence (random.sample ~50x faster for small samples)
- numpy.random.Generator.choice docs: [NumPy v2.4 Manual](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.choice.html) -- HIGH confidence
- Chen formula: [thepokerbank.com](https://www.thepokerbank.com/strategy/basic/starting-hand-selection/chen-formula/) -- HIGH confidence
- PHEvaluator perfect hash approach: [HenryRLee/PokerHandEvaluator](https://github.com/HenryRLee/PokerHandEvaluator) -- MEDIUM confidence (reference only, not using this approach)
- Hand rank boundaries (7462 distinct hands): [treys lookup.py](https://github.com/ihendley/treys/blob/master/treys/lookup.py) -- HIGH confidence

from engine.player_interface import Bot
import math

# === CONSTANTS ===
_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
_SUITS = [1, 2, 4, 8]

# 21 index tuples for C(7,5) combinations (Phase 3 will use these)
COMBO_INDICES = [
    (0,1,2,3,4),(0,1,2,3,5),(0,1,2,3,6),(0,1,2,4,5),(0,1,2,4,6),
    (0,1,2,5,6),(0,1,3,4,5),(0,1,3,4,6),(0,1,3,5,6),(0,1,4,5,6),
    (0,2,3,4,5),(0,2,3,4,6),(0,2,3,5,6),(0,2,4,5,6),(0,3,4,5,6),
    (1,2,3,4,5),(1,2,3,4,6),(1,2,3,5,6),(1,2,4,5,6),(1,3,4,5,6),
    (2,3,4,5,6),
]

# === PRECOMPUTATION ===

# --- COMP-01: Full 52-card deck in treys integer encoding ---
FULL_DECK = []
for _r in range(13):
    for _s in _SUITS:
        FULL_DECK.append((1 << _r << 16) | (_s << 12) | (_r << 8) | _PRIMES[_r])


def _build_chen_table():
    """PRE-01, COMP-02: Build 169-entry Chen score lookup.

    Returns dict[(high_rank_int, low_rank_int, suited_bool)] -> int.
    rank_int: 0=2, 1=3, ..., 10=Q, 11=K, 12=A
    """
    # Rank values per Chen formula: A=10, K=8, Q=7, J=6, T=5, 9=4.5, ..., 2=1
    _RANK_VALUES = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 10]
    table = {}
    for r1 in range(13):
        for r2 in range(r1, 13):
            for suited in [False, True]:
                if r1 == r2 and suited:
                    continue  # pairs cannot be suited
                high_val = _RANK_VALUES[r2]
                low_val = _RANK_VALUES[r1]
                if r1 == r2:
                    # Pair: multiply highest by 2, minimum 5
                    score = max(high_val * 2, 5)
                else:
                    score = high_val  # start with highest card value
                    if suited:
                        score += 2
                    gap = r2 - r1 - 1
                    if gap == 1:
                        score -= 1
                    elif gap == 2:
                        score -= 2
                    elif gap == 3:
                        score -= 4
                    elif gap >= 4:
                        score -= 5
                    # Straight bonus: gap <= 1 and both below Queen (rank_int < 10)
                    if gap <= 1 and r1 < 10 and r2 < 10:
                        score += 1
                table[(r2, r1, suited)] = math.ceil(score)
    return table


CHEN_TABLE = _build_chen_table()


def _build_shove_table():
    """PRE-04, COMP-03: Build 169-entry push-fold shove table.

    Returns dict[(high_rank_int, low_rank_int, suited_bool)] -> int (max BB to shove).
    Based on Nash equilibrium ranges, tightened for multiway.
    """
    # Initialize all entries to 0
    table = {}
    for r1 in range(13):
        for r2 in range(r1, 13):
            for suited in [False, True]:
                if r1 == r2 and suited:
                    continue
                table[(r2, r1, suited)] = 0

    # --- Pairs (high, high, False) ---
    table[(12, 12, False)] = 15  # AA
    table[(11, 11, False)] = 15  # KK
    table[(10, 10, False)] = 15  # QQ
    table[(9, 9, False)] = 15    # JJ
    table[(8, 8, False)] = 15    # TT
    table[(7, 7, False)] = 14    # 99
    table[(6, 6, False)] = 13    # 88
    table[(5, 5, False)] = 12    # 77
    table[(4, 4, False)] = 11    # 66
    table[(3, 3, False)] = 10    # 55
    table[(2, 2, False)] = 9     # 44
    table[(1, 1, False)] = 8     # 33
    table[(0, 0, False)] = 7     # 22

    # --- Ace-x suited ---
    table[(12, 11, True)] = 15   # AKs
    table[(12, 10, True)] = 15   # AQs
    table[(12, 9, True)] = 14    # AJs
    table[(12, 8, True)] = 14    # ATs
    table[(12, 7, True)] = 13    # A9s
    table[(12, 6, True)] = 12    # A8s
    table[(12, 5, True)] = 12    # A7s
    table[(12, 4, True)] = 11    # A6s
    table[(12, 3, True)] = 11    # A5s
    table[(12, 2, True)] = 10    # A4s
    table[(12, 1, True)] = 10    # A3s
    table[(12, 0, True)] = 10    # A2s

    # --- Ace-x offsuit ---
    table[(12, 11, False)] = 15  # AKo
    table[(12, 10, False)] = 14  # AQo
    table[(12, 9, False)] = 13   # AJo
    table[(12, 8, False)] = 11   # ATo
    table[(12, 7, False)] = 9    # A9o
    table[(12, 6, False)] = 8    # A8o
    table[(12, 5, False)] = 7    # A7o
    table[(12, 4, False)] = 6    # A6o
    table[(12, 3, False)] = 6    # A5o
    table[(12, 2, False)] = 5    # A4o
    table[(12, 1, False)] = 5    # A3o
    table[(12, 0, False)] = 5    # A2o

    # --- King-x suited ---
    table[(11, 10, True)] = 14   # KQs
    table[(11, 9, True)] = 13    # KJs
    table[(11, 8, True)] = 12    # KTs
    table[(11, 7, True)] = 9     # K9s
    table[(11, 6, True)] = 8     # K8s
    table[(11, 5, True)] = 7     # K7s
    table[(11, 4, True)] = 6     # K6s
    table[(11, 3, True)] = 5     # K5s
    table[(11, 2, True)] = 5     # K4s
    table[(11, 1, True)] = 4     # K3s
    table[(11, 0, True)] = 4     # K2s

    # --- King-x offsuit ---
    table[(11, 10, False)] = 12  # KQo
    table[(11, 9, False)] = 10   # KJo
    table[(11, 8, False)] = 8    # KTo
    table[(11, 7, False)] = 5    # K9o
    table[(11, 6, False)] = 4    # K8o
    table[(11, 5, False)] = 3    # K7o
    table[(11, 4, False)] = 0    # K6o
    table[(11, 3, False)] = 0    # K5o
    table[(11, 2, False)] = 0    # K4o
    table[(11, 1, False)] = 0    # K3o
    table[(11, 0, False)] = 0    # K2o

    # --- Queen-x suited ---
    table[(10, 9, True)] = 12    # QJs
    table[(10, 8, True)] = 11    # QTs
    table[(10, 7, True)] = 8     # Q9s
    table[(10, 6, True)] = 7     # Q8s
    table[(10, 5, True)] = 5     # Q7s
    table[(10, 4, True)] = 4     # Q6s
    table[(10, 3, True)] = 4     # Q5s
    table[(10, 2, True)] = 3     # Q4s
    table[(10, 1, True)] = 3     # Q3s
    table[(10, 0, True)] = 3     # Q2s

    # --- Queen-x offsuit ---
    table[(10, 9, False)] = 9    # QJo
    table[(10, 8, False)] = 7    # QTo
    table[(10, 7, False)] = 4    # Q9o
    table[(10, 6, False)] = 3    # Q8o
    table[(10, 5, False)] = 0    # Q7o
    table[(10, 4, False)] = 0    # Q6o
    table[(10, 3, False)] = 0    # Q5o
    table[(10, 2, False)] = 0    # Q4o
    table[(10, 1, False)] = 0    # Q3o
    table[(10, 0, False)] = 0    # Q2o

    # --- Jack-x suited ---
    table[(9, 8, True)] = 11     # JTs
    table[(9, 7, True)] = 9      # J9s
    table[(9, 6, True)] = 6      # J8s
    table[(9, 5, True)] = 5      # J7s
    table[(9, 4, True)] = 4      # J6s
    table[(9, 3, True)] = 0      # J5s
    table[(9, 2, True)] = 0      # J4s
    table[(9, 1, True)] = 0      # J3s
    table[(9, 0, True)] = 0      # J2s

    # --- Jack-x offsuit ---
    table[(9, 8, False)] = 8     # JTo
    table[(9, 7, False)] = 5     # J9o
    table[(9, 6, False)] = 3     # J8o
    table[(9, 5, False)] = 0     # J7o
    table[(9, 4, False)] = 0     # J6o
    table[(9, 3, False)] = 0     # J5o
    table[(9, 2, False)] = 0     # J4o
    table[(9, 1, False)] = 0     # J3o
    table[(9, 0, False)] = 0     # J2o

    # --- Ten-x suited ---
    table[(8, 7, True)] = 9      # T9s
    table[(8, 6, True)] = 7      # T8s
    table[(8, 5, True)] = 4      # T7s
    table[(8, 4, True)] = 0      # T6s
    table[(8, 3, True)] = 0      # T5s
    table[(8, 2, True)] = 0      # T4s
    table[(8, 1, True)] = 0      # T3s
    table[(8, 0, True)] = 0      # T2s

    # --- Ten-x offsuit ---
    table[(8, 7, False)] = 6     # T9o
    table[(8, 6, False)] = 3     # T8o
    table[(8, 5, False)] = 0     # T7o
    table[(8, 4, False)] = 0     # T6o
    table[(8, 3, False)] = 0     # T5o
    table[(8, 2, False)] = 0     # T4o
    table[(8, 1, False)] = 0     # T3o
    table[(8, 0, False)] = 0     # T2o

    # --- 9-x suited ---
    table[(7, 6, True)] = 8      # 98s
    table[(7, 5, True)] = 5      # 97s
    table[(7, 4, True)] = 0      # 96s
    table[(7, 3, True)] = 0      # 95s
    table[(7, 2, True)] = 0      # 94s
    table[(7, 1, True)] = 0      # 93s
    table[(7, 0, True)] = 0      # 92s

    # --- 9-x offsuit ---
    table[(7, 6, False)] = 4     # 98o
    table[(7, 5, False)] = 0     # 97o
    table[(7, 4, False)] = 0     # 96o
    table[(7, 3, False)] = 0     # 95o
    table[(7, 2, False)] = 0     # 94o
    table[(7, 1, False)] = 0     # 93o
    table[(7, 0, False)] = 0     # 92o

    # --- 8-x suited ---
    table[(6, 5, True)] = 7      # 87s
    table[(6, 4, True)] = 4      # 86s
    table[(6, 3, True)] = 0      # 85s
    table[(6, 2, True)] = 0      # 84s
    table[(6, 1, True)] = 0      # 83s
    table[(6, 0, True)] = 0      # 82s

    # --- 8-x offsuit ---
    table[(6, 5, False)] = 3     # 87o
    table[(6, 4, False)] = 0     # 86o
    table[(6, 3, False)] = 0     # 85o
    table[(6, 2, False)] = 0     # 84o
    table[(6, 1, False)] = 0     # 83o
    table[(6, 0, False)] = 0     # 82o

    # --- 7-x suited ---
    table[(5, 4, True)] = 6      # 76s
    table[(5, 3, True)] = 3      # 75s
    table[(5, 2, True)] = 0      # 74s
    table[(5, 1, True)] = 0      # 73s
    table[(5, 0, True)] = 0      # 72s

    # --- 7-x offsuit ---
    table[(5, 4, False)] = 3     # 76o
    table[(5, 3, False)] = 0     # 75o
    table[(5, 2, False)] = 0     # 74o
    table[(5, 1, False)] = 0     # 73o
    table[(5, 0, False)] = 0     # 72o

    # --- 6-x suited ---
    table[(4, 3, True)] = 5      # 65s
    table[(4, 2, True)] = 3      # 64s
    table[(4, 1, True)] = 0      # 63s
    table[(4, 0, True)] = 0      # 62s

    # --- 6-x offsuit ---
    table[(4, 3, False)] = 0     # 65o
    table[(4, 2, False)] = 0     # 64o
    table[(4, 1, False)] = 0     # 63o
    table[(4, 0, False)] = 0     # 62o

    # --- 5-x suited ---
    table[(3, 2, True)] = 5      # 54s
    table[(3, 1, True)] = 0      # 53s
    table[(3, 0, True)] = 0      # 52s

    # --- 5-x offsuit ---
    table[(3, 2, False)] = 0     # 54o
    table[(3, 1, False)] = 0     # 53o
    table[(3, 0, False)] = 0     # 52o

    # --- 4-x suited ---
    table[(2, 1, True)] = 3      # 43s
    table[(2, 0, True)] = 0      # 42s

    # --- 4-x offsuit ---
    table[(2, 1, False)] = 0     # 43o
    table[(2, 0, False)] = 0     # 42o

    # --- 3-x suited ---
    table[(1, 0, True)] = 0      # 32s

    # --- 3-x offsuit ---
    table[(1, 0, False)] = 0     # 32o

    return table


SHOVE_TABLE = _build_shove_table()


def _build_call_table():
    """PRE-05, COMP-04: Build 169-entry push-fold call table.

    Returns dict[(high_rank_int, low_rank_int, suited_bool)] -> int (max villain BB to call).
    Tighter than shove ranges. Based on Nash equilibrium calling ranges.
    """
    # Initialize all entries to 0
    table = {}
    for r1 in range(13):
        for r2 in range(r1, 13):
            for suited in [False, True]:
                if r1 == r2 and suited:
                    continue
                table[(r2, r1, suited)] = 0

    # --- Pairs ---
    table[(12, 12, False)] = 15  # AA
    table[(11, 11, False)] = 15  # KK
    table[(10, 10, False)] = 15  # QQ
    table[(9, 9, False)] = 14    # JJ
    table[(8, 8, False)] = 13    # TT
    table[(7, 7, False)] = 11    # 99
    table[(6, 6, False)] = 10    # 88
    table[(5, 5, False)] = 9     # 77
    table[(4, 4, False)] = 8     # 66
    table[(3, 3, False)] = 7     # 55
    table[(2, 2, False)] = 5     # 44
    table[(1, 1, False)] = 4     # 33
    table[(0, 0, False)] = 3     # 22

    # --- Ace-x suited ---
    table[(12, 11, True)] = 15   # AKs
    table[(12, 10, True)] = 14   # AQs
    table[(12, 9, True)] = 12    # AJs
    table[(12, 8, True)] = 11    # ATs
    table[(12, 7, True)] = 9     # A9s
    table[(12, 6, True)] = 8     # A8s
    table[(12, 5, True)] = 7     # A7s
    table[(12, 4, True)] = 6     # A6s
    table[(12, 3, True)] = 6     # A5s
    table[(12, 2, True)] = 5     # A4s
    table[(12, 1, True)] = 5     # A3s
    table[(12, 0, True)] = 4     # A2s

    # --- Ace-x offsuit ---
    table[(12, 11, False)] = 14  # AKo
    table[(12, 10, False)] = 12  # AQo
    table[(12, 9, False)] = 10   # AJo
    table[(12, 8, False)] = 8    # ATo
    table[(12, 7, False)] = 6    # A9o
    table[(12, 6, False)] = 5    # A8o
    table[(12, 5, False)] = 4    # A7o
    table[(12, 4, False)] = 3    # A6o
    table[(12, 3, False)] = 3    # A5o
    table[(12, 2, False)] = 0    # A4o
    table[(12, 1, False)] = 0    # A3o
    table[(12, 0, False)] = 0    # A2o

    # --- King-x suited ---
    table[(11, 10, True)] = 11   # KQs
    table[(11, 9, True)] = 9     # KJs
    table[(11, 8, True)] = 7     # KTs
    table[(11, 7, True)] = 5     # K9s
    table[(11, 6, True)] = 4     # K8s
    table[(11, 5, True)] = 3     # K7s
    table[(11, 4, True)] = 0     # K6s
    table[(11, 3, True)] = 0     # K5s
    table[(11, 2, True)] = 0     # K4s
    table[(11, 1, True)] = 0     # K3s
    table[(11, 0, True)] = 0     # K2s

    # --- King-x offsuit ---
    table[(11, 10, False)] = 9   # KQo
    table[(11, 9, False)] = 6    # KJo
    table[(11, 8, False)] = 4    # KTo
    table[(11, 7, False)] = 3    # K9o
    table[(11, 6, False)] = 0    # K8o
    table[(11, 5, False)] = 0    # K7o
    table[(11, 4, False)] = 0    # K6o
    table[(11, 3, False)] = 0    # K5o
    table[(11, 2, False)] = 0    # K4o
    table[(11, 1, False)] = 0    # K3o
    table[(11, 0, False)] = 0    # K2o

    # --- Queen-x suited ---
    table[(10, 9, True)] = 5     # QJs
    table[(10, 8, True)] = 4     # QTs
    table[(10, 7, True)] = 3     # Q9s
    table[(10, 6, True)] = 0     # Q8s
    table[(10, 5, True)] = 0     # Q7s
    table[(10, 4, True)] = 0     # Q6s
    table[(10, 3, True)] = 0     # Q5s
    table[(10, 2, True)] = 0     # Q4s
    table[(10, 1, True)] = 0     # Q3s
    table[(10, 0, True)] = 0     # Q2s

    # --- Queen-x offsuit ---
    table[(10, 9, False)] = 3    # QJo
    table[(10, 8, False)] = 0    # QTo
    table[(10, 7, False)] = 0    # Q9o
    table[(10, 6, False)] = 0    # Q8o
    table[(10, 5, False)] = 0    # Q7o
    table[(10, 4, False)] = 0    # Q6o
    table[(10, 3, False)] = 0    # Q5o
    table[(10, 2, False)] = 0    # Q4o
    table[(10, 1, False)] = 0    # Q3o
    table[(10, 0, False)] = 0    # Q2o

    # --- Jack-x suited ---
    table[(9, 8, True)] = 4      # JTs
    table[(9, 7, True)] = 3      # J9s
    # J8s and below: 0

    # --- Jack-x offsuit ---
    table[(9, 8, False)] = 0     # JTo
    # J9o and below: 0

    # --- Ten-x suited ---
    table[(8, 7, True)] = 3      # T9s
    # T8s and below: 0

    # --- Ten-x offsuit: all 0 ---

    # --- 9-x and below: all 0 (already initialized) ---

    return table


CALL_TABLE = _build_call_table()

# === HELPERS ===
# All helpers are class methods per D-12

# === BOT CLASS ===


class HawkEyeBot(Bot):
    """MTTBot -- IIT Poker Club Tournament Bot.

    A crash-proof bot with safety guards, tight-passive decision logic,
    and premium hand raises. Foundation for all subsequent phases.
    """

    def __init__(self):
        super().__init__("HawkEye")
        # Per-simulation state (persists across hands)
        self._hand_num = 0  # STATE-04 counter

        # Per-hand state (reset each hand by Plan 02's hand detection)
        self._last_board_len = -1  # Sentinel for first-hand edge case
        self._pot_total = 0  # Accumulated pot from prior streets
        self._street_pot = 0  # Current street's pot reading
        self._was_preflop_aggressor = False  # STATE-03 flag

    def get_action(self, game_state):
        """SAFE-02: try/except wrapper -- no exception ever escapes."""
        try:
            return self._decide(game_state)
        except Exception:
            if game_state.get("call_amount", 0) == 0:
                return ("call", 0)
            return ("fold", 0)

    def _guard(self, action, amount, game_state):
        """SAFE-07: Validate and correct every action before returning.

        Validation sequence:
        1. SAFE-04: Never return ('check', 0)
        2. SAFE-03: Never fold when call_amount == 0
        3. Handle fold normally
        4. Handle call
        5. SAFE-05: Validate raise amounts (floor and cap)
        6. Fallback for unrecognized actions
        """
        call_amount = game_state["call_amount"]
        stack_size = game_state["stack_size"]
        min_raise = game_state["min_raise"]

        # 1. SAFE-04: Never return ('check', 0) -- convert to ('call', 0)
        if action == "check":
            return ("call", 0)

        # 2. SAFE-03: Never fold when call_amount is 0
        if action == "fold" and call_amount == 0:
            return ("call", 0)

        # 3. Handle fold normally
        if action == "fold":
            return ("fold", 0)

        # 4. Handle call
        if action == "call":
            return ("call", 0)

        # 5. SAFE-05: Validate raise amount
        if action == "raise":
            if amount is None or amount < min_raise:
                amount = min_raise
            if amount > stack_size:
                amount = stack_size
            # If we can't afford even the call, just call
            if stack_size <= call_amount:
                return ("call", 0)
            return ("raise", amount)

        # 6. Fallback: unrecognized action -> call (safe default)
        return ("call", 0)

    def _detect_new_hand(self, game_state):
        """STATE-02, STATE-04: Detect hand boundaries and reset per-hand state.

        Uses board_cards length transitions to detect new hands:
        - First call ever: _last_board_len == -1 (sentinel) -> initialize
        - New hand: board went from non-empty back to empty
        - Same hand: no transition detected, do nothing
        """
        board_len = len(game_state["board_cards"])

        if self._last_board_len == -1:
            # First call ever in this simulation (sentinel)
            self._hand_num = 1
            self._pot_total = 0
            self._street_pot = 0
            self._was_preflop_aggressor = False
            return

        if board_len == 0 and self._last_board_len > 0:
            # Board went from having cards to empty = new hand (D-07)
            self._hand_num += 1  # STATE-04
            # Reset per-hand state (D-09)
            self._pot_total = 0
            self._street_pot = 0
            self._was_preflop_aggressor = False  # STATE-03 reset

    def _update_pot(self, game_state):
        """STATE-01: Track total pot across streets.

        Engine's pot_size only shows current-street bets (D-08).
        This method accumulates pot across streets additively.

        Returns estimated total pot (locked streets + current street).
        """
        board_len = len(game_state["board_cards"])

        # Detect new street: board grew (D-08 additive tracking)
        if board_len > self._last_board_len and self._last_board_len >= 0:
            # Previous street's bets are now locked in
            self._pot_total += self._street_pot
            self._street_pot = 0

        # Read current street's running total from engine
        self._street_pot = game_state["pot_size"]

        # Update board length tracker
        self._last_board_len = board_len

        # Return estimated total pot
        return self._pot_total + self._street_pot

    def _decide(self, game_state):
        """Main decision router: preflop engine or postflop fallback.

        D-11: Routes to _preflop() when board is empty, tight-passive
        fallback for postflop (Phase 3/4 will replace postflop logic).
        """
        # 1. Detect hand boundary and reset state
        self._detect_new_hand(game_state)

        # 2. Update pot accumulator
        est_pot = self._update_pot(game_state)

        # 3. Route to preflop or postflop
        if len(game_state["board_cards"]) == 0:
            return self._preflop(game_state, est_pot)
        else:
            # Phase 3/4 will add postflop logic. For now, use tight-passive fallback.
            call_amount = game_state["call_amount"]
            stack_size = game_state["stack_size"]
            if call_amount == 0:
                return self._guard("call", 0, game_state)
            if call_amount < stack_size * 0.15:
                return self._guard("call", 0, game_state)
            return self._guard("fold", 0, game_state)

    def _is_premium(self, hole_cards):
        """D-02: Detect premium hands (AA, KK, QQ) from treys integer encoding.

        Treys card encoding: rank = ((card >> 8) & 0xF) + 2
        Ace=14, King=13, Queen=12
        Premium = pocket pair with both ranks >= 12 (QQ+)
        """
        r1 = ((hole_cards[0] >> 8) & 0xF) + 2
        r2 = ((hole_cards[1] >> 8) & 0xF) + 2
        return r1 == r2 and r1 >= 12  # AA(14,14) KK(13,13) QQ(12,12)

    def _get_chen_key(self, hole_cards):
        """PRE-01: Extract (high_rank_int, low_rank_int, suited) from treys card ints."""
        r1 = (hole_cards[0] >> 8) & 0xF
        r2 = (hole_cards[1] >> 8) & 0xF
        s1 = (hole_cards[0] >> 12) & 0xF
        s2 = (hole_cards[1] >> 12) & 0xF
        high = max(r1, r2)
        low = min(r1, r2)
        suited = (s1 == s2) and (r1 != r2)  # pairs cannot be suited
        return (high, low, suited)

    def _get_stack_mode(self, game_state):
        """PRE-02: Classify stack depth into deep/medium/shallow/push_fold."""
        bb = game_state["blinds"]["big"]
        if bb == 0:
            return "deep"  # T-02-05: avoid division by zero
        bbs = game_state["stack_size"] / bb
        if bbs >= 40:
            return "deep"
        elif bbs >= 25:
            return "medium"
        elif bbs >= 15:
            return "shallow"
        else:
            return "push_fold"

    def _detect_situation(self, game_state):
        """PRE-06: Infer preflop situation from call_amount relative to blinds."""
        call_amount = game_state["call_amount"]
        bb = game_state["blinds"]["big"]
        sb = game_state["blinds"]["small"]
        if call_amount == 0:
            return "bb_option"
        elif call_amount == bb - sb:
            return "sb_complete"
        elif call_amount == bb:
            return "rfi"
        elif call_amount < bb * 6:
            return "facing_open"
        else:
            return "facing_3bet"

    def _is_3bet_hand(self, hole_cards):
        """PRE-08: QQ+, AKs -- hands that 3-bet facing an open."""
        r1 = (hole_cards[0] >> 8) & 0xF
        r2 = (hole_cards[1] >> 8) & 0xF
        s1 = (hole_cards[0] >> 12) & 0xF
        s2 = (hole_cards[1] >> 12) & 0xF
        high = max(r1, r2)
        low = min(r1, r2)
        if r1 == r2 and r1 >= 10:      # QQ(10), KK(11), AA(12)
            return True
        if high == 12 and low == 11 and s1 == s2:  # AKs
            return True
        return False

    def _is_4bet_hand(self, hole_cards):
        """PRE-08: AA, KK -- hands that 4-bet facing a 3-bet."""
        r1 = (hole_cards[0] >> 8) & 0xF
        r2 = (hole_cards[1] >> 8) & 0xF
        return r1 == r2 and r1 >= 11    # KK(11), AA(12)

    def _preflop_raise_amount(self, game_state, stack_mode):
        """PRE-09: Calculate raise increment by stack mode.

        Returns the amount parameter for ('raise', amount).
        Engine does: total_to_put_in = call_amount + amount.
        """
        bb = game_state["blinds"]["big"]
        call_amount = game_state["call_amount"]
        if stack_mode == "deep":
            desired_total = int(bb * 2.5)
        elif stack_mode == "medium":
            desired_total = int(bb * 2.2)
        else:  # shallow
            desired_total = int(bb * 2.0)
        # amount is the raise increment above call_amount
        amount = desired_total - call_amount
        if amount < 1:
            amount = 1  # _guard will floor to min_raise
        return amount

    def _preflop(self, game_state, est_pot):
        """PRE-03, PRE-07: Main preflop decision engine.

        Decision tree: stack mode -> situation -> hand strength -> action.
        All returns go through _guard() (T-02-08).
        """
        hole_cards = game_state["hole_cards"]
        call_amount = game_state["call_amount"]
        stack = game_state["stack_size"]
        bb = game_state["blinds"]["big"]

        # 1. Extract chen key and score (T-02-07: .get with default 0)
        chen_key = self._get_chen_key(hole_cards)
        chen_score = CHEN_TABLE.get(chen_key, 0)

        # 2. Get stack mode and situation
        stack_mode = self._get_stack_mode(game_state)
        situation = self._detect_situation(game_state)

        # === PUSH-FOLD MODE (<15BB) ===
        if stack_mode == "push_fold":
            # BB option: free check
            if situation == "bb_option":
                return self._guard("call", 0, game_state)

            # Facing a shove (call_amount >= 50% of stack)
            if call_amount >= stack * 0.5:
                villain_bb = call_amount / bb if bb > 0 else 999
                if CALL_TABLE.get(chen_key, 0) >= villain_bb:
                    return self._guard("call", 0, game_state)
                else:
                    return self._guard("fold", 0, game_state)

            # RFI or SB complete: shove or fold
            if situation in ("rfi", "sb_complete"):
                hero_bb = stack / bb if bb > 0 else 999
                if SHOVE_TABLE.get(chen_key, 0) >= hero_bb:
                    self._was_preflop_aggressor = True
                    return self._guard("raise", stack, game_state)
                else:
                    return self._guard("fold", 0, game_state)

            # Facing open or facing 3-bet in push-fold: reshove or fold
            if situation in ("facing_open", "facing_3bet"):
                villain_bb = call_amount / bb if bb > 0 else 999
                if CALL_TABLE.get(chen_key, 0) >= villain_bb:
                    self._was_preflop_aggressor = True
                    return self._guard("raise", stack, game_state)
                else:
                    return self._guard("fold", 0, game_state)

            # Fallback
            return self._guard("fold", 0, game_state)

        # === SHALLOW MODE (15-24BB) ===
        if stack_mode == "shallow":
            # BB option: free check
            if situation == "bb_option":
                return self._guard("call", 0, game_state)

            # Large bet relative to stack (>= 40%): treat as shove decision
            if call_amount >= stack * 0.4:
                villain_bb = call_amount / bb if bb > 0 else 999
                if CALL_TABLE.get(chen_key, 0) >= villain_bb:
                    self._was_preflop_aggressor = True
                    return self._guard("raise", stack, game_state)
                else:
                    return self._guard("fold", 0, game_state)

            # RFI: shove strong, raise decent, fold trash
            if situation == "rfi":
                hero_bb = stack / bb if bb > 0 else 999
                if SHOVE_TABLE.get(chen_key, 0) >= hero_bb:
                    self._was_preflop_aggressor = True
                    return self._guard("raise", stack, game_state)
                elif chen_score >= 8:
                    self._was_preflop_aggressor = True
                    amt = self._preflop_raise_amount(game_state, stack_mode)
                    return self._guard("raise", amt, game_state)
                else:
                    return self._guard("fold", 0, game_state)

            # Facing open: 3-bet shove premium, call decent, fold trash
            if situation == "facing_open":
                if self._is_3bet_hand(hole_cards):
                    self._was_preflop_aggressor = True
                    return self._guard("raise", stack, game_state)
                elif chen_score >= 7:
                    return self._guard("call", 0, game_state)
                else:
                    return self._guard("fold", 0, game_state)

            # Facing 3-bet: 4-bet shove or fold
            if situation == "facing_3bet":
                if self._is_4bet_hand(hole_cards):
                    self._was_preflop_aggressor = True
                    return self._guard("raise", stack, game_state)
                else:
                    return self._guard("fold", 0, game_state)

            # SB complete: call with decent, fold trash
            if situation == "sb_complete":
                if chen_score >= 4:
                    return self._guard("call", 0, game_state)
                else:
                    return self._guard("fold", 0, game_state)

            # Fallback
            return self._guard("fold", 0, game_state)

        # === DEEP / MEDIUM MODE (25BB+) ===
        # Chen thresholds by stack mode
        rfi_threshold = 6 if stack_mode == "deep" else 7

        # BB option: always check (free card)
        if situation == "bb_option":
            return self._guard("call", 0, game_state)

        # RFI: open with hands above threshold
        if situation == "rfi":
            if chen_score >= rfi_threshold:
                self._was_preflop_aggressor = True
                amt = self._preflop_raise_amount(game_state, stack_mode)
                return self._guard("raise", amt, game_state)
            else:
                return self._guard("fold", 0, game_state)

        # SB complete: call with wide range (chen >= 4)
        if situation == "sb_complete":
            if chen_score >= 4:
                return self._guard("call", 0, game_state)
            else:
                return self._guard("fold", 0, game_state)

        # Facing open: 3-bet premium, call decent, fold trash
        if situation == "facing_open":
            if self._is_3bet_hand(hole_cards):
                self._was_preflop_aggressor = True
                # 3x the open: amount = call_amount * 2
                amt = call_amount * 2
                return self._guard("raise", amt, game_state)
            elif chen_score >= 5:
                return self._guard("call", 0, game_state)
            else:
                return self._guard("fold", 0, game_state)

        # Facing 3-bet: 4-bet all-in with AA/KK, call strong deep, fold rest
        if situation == "facing_3bet":
            if self._is_4bet_hand(hole_cards):
                self._was_preflop_aggressor = True
                return self._guard("raise", stack, game_state)
            elif chen_score >= 9 and stack_mode == "deep":
                return self._guard("call", 0, game_state)
            else:
                return self._guard("fold", 0, game_state)

        # Fallback: fold unknown situations
        return self._guard("fold", 0, game_state)

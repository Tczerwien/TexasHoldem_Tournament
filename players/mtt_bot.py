from engine.player_interface import Bot
import math
import random

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
        self._initial_table_players = 0  # TOURN-03: captured on first hand

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
            self._initial_table_players = game_state["active_players"]  # TOURN-03
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
        """Main decision router: preflop engine or postflop decision engine.

        D-10: Routes to _preflop() when board is empty,
        _postflop() when board cards are present.
        """
        # 1. Detect hand boundary and reset state
        self._detect_new_hand(game_state)

        # 2. Update pot accumulator
        est_pot = self._update_pot(game_state)

        # 3. Route to preflop or postflop
        if len(game_state["board_cards"]) == 0:
            return self._preflop(game_state, est_pot)
        else:
            return self._postflop(game_state, est_pot)

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

    # === PHASE 5: TOURNAMENT AWARENESS ===

    def _get_tournament_stage(self, game_state):
        """TOURN-01: Detect tournament stage from active players and blind level.

        Priority: player count first (heads_up/itm/bubble), then blind level
        for multi-player stages (early/middle/late).

        Returns one of: 'heads_up', 'itm', 'bubble', 'early', 'middle', 'late'.
        """
        n = game_state["active_players"]
        if n <= 2:
            return "heads_up"
        if n <= 3:
            return "itm"
        if n <= 4:
            return "bubble"
        bb = game_state["blinds"]["big"]
        if bb <= 30:
            return "early"
        if bb <= 100:
            return "middle"
        return "late"

    def _get_stack_role(self, game_state):
        """TOURN-03: Classify hero stack as big/medium/short relative to avg.

        Uses _initial_table_players * 1500 as total chip count (chips are
        conserved in tournament). Average = total / active_players.

        Returns one of: 'big' (>= 1.5x avg), 'short' (<= 0.5x avg), 'medium'.
        """
        total_chips = self._initial_table_players * 1500
        n = game_state["active_players"]
        avg_stack = total_chips / n
        my_stack = game_state["stack_size"]
        if my_stack >= avg_stack * 1.5:
            return "big"
        elif my_stack <= avg_stack * 0.5:
            return "short"
        else:
            return "medium"

    def _detect_situation(self, game_state):
        """PRE-06: Infer preflop situation from call_amount relative to blinds."""
        call_amount = game_state["call_amount"]
        bb = game_state["blinds"]["big"]
        sb = game_state["blinds"]["small"]
        if call_amount == 0:
            return "bb_option"
        # Only treat as sb_complete if sb < bb (standard blind structure)
        elif sb < bb and call_amount == bb - sb:
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
        if len(hole_cards) < 2:
            # Malformed state -- fall back safely
            return self._guard("fold", 0, game_state)
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

            # Push-fold: detect whether villain is effectively all-in
            # Use call_amount > 8 * bb as proxy for "villain shoved"
            # (8BB+ call in push-fold territory means villain committed significant stack)
            if call_amount > bb * 8:
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
                # 3-bet to ~3x the open. Engine uses raise-BY semantics:
                # total_to_put_in = call_amount + amount
                # So to make total = 3 * call_amount: amount = 2 * call_amount
                threex_amount = call_amount * 2
                return self._guard("raise", threex_amount, game_state)
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

    # --- Phase 3: Postflop Analysis Methods ---

    def _eval_5(self, cards):
        """POST-01: Evaluate a 5-card poker hand.

        Takes a list of exactly 5 treys-encoded card integers.
        Returns a classification tuple where lower = better hand (treys convention).

        Tuple format: (class_id, -tiebreaker1, -tiebreaker2, ...)
          0 = straight flush, 1 = four of a kind, 2 = full house,
          3 = flush, 4 = straight, 5 = three of a kind,
          6 = two pair, 7 = one pair, 8 = high card

        Uses manual rank/suit classification per D-01.
        """
        # Extract ranks and suits via bit operations
        ranks = sorted([(c >> 8) & 0xF for c in cards], reverse=True)
        suits = [(c >> 12) & 0xF for c in cards]

        # Check flush: all 5 suits identical
        is_flush = suits[0] == suits[1] == suits[2] == suits[3] == suits[4]

        # Build frequency dict
        freq = {}
        for r in ranks:
            freq[r] = freq.get(r, 0) + 1

        # Sort groups by (count, rank) descending for hand classification
        groups = sorted(freq.items(), key=lambda x: (x[1], x[0]), reverse=True)

        # Check straight: 5 unique ranks with span of 4
        unique_sorted = sorted(set(ranks))
        is_straight = False
        straight_high = -1

        if len(unique_sorted) == 5:
            # Normal straight: highest - lowest == 4
            if unique_sorted[4] - unique_sorted[0] == 4:
                is_straight = True
                straight_high = unique_sorted[4]
            # Wheel: A-2-3-4-5 (ranks 12, 0, 1, 2, 3)
            elif unique_sorted == [0, 1, 2, 3, 12]:
                is_straight = True
                straight_high = 3  # 5-high straight

        # Classify hand
        counts = [g[1] for g in groups]

        # Straight flush
        if is_flush and is_straight:
            return (0, -straight_high)

        # Four of a kind
        if counts[0] == 4:
            quad_rank = groups[0][0]
            kicker_rank = groups[1][0]
            return (1, -quad_rank, -kicker_rank)

        # Full house
        if counts[0] == 3 and counts[1] == 2:
            trips_rank = groups[0][0]
            pair_rank = groups[1][0]
            return (2, -trips_rank, -pair_rank)

        # Flush (not straight -- already caught above)
        if is_flush:
            return (3, -ranks[0], -ranks[1], -ranks[2], -ranks[3], -ranks[4])

        # Straight (not flush -- already caught above)
        if is_straight:
            return (4, -straight_high)

        # Three of a kind (no pair beside it -- else would be full house)
        if counts[0] == 3:
            trips_rank = groups[0][0]
            kickers = sorted([g[0] for g in groups[1:]], reverse=True)
            return (5, -trips_rank, -kickers[0], -kickers[1])

        # Two pair
        if counts[0] == 2 and counts[1] == 2:
            high_pair = max(groups[0][0], groups[1][0])
            low_pair = min(groups[0][0], groups[1][0])
            kicker = groups[2][0]
            return (6, -high_pair, -low_pair, -kicker)

        # One pair
        if counts[0] == 2:
            pair_rank = groups[0][0]
            kickers = sorted([g[0] for g in groups[1:]], reverse=True)
            return (7, -pair_rank, -kickers[0], -kickers[1], -kickers[2])

        # High card
        return (8, -ranks[0], -ranks[1], -ranks[2], -ranks[3], -ranks[4])

    def _eval_7(self, cards):
        """POST-01: Evaluate a 7-card poker hand by checking all C(7,5)=21 combinations.

        Takes a list of exactly 7 treys-encoded card integers.
        Returns the best (lowest) 5-card hand rank tuple found among all 21 combos.

        Uses COMBO_INDICES module-level constant per D-03.
        """
        best = (9,)  # Sentinel worse than any real hand (max class is 8)
        for idx in COMBO_INDICES:
            five = [cards[i] for i in idx]
            r = self._eval_5(five)
            if r < best:
                best = r
        return best

    def _mc_equity(self, hole, board):
        """POST-02, D-04, D-09: Monte Carlo equity estimation.

        Samples random opponent hands and remaining board cards to estimate
        hero's equity (probability of winning) against a random opponent.

        Uses random.sample for MC inner loop (50x faster than numpy for
        small samples per CLAUDE.md). Fixed iteration caps: 300 flop,
        400 turn, 500 river.

        Args:
            hole: list of 2 treys-encoded card integers (hero's hole cards)
            board: list of 3-5 treys-encoded card integers (community cards)

        Returns:
            float: equity between 0.0 and 1.0
        """
        # Guard: preflop or invalid board -> return 0.5 (Pitfall 5)
        if len(board) < 3:
            return 0.5

        # Build known set for O(1) exclusion (T-03-04 mitigation)
        known = set(hole + board)
        remaining = [c for c in FULL_DECK if c not in known]

        # Fixed iteration caps per D-04
        board_len = len(board)
        if board_len == 3:
            iters = 300   # Flop
        elif board_len == 4:
            iters = 400   # Turn
        else:
            iters = 500   # River

        # Cards needed: 2 opponent hole + remaining board cards
        need = 2 + (5 - board_len)

        wins = 0
        ties = 0
        for _ in range(iters):
            draw = random.sample(remaining, need)
            opp_hole = draw[:2]
            extra_board = draw[2:]
            full_board = board + extra_board
            my_rank = self._eval_7(hole + full_board)
            opp_rank = self._eval_7(opp_hole + full_board)
            # Lower tuple = better hand (Pitfall 7)
            if my_rank < opp_rank:
                wins += 1
            elif my_rank == opp_rank:
                ties += 1

        return (wins + ties * 0.5) / iters

    def _detect_draws(self, hole, board):
        """POST-03, D-05: Detect draw types from hole + board cards.

        Checks for flush draws, open-ended straight draws (OESD),
        gutshots, and combo draws. Handles edge cases: made flush
        suppresses flush draw (Pitfall 2), ace boundaries suppress
        OESD (Pitfall 3).

        Args:
            hole: list of 2 treys-encoded card integers
            board: list of 3-5 treys-encoded card integers

        Returns:
            dict with keys: flush_draw, oesd, gutshot, combo_draw (all bool)
        """
        combined = hole + board

        # --- Flush draw detection ---
        suit_counts = {}
        for c in combined:
            s = (c >> 12) & 0xF
            suit_counts[s] = suit_counts.get(s, 0) + 1

        has_made_flush = any(cnt >= 5 for cnt in suit_counts.values())
        has_flush_draw = any(cnt == 4 for cnt in suit_counts.values())
        # Pitfall 2: made flush suppresses flush draw
        if has_made_flush:
            has_flush_draw = False

        # --- Straight draw detection ---
        unique_ranks = sorted(set((c >> 8) & 0xF for c in combined))
        # Add ace-low (-1) if ace present for wheel detection
        if 12 in unique_ranks:
            unique_ranks = [-1] + unique_ranks

        has_oesd = False
        has_gutshot = False
        # Check for made straight (5+ consecutive) to suppress draws
        has_made_straight = False
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i + 4] - unique_ranks[i] == 4:
                has_made_straight = True
                break

        if not has_made_straight:
            # Scan all windows of 4 ranks
            for i in range(len(unique_ranks)):
                for j in range(i + 3, len(unique_ranks)):
                    if j - i != 3:
                        continue  # only look at exactly 4 ranks
                    span = unique_ranks[j] - unique_ranks[i]
                    if span == 3:
                        # 4 consecutive ranks -> OESD if both ends open
                        low_end = unique_ranks[i] - 1
                        high_end = unique_ranks[j] + 1
                        # Pitfall 3: both ends must be valid ranks (0-12)
                        if low_end >= 0 and high_end <= 12:
                            has_oesd = True
                    elif span == 4:
                        # 4 ranks spanning 5 -> gutshot (one gap)
                        has_gutshot = True

        has_combo = has_flush_draw and (has_oesd or has_gutshot)

        return {
            "flush_draw": has_flush_draw,
            "oesd": has_oesd,
            "gutshot": has_gutshot,
            "combo_draw": has_combo,
        }

    def _classify_board(self, board):
        """POST-05, D-06: Board texture classification.

        Classifies the community cards as PAIRED, DRY, SEMI_WET, or WET.
        PAIRED takes priority over all other classifications.

        Args:
            board: list of 3-5 treys-encoded card integers

        Returns:
            str: one of 'PAIRED', 'DRY', 'SEMI_WET', 'WET'
        """
        ranks = [(c >> 8) & 0xF for c in board]
        suits = [(c >> 12) & 0xF for c in board]

        # Check PAIRED first (takes priority)
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        if any(c >= 2 for c in rank_counts.values()):
            return "PAIRED"

        # Flush potential: 3+ cards share a suit on board
        suit_counts = {}
        for s in suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
        max_suit = max(suit_counts.values())
        flush_possible = max_suit >= 3

        # Connectedness: check if 3 board ranks fall within a tight span
        unique_ranks = sorted(set(ranks))
        if 12 in unique_ranks:
            unique_ranks_ext = [-1] + unique_ranks
        else:
            unique_ranks_ext = unique_ranks

        connected = False
        # Check for any 3 consecutive board ranks within span <= 3
        # (Pitfall 4: avoid over-classification)
        for i in range(len(unique_ranks_ext) - 2):
            span = unique_ranks_ext[i + 2] - unique_ranks_ext[i]
            if span <= 3:
                connected = True
                break

        if flush_possible and connected:
            return "WET"
        elif flush_possible or connected:
            return "SEMI_WET"
        else:
            return "DRY"

    def _ehs(self, hole, board):
        """POST-04, D-07: Effective Hand Strength combining equity with draw bonus.

        EHS = mc_equity + draw_bonus, capped at 1.0.
        On river (5 board cards), no draw bonus is applied since no cards
        remain to complete draws.

        Draw bonuses (in priority order):
        - combo_draw: 0.09 (flush + straight draw)
        - flush_draw: 0.06
        - oesd: 0.05
        - gutshot: 0.03

        Args:
            hole: list of 2 treys-encoded card integers
            board: list of 3-5 treys-encoded card integers

        Returns:
            float: effective hand strength between 0.0 and 1.0
        """
        equity = self._mc_equity(hole, board)

        # No draw bonus on river (no cards to come)
        if len(board) >= 5:
            return equity

        draws = self._detect_draws(hole, board)

        # Draw bonus in priority order (combo first since it includes flush+straight)
        if draws["combo_draw"]:
            bonus = 0.09
        elif draws["flush_draw"]:
            bonus = 0.06
        elif draws["oesd"]:
            bonus = 0.05
        elif draws["gutshot"]:
            bonus = 0.03
        else:
            bonus = 0.0

        return min(equity + bonus, 1.0)

    # === PHASE 4: POSTFLOP DECISION ENGINE ===

    def _cbet_threshold(self, texture):
        """POST-06: Return EHS threshold for c-betting based on board texture.

        DRY boards allow wider c-betting (lower threshold) since they
        connect with fewer opponent ranges. WET boards require stronger
        hands to c-bet profitably.

        Args:
            texture: str, one of 'DRY', 'SEMI_WET', 'PAIRED', 'WET'

        Returns:
            float: EHS threshold for c-bet decision
        """
        if texture == "DRY":
            return 0.35
        elif texture == "SEMI_WET":
            return 0.45
        elif texture == "PAIRED":
            return 0.40
        else:  # WET
            return 0.55

    def _calc_bet_size(self, est_pot, stack, texture, street):
        """POST-09: Calculate bet size as pot fraction by street and texture.

        Flop sizing varies by texture (deny equity on wet boards).
        Turn and river use fixed fractions regardless of texture.
        Result floored to 1 chip minimum; _guard() handles min_raise.

        Args:
            est_pot: int, estimated total pot
            stack: int, our remaining stack
            texture: str, board texture classification
            street: int, 3=flop, 4=turn, 5=river

        Returns:
            int: bet amount in chips (at least 1)
        """
        if street == 3:
            # Flop: sizing varies by texture
            if texture == "DRY":
                frac = 0.33
            elif texture == "WET":
                frac = 0.66
            else:  # SEMI_WET, PAIRED
                frac = 0.50
        elif street == 4:
            # Turn: 66% pot
            frac = 0.66
        else:
            # River: 75% pot
            frac = 0.75

        raw = int(est_pot * frac)
        return max(raw, 1)

    def _facing_bet(self, game_state, est_pot, ehs, texture, street):
        """POST-07/08/10/13: Decision when facing a bet (call_amount > 0).

        Decision hierarchy:
        1. SPR < 1.5 with adequate equity -> shove (POST-13)
        2. EHS >= 0.85 (MONSTER) -> raise, with stack commitment check (POST-08/10)
        3. EHS >= required equity -> call (POST-07)
        4. Otherwise -> fold

        Args:
            game_state: dict from engine
            est_pot: int, estimated total pot
            ehs: float, effective hand strength 0.0-1.0
            texture: str, board texture
            street: int, 3=flop, 4=turn, 5=river

        Returns:
            tuple: (action, amount) validated by _guard()
        """
        call_amount = game_state["call_amount"]
        stack = game_state["stack_size"]

        # POST-07: Required equity = call / (pot + call)
        req_eq = call_amount / (est_pot + call_amount) if (est_pot + call_amount) > 0 else 0.0

        # POST-13: SPR commitment check
        safe_pot = est_pot if est_pot > 0 else 1
        spr = stack / safe_pot

        if spr < 1.5 and ehs >= req_eq:
            # Low SPR with enough equity -> shove
            return self._guard("raise", stack, game_state)

        # POST-08: Monster hand raises
        if ehs >= 0.85:
            raise_size = self._calc_bet_size(est_pot, stack, texture, street)
            # POST-10: Stack commitment (bet >= 60% stack -> shove)
            if raise_size >= stack * 0.6:
                return self._guard("raise", stack, game_state)
            return self._guard("raise", raise_size, game_state)

        # POST-07: Pot odds call
        if ehs >= req_eq:
            return self._guard("call", 0, game_state)

        # Not enough equity -> fold
        return self._guard("fold", 0, game_state)

    def _bet_or_check(self, game_state, est_pot, ehs, texture, street):
        """POST-06/11/12/13: Decision when first to act (call_amount == 0).

        Decision hierarchy:
        1. Flop + preflop aggressor + EHS >= c-bet threshold -> c-bet (POST-06)
        2. Turn + EHS >= 0.65 (STRONG+) -> barrel at 66% pot (POST-11)
        3. River + EHS >= 0.65 (STRONG+) -> value bet at 75% pot (POST-12)
        4. Otherwise -> check

        All bets check SPR (POST-13) and stack commitment (POST-10) before sizing.

        Args:
            game_state: dict from engine
            est_pot: int, estimated total pot
            ehs: float, effective hand strength 0.0-1.0
            texture: str, board texture
            street: int, 3=flop, 4=turn, 5=river

        Returns:
            tuple: (action, amount) validated by _guard()
        """
        stack = game_state["stack_size"]

        # POST-13: SPR commitment check
        safe_pot = est_pot if est_pot > 0 else 1
        spr = stack / safe_pot

        # Helper: apply SPR and stack commitment to a bet
        def _apply_commit(bet_size):
            if spr < 1.5:
                return self._guard("raise", stack, game_state)
            if bet_size >= stack * 0.6:
                return self._guard("raise", stack, game_state)
            return self._guard("raise", bet_size, game_state)

        # POST-06: C-bet on flop when preflop aggressor
        if street == 3 and self._was_preflop_aggressor:
            threshold = self._cbet_threshold(texture)
            if ehs >= threshold:
                bet_size = self._calc_bet_size(est_pot, stack, texture, street)
                return _apply_commit(bet_size)

        # POST-11: Turn barrel with STRONG+ hands
        if street == 4 and ehs >= 0.65:
            bet_size = self._calc_bet_size(est_pot, stack, texture, street)
            return _apply_commit(bet_size)

        # POST-12: River value bet with STRONG+ hands
        if street == 5 and ehs >= 0.65:
            bet_size = self._calc_bet_size(est_pot, stack, texture, street)
            return _apply_commit(bet_size)

        # Default: check
        return self._guard("call", 0, game_state)

    def _postflop(self, game_state, est_pot):
        """POST: Single entry point for all postflop decisions.

        Computes EHS and texture ONCE (anti-pattern: never call _ehs twice),
        determines street from board length, then routes to _facing_bet
        or _bet_or_check based on call_amount.

        Args:
            game_state: dict from engine
            est_pot: int, estimated total pot

        Returns:
            tuple: (action, amount) from sub-method
        """
        hole = game_state["hole_cards"]
        board = game_state["board_cards"]
        call_amount = game_state["call_amount"]

        ehs = self._ehs(hole, board)
        texture = self._classify_board(board)
        street = len(board)  # 3=flop, 4=turn, 5=river

        if call_amount > 0:
            return self._facing_bet(game_state, est_pot, ehs, texture, street)
        else:
            return self._bet_or_check(game_state, est_pot, ehs, texture, street)

from engine.player_interface import Bot

# === CONSTANTS ===
# Phase 2+ will add lookup tables here

# === PRECOMPUTATION ===
# Phase 2+ will add module-level table builds here

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
        """Tight-passive decision logic with premium hand raises.

        D-01: Call if cheap (< 15% of stack), fold otherwise.
        D-02: Raise with premium hands (AA/KK/QQ) preflop.
        D-03: Always check when call_amount is 0 (non-premium).
        """
        # 1. Detect hand boundary and reset state
        self._detect_new_hand(game_state)

        # 2. Update pot accumulator
        est_pot = self._update_pot(game_state)

        call_amount = game_state["call_amount"]
        stack_size = game_state["stack_size"]
        min_raise = game_state["min_raise"]
        hole_cards = game_state["hole_cards"]
        board_cards = game_state["board_cards"]

        # D-03: Always check when free (handled by guard, but be explicit)
        if call_amount == 0:
            # D-02: Raise with premium hands preflop
            if len(board_cards) == 0 and self._is_premium(hole_cards):
                big_blind = game_state["blinds"]["big"]
                raise_amt = max(min_raise, big_blind * 3)
                if raise_amt > stack_size:
                    raise_amt = stack_size
                if len(board_cards) == 0:  # only set on preflop raises
                    self._was_preflop_aggressor = True
                return self._guard("raise", raise_amt, game_state)
            return self._guard("call", 0, game_state)

        # D-02: Raise with premium hands preflop when facing a bet
        if len(board_cards) == 0 and self._is_premium(hole_cards):
            raise_amt = max(min_raise, call_amount * 3)
            if raise_amt > stack_size:
                raise_amt = stack_size
            if len(board_cards) == 0:  # only set on preflop raises
                self._was_preflop_aggressor = True
            return self._guard("raise", raise_amt, game_state)

        # D-01: Tight-passive -- call if cheap (< 15% of stack), fold otherwise
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

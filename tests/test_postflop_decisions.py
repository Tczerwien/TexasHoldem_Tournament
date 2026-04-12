"""Postflop decision engine tests for HawkEyeBot.

Tests POST-06 through POST-13: c-bet logic, pot odds, raise/call/fold,
bet sizing by street/texture, stack commitment, turn barrel, river value bet,
SPR commitment, and postflop routing.

All tests mock _ehs() for deterministic fast execution.
"""
import sys
import os
import types

# Mock the engine module so we can import mtt_bot without the engine on PYTHONPATH
mock_engine = types.ModuleType("engine")
mock_player_interface = types.ModuleType("engine.player_interface")


class MockBot:
    def __init__(self, name):
        self.name = name

    def get_action(self, game_state):
        raise NotImplementedError


mock_player_interface.Bot = MockBot
sys.modules["engine"] = mock_engine
sys.modules["engine.player_interface"] = mock_player_interface

# Add players directory to path and import the bot
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "players"))
from mtt_bot import HawkEyeBot


_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]

# Rank chars to rank_int: '2'=0, '3'=1, ..., 'T'=8, 'J'=9, 'Q'=10, 'K'=11, 'A'=12
_RANK_MAP = {
    '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6,
    '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12
}

# Suit chars to suit_int: s=1 (spades), h=2 (hearts), d=4 (diamonds), c=8 (clubs)
_SUIT_MAP = {'s': 1, 'h': 2, 'd': 4, 'c': 8}


def make_card(name):
    """Build treys-encoded card integer from string like 'Ah', 'Ts', '2c'."""
    rank_char = name[0]
    suit_char = name[1]
    rank_int = _RANK_MAP[rank_char]
    suit_int = _SUIT_MAP[suit_char]
    return (1 << rank_int << 16) | (suit_int << 12) | (rank_int << 8) | _PRIMES[rank_int]


def make_gs(call_amount, stack_size, min_raise, board_cards, hole_cards=None,
            pot_size=0, big_blind=100, active_players=6):
    """Build a complete game_state dict for testing."""
    if hole_cards is None:
        hole_cards = [make_card("Ah"), make_card("Kh")]
    return {
        "hole_cards": hole_cards,
        "board_cards": board_cards,
        "call_amount": call_amount,
        "stack_size": stack_size,
        "min_raise": min_raise,
        "pot_size": pot_size,
        "blinds": {"big": big_blind, "small": big_blind // 2},
        "active_players": active_players,
    }


# --- Flop board fixtures ---
# DRY flop: rainbow, ungapped (e.g., 2s 7d Qc)
DRY_FLOP = [make_card("2s"), make_card("7d"), make_card("Qc")]
# WET flop: suited + connected (e.g., 8h 9h Th)
WET_FLOP = [make_card("8h"), make_card("9h"), make_card("Th")]
# SEMI_WET flop: connected but rainbow (e.g., 6s 7d 8c)
SEMI_WET_FLOP = [make_card("6s"), make_card("7d"), make_card("8c")]
# Turn board (4 cards, DRY)
DRY_TURN = [make_card("2s"), make_card("7d"), make_card("Qc"), make_card("4h")]
# River board (5 cards, DRY)
DRY_RIVER = [make_card("2s"), make_card("7d"), make_card("Qc"), make_card("4h"), make_card("9s")]


# ============================================================
# POST-06: C-Bet Tests
# ============================================================
class TestCbet:
    """POST-06: C-bet logic with preflop aggressor tracking and board texture."""

    def setup_method(self):
        self.bot = HawkEyeBot()
        self.bot._was_preflop_aggressor = True

    def test_cbet_dry_board(self):
        """Aggressor with EHS=0.40 on DRY board (threshold 0.35) -> raises."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=200)
        self.bot._ehs = lambda hole, board: 0.40
        self.bot._classify_board = lambda board: "DRY"
        action, amount = self.bot._bet_or_check(gs, est_pot=200, ehs=0.40,
                                                 texture="DRY", street=3)
        assert action == "raise", f"Expected raise on dry c-bet, got {action}"

    def test_cbet_wet_board_below_threshold(self):
        """Aggressor with EHS=0.50 on WET board (threshold 0.55) -> checks."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=WET_FLOP, pot_size=200)
        self.bot._ehs = lambda hole, board: 0.50
        self.bot._classify_board = lambda board: "WET"
        action, amount = self.bot._bet_or_check(gs, est_pot=200, ehs=0.50,
                                                 texture="WET", street=3)
        assert action == "call" and amount == 0, \
            f"Expected check (call,0), got ({action},{amount})"

    def test_cbet_wet_board_above_threshold(self):
        """Aggressor with EHS=0.60 on WET board (threshold 0.55) -> raises."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=WET_FLOP, pot_size=200)
        self.bot._ehs = lambda hole, board: 0.60
        self.bot._classify_board = lambda board: "WET"
        action, amount = self.bot._bet_or_check(gs, est_pot=200, ehs=0.60,
                                                 texture="WET", street=3)
        assert action == "raise", f"Expected raise on wet c-bet above threshold, got {action}"

    def test_no_cbet_not_aggressor(self):
        """Non-aggressor with EHS=0.60 on DRY flop -> checks (no c-bet right)."""
        self.bot._was_preflop_aggressor = False
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=200)
        self.bot._ehs = lambda hole, board: 0.60
        self.bot._classify_board = lambda board: "DRY"
        # EHS 0.60 is below STRONG (0.65), so non-aggressor checks
        action, amount = self.bot._bet_or_check(gs, est_pot=200, ehs=0.60,
                                                 texture="DRY", street=3)
        assert action == "call" and amount == 0, \
            f"Expected check for non-aggressor, got ({action},{amount})"


# ============================================================
# POST-07: Pot Odds Tests
# ============================================================
class TestPotOdds:
    """POST-07: Pot odds call/fold decisions."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_pot_odds_fold(self):
        """est_pot=100, call_amount=50, EHS=0.20 -> folds (req_eq=0.333)."""
        gs = make_gs(call_amount=50, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=100)
        action, amount = self.bot._facing_bet(gs, est_pot=100, ehs=0.20,
                                               texture="DRY", street=3)
        assert action == "fold", f"Expected fold (EHS < req_eq), got {action}"

    def test_pot_odds_call(self):
        """est_pot=100, call_amount=50, EHS=0.40 -> calls (req_eq=0.333)."""
        gs = make_gs(call_amount=50, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=100)
        action, amount = self.bot._facing_bet(gs, est_pot=100, ehs=0.40,
                                               texture="DRY", street=3)
        assert action == "call", f"Expected call (EHS >= req_eq), got {action}"


# ============================================================
# POST-08: Raise/Call/Fold Tests
# ============================================================
class TestFacingBet:
    """POST-08: Raise/call/fold decisions when facing a bet."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_facing_bet_raise_monster(self):
        """EHS=0.90 (MONSTER >= 0.85) -> raises."""
        gs = make_gs(call_amount=50, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=200)
        action, amount = self.bot._facing_bet(gs, est_pot=200, ehs=0.90,
                                               texture="DRY", street=3)
        assert action == "raise", f"Expected raise for monster hand, got {action}"

    def test_facing_bet_call_with_odds(self):
        """EHS=0.40, est_pot=100, call=50 -> calls (req_eq=0.333)."""
        gs = make_gs(call_amount=50, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=100)
        action, amount = self.bot._facing_bet(gs, est_pot=100, ehs=0.40,
                                               texture="DRY", street=3)
        assert action == "call", f"Expected call with pot odds, got {action}"

    def test_facing_bet_fold_no_odds(self):
        """EHS=0.15, est_pot=100, call=50 -> folds (req_eq=0.333)."""
        gs = make_gs(call_amount=50, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=100)
        action, amount = self.bot._facing_bet(gs, est_pot=100, ehs=0.15,
                                               texture="DRY", street=3)
        assert action == "fold", f"Expected fold without pot odds, got {action}"


# ============================================================
# POST-09: Bet Sizing Tests
# ============================================================
class TestBetSizing:
    """POST-09: Bet sizing system by street and texture."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_sizing_dry_flop(self):
        """Street=3, DRY texture, est_pot=300 -> 99 (33%)."""
        result = self.bot._calc_bet_size(est_pot=300, stack=1000,
                                          texture="DRY", street=3)
        assert result == 99, f"Expected 99 (33% of 300), got {result}"

    def test_sizing_wet_flop(self):
        """Street=3, WET texture, est_pot=300 -> 198 (66%)."""
        result = self.bot._calc_bet_size(est_pot=300, stack=1000,
                                          texture="WET", street=3)
        assert result == 198, f"Expected 198 (66% of 300), got {result}"

    def test_sizing_semi_wet_flop(self):
        """Street=3, SEMI_WET texture, est_pot=300 -> 150 (50%)."""
        result = self.bot._calc_bet_size(est_pot=300, stack=1000,
                                          texture="SEMI_WET", street=3)
        assert result == 150, f"Expected 150 (50% of 300), got {result}"

    def test_sizing_paired_flop(self):
        """Street=3, PAIRED texture, est_pot=300 -> 150 (50%)."""
        result = self.bot._calc_bet_size(est_pot=300, stack=1000,
                                          texture="PAIRED", street=3)
        assert result == 150, f"Expected 150 (50% of 300), got {result}"

    def test_sizing_turn(self):
        """Street=4, est_pot=300 -> 198 (66%)."""
        result = self.bot._calc_bet_size(est_pot=300, stack=1000,
                                          texture="DRY", street=4)
        assert result == 198, f"Expected 198 (66% of 300), got {result}"

    def test_sizing_river(self):
        """Street=5, est_pot=300 -> 225 (75%)."""
        result = self.bot._calc_bet_size(est_pot=300, stack=1000,
                                          texture="DRY", street=5)
        assert result == 225, f"Expected 225 (75% of 300), got {result}"


# ============================================================
# POST-10: Stack Commitment Tests
# ============================================================
class TestStackCommit:
    """POST-10: Stack commitment rule (bet >= 60% stack -> shove)."""

    def setup_method(self):
        self.bot = HawkEyeBot()
        self.bot._was_preflop_aggressor = True

    def test_stack_commit_shoves(self):
        """Stack=300, est_pot=300, bet would be ~198 (66% of 300) >= 60% of 300 -> shoves."""
        gs = make_gs(call_amount=0, stack_size=300, min_raise=100,
                     board_cards=DRY_TURN, pot_size=300)
        # EHS=0.70 (STRONG+) on turn -> would barrel at 66% pot = 198
        # 198 >= 0.6 * 300 (180) -> shove
        action, amount = self.bot._bet_or_check(gs, est_pot=300, ehs=0.70,
                                                 texture="DRY", street=4)
        assert action == "raise", f"Expected raise (shove), got {action}"
        assert amount == 300, f"Expected shove amount=stack (300), got {amount}"

    def test_stack_commit_normal(self):
        """Stack=1000, est_pot=300, bet=198 < 60% of 1000 -> normal raise."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_TURN, pot_size=300)
        # EHS=0.70 on turn -> barrel at 66% pot = 198
        # 198 < 0.6 * 1000 (600) -> normal raise
        action, amount = self.bot._bet_or_check(gs, est_pot=300, ehs=0.70,
                                                 texture="DRY", street=4)
        assert action == "raise", f"Expected raise, got {action}"
        assert amount == 198, f"Expected 198, got {amount}"


# ============================================================
# POST-11: Turn Barrel Tests
# ============================================================
class TestTurnBarrel:
    """POST-11: Turn barrel with STRONG+ hands (EHS >= 0.55 after TOURN-07 exploit adjustment)."""

    def setup_method(self):
        self.bot = HawkEyeBot()
        self.bot._was_preflop_aggressor = False  # non-aggressor to isolate turn logic

    def test_turn_barrel_strong(self):
        """Street=4, EHS=0.70, call_amount=0 -> raises at 66% pot."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_TURN, pot_size=300)
        action, amount = self.bot._bet_or_check(gs, est_pot=300, ehs=0.70,
                                                 texture="DRY", street=4)
        assert action == "raise", f"Expected raise on turn barrel, got {action}"
        assert amount == 198, f"Expected 198 (66% of 300), got {amount}"

    def test_turn_no_barrel_medium(self):
        """Street=4, EHS=0.50, call_amount=0 -> checks."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_TURN, pot_size=300)
        action, amount = self.bot._bet_or_check(gs, est_pot=300, ehs=0.50,
                                                 texture="DRY", street=4)
        assert action == "call" and amount == 0, \
            f"Expected check (call,0), got ({action},{amount})"


# ============================================================
# POST-12: River Value Bet Tests
# ============================================================
class TestRiverValueBet:
    """POST-12: River value bet with STRONG+ hands (EHS >= 0.55 after TOURN-07 exploit adjustment)."""

    def setup_method(self):
        self.bot = HawkEyeBot()
        self.bot._was_preflop_aggressor = False

    def test_river_value_bet_strong(self):
        """Street=5, EHS=0.70, call_amount=0 -> raises at 75% pot."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_RIVER, pot_size=300)
        action, amount = self.bot._bet_or_check(gs, est_pot=300, ehs=0.70,
                                                 texture="DRY", street=5)
        assert action == "raise", f"Expected raise on river value bet, got {action}"
        assert amount == 225, f"Expected 225 (75% of 300), got {amount}"

    def test_river_no_bet_medium(self):
        """Street=5, EHS=0.50, call_amount=0 -> checks."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_RIVER, pot_size=300)
        action, amount = self.bot._bet_or_check(gs, est_pot=300, ehs=0.50,
                                                 texture="DRY", street=5)
        assert action == "call" and amount == 0, \
            f"Expected check (call,0), got ({action},{amount})"


# ============================================================
# POST-13: SPR Commitment Tests
# ============================================================
class TestSPRCommit:
    """POST-13: SPR < 1.5 triggers shove when betting."""

    def setup_method(self):
        self.bot = HawkEyeBot()
        self.bot._was_preflop_aggressor = True

    def test_spr_commit_shoves(self):
        """Stack=100, est_pot=80, SPR=1.25 -> shoves when betting (c-bet on flop)."""
        gs = make_gs(call_amount=0, stack_size=100, min_raise=20,
                     board_cards=DRY_FLOP, pot_size=80)
        # EHS=0.40 on DRY board (threshold 0.35) -> would c-bet
        # SPR = 100/80 = 1.25 < 1.5 -> shove
        action, amount = self.bot._bet_or_check(gs, est_pot=80, ehs=0.40,
                                                 texture="DRY", street=3)
        assert action == "raise", f"Expected raise (SPR shove), got {action}"
        assert amount == 100, f"Expected shove amount=stack (100), got {amount}"

    def test_spr_no_commit(self):
        """Stack=1000, est_pot=80, SPR=12.5 -> normal sizing."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=20,
                     board_cards=DRY_FLOP, pot_size=80)
        # EHS=0.40 on DRY board (threshold 0.35) -> c-bet at 33% pot = 26
        action, amount = self.bot._bet_or_check(gs, est_pot=80, ehs=0.40,
                                                 texture="DRY", street=3)
        assert action == "raise", f"Expected raise (c-bet), got {action}"
        # 33% of 80 = 26.4 -> int = 26
        assert amount != 1000, f"Should not shove with SPR=12.5"


# ============================================================
# POST Routing Tests
# ============================================================
class TestPostflopRouting:
    """Test _postflop routes to _facing_bet or _bet_or_check."""

    def setup_method(self):
        self.bot = HawkEyeBot()
        self.bot._was_preflop_aggressor = False

    def test_postflop_routes_facing_bet(self):
        """call_amount > 0 -> _facing_bet path -> may fold/call/raise."""
        gs = make_gs(call_amount=50, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=200)
        # Mock _ehs to return low value -> should fold
        self.bot._ehs = lambda hole, board: 0.10
        self.bot._classify_board = lambda board: "DRY"
        action, amount = self.bot._postflop(gs, est_pot=200)
        assert action == "fold", f"Expected fold via _facing_bet path, got {action}"

    def test_postflop_routes_bet_or_check(self):
        """call_amount == 0 -> _bet_or_check path -> may check."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=200)
        # Mock _ehs to return medium value (no c-bet since not aggressor, not STRONG)
        self.bot._ehs = lambda hole, board: 0.50
        self.bot._classify_board = lambda board: "DRY"
        action, amount = self.bot._postflop(gs, est_pot=200)
        assert action == "call" and amount == 0, \
            f"Expected check (call,0) via _bet_or_check path, got ({action},{amount})"

    def test_postflop_computes_ehs_once(self):
        """_postflop calls _ehs exactly once (anti-pattern prevention)."""
        call_count = [0]
        original_ehs = self.bot._ehs

        def counting_ehs(hole, board):
            call_count[0] += 1
            return 0.50

        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=200)
        self.bot._ehs = counting_ehs
        self.bot._classify_board = lambda board: "DRY"
        self.bot._postflop(gs, est_pot=200)
        assert call_count[0] == 1, \
            f"_ehs should be called exactly once, was called {call_count[0]} times"


# ============================================================
# Edge case tests
# ============================================================
class TestEdgeCases:
    """Edge cases for postflop decisions."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_spr_facing_bet_shove(self):
        """SPR < 1.5 facing bet with adequate EHS -> shoves."""
        gs = make_gs(call_amount=50, stack_size=100, min_raise=50,
                     board_cards=DRY_FLOP, pot_size=80)
        # SPR = 100/80 = 1.25 < 1.5, EHS=0.50 >= req_eq (50/130 = 0.385)
        action, amount = self.bot._facing_bet(gs, est_pot=80, ehs=0.50,
                                               texture="DRY", street=3)
        assert action == "raise", f"Expected shove for low SPR facing bet, got {action}"
        assert amount == 100, f"Expected shove amount=stack (100), got {amount}"

    def test_cbet_threshold_values(self):
        """Verify _cbet_threshold returns correct values for each texture."""
        assert self.bot._cbet_threshold("DRY") == 0.35
        assert self.bot._cbet_threshold("SEMI_WET") == 0.45
        assert self.bot._cbet_threshold("PAIRED") == 0.40
        assert self.bot._cbet_threshold("WET") == 0.55

    def test_calc_bet_size_min_one(self):
        """Bet size floors to 1 chip minimum."""
        result = self.bot._calc_bet_size(est_pot=1, stack=1000,
                                          texture="DRY", street=3)
        # 33% of 1 = 0.33 -> floor would be 0 -> should be 1
        assert result >= 1, f"Bet size should be at least 1, got {result}"

    def test_est_pot_zero_no_crash(self):
        """est_pot=0 should not crash (division guard)."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=0)
        self.bot._was_preflop_aggressor = True
        self.bot._ehs = lambda hole, board: 0.50
        self.bot._classify_board = lambda board: "DRY"
        # Should not raise ZeroDivisionError
        action, amount = self.bot._postflop(gs, est_pot=0)
        # Just verify it returns a valid action tuple
        assert action in ("call", "fold", "raise"), \
            f"Expected valid action, got {action}"


# ============================================================
# Integration Tests: _decide() -> _postflop() routing
# ============================================================
class TestDecidePostflopRouting:
    """Integration tests proving _decide() routes to _postflop() for all
    postflop streets and the full pipeline (get_action -> _decide ->
    _postflop -> _facing_bet/_bet_or_check -> _guard) works correctly."""

    def setup_method(self):
        self.bot = HawkEyeBot()
        # Set state so _detect_new_hand does not reset anything
        self.bot._last_board_len = 3  # pretend we are mid-hand on flop
        self.bot._pot_total = 100
        self.bot._street_pot = 0
        self.bot._was_preflop_aggressor = False

    def test_decide_routes_to_postflop(self):
        """_decide routes to _postflop when board_cards is non-empty.
        Aggressor with EHS=0.50 on DRY flop -> c-bet (raise)."""
        gs = make_gs(call_amount=0, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=200)
        self.bot._was_preflop_aggressor = True
        self.bot._last_board_len = 3  # same street, no pot accumulation reset
        self.bot._ehs = lambda hole, board: 0.50
        self.bot._classify_board = lambda board: "DRY"
        action, amount = self.bot._decide(gs)
        # EHS 0.50 >= DRY c-bet threshold 0.35 -> should raise (c-bet)
        assert action == "raise", \
            f"Expected raise (c-bet via _postflop), got {action}"

    def test_decide_postflop_fold(self):
        """_decide -> _postflop -> _facing_bet -> fold when EHS far below req_eq."""
        gs = make_gs(call_amount=200, stack_size=1000, min_raise=200,
                     board_cards=DRY_FLOP, pot_size=300)
        self.bot._last_board_len = 3
        self.bot._ehs = lambda hole, board: 0.10
        self.bot._classify_board = lambda board: "DRY"
        action, amount = self.bot._decide(gs)
        # req_eq = 200 / (est_pot + 200). est_pot = pot_total + pot_size = 100 + 300 = 400
        # req_eq = 200 / 600 = 0.333. EHS 0.10 < 0.333 -> fold
        assert action == "fold" and amount == 0, \
            f"Expected (fold, 0), got ({action}, {amount})"

    def test_decide_postflop_call(self):
        """_decide -> _postflop -> _facing_bet -> call when EHS above req_eq but below MONSTER."""
        gs = make_gs(call_amount=50, stack_size=1000, min_raise=100,
                     board_cards=DRY_FLOP, pot_size=150)
        self.bot._last_board_len = 3
        self.bot._ehs = lambda hole, board: 0.45
        self.bot._classify_board = lambda board: "DRY"
        action, amount = self.bot._decide(gs)
        # est_pot = pot_total + pot_size = 100 + 150 = 250
        # req_eq = 50 / (250 + 50) = 50 / 300 = 0.167. EHS 0.45 >= 0.167 -> call
        # EHS 0.45 < 0.85 (MONSTER) -> not raise
        assert action == "call" and amount == 0, \
            f"Expected (call, 0), got ({action}, {amount})"

    def test_decide_preflop_unchanged(self):
        """_decide still routes to _preflop when board_cards is empty (regression test)."""
        gs = make_gs(call_amount=100, stack_size=1000, min_raise=200,
                     board_cards=[], pot_size=150,
                     hole_cards=[make_card("Ah"), make_card("Kh")])
        # Reset state for preflop
        self.bot._last_board_len = 0
        self.bot._pot_total = 0
        self.bot._street_pot = 0
        action, amount = self.bot._decide(gs)
        # AKs is a premium hand -> should not fold preflop
        assert action in ("call", "raise"), \
            f"Expected call or raise for AKs preflop, got {action}"

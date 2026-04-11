"""Postflop hand evaluator tests for HawkEyeBot.

Tests all 9 hand categories, relative ordering, kicker comparison,
wheel straight detection, 7-card evaluation via COMBO_INDICES,
Monte Carlo equity, draw detection, board texture, and EHS.
"""
import sys
import os
import types
import random

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
    """Build treys-encoded card integer from string like 'Ah', 'Ts', '2c'.

    rank_int: 0=2, 1=3, ..., 8=T, 9=J, 10=Q, 11=K, 12=A
    suit_int: 1=spades, 2=hearts, 4=diamonds, 8=clubs
    """
    rank_char = name[0]
    suit_char = name[1]
    rank_int = _RANK_MAP[rank_char]
    suit_int = _SUIT_MAP[suit_char]
    return (1 << rank_int << 16) | (suit_int << 12) | (rank_int << 8) | _PRIMES[rank_int]


class TestEvaluator:
    """Test _eval_5 for all 9 hand categories and ordering."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    # --- Category classification tests ---

    def test_straight_flush(self):
        """Royal flush (A-K-Q-J-T suited) returns tuple starting with (0, ...)"""
        cards = [make_card(c) for c in ["Ah", "Kh", "Qh", "Jh", "Th"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 0, f"Straight flush should have class 0, got {result}"

    def test_four_of_a_kind(self):
        """Four aces + kicker returns tuple starting with (1, ...)"""
        cards = [make_card(c) for c in ["Ah", "As", "Ad", "Ac", "Kh"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 1, f"Four of a kind should have class 1, got {result}"

    def test_full_house(self):
        """AAA-KK returns tuple starting with (2, ...)"""
        cards = [make_card(c) for c in ["Ah", "As", "Ad", "Kh", "Ks"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 2, f"Full house should have class 2, got {result}"

    def test_flush(self):
        """5 hearts non-straight returns tuple starting with (3, ...)"""
        cards = [make_card(c) for c in ["Ah", "Jh", "9h", "7h", "2h"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 3, f"Flush should have class 3, got {result}"

    def test_straight(self):
        """A-K-Q-J-T rainbow returns tuple starting with (4, ...)"""
        cards = [make_card(c) for c in ["Ah", "Ks", "Qd", "Jc", "Th"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 4, f"Straight should have class 4, got {result}"

    def test_three_of_a_kind(self):
        """Three aces + 2 kickers returns tuple starting with (5, ...)"""
        cards = [make_card(c) for c in ["Ah", "As", "Ad", "Kh", "Qs"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 5, f"Three of a kind should have class 5, got {result}"

    def test_two_pair(self):
        """AA-KK-Q kicker returns tuple starting with (6, ...)"""
        cards = [make_card(c) for c in ["Ah", "As", "Kh", "Ks", "Qd"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 6, f"Two pair should have class 6, got {result}"

    def test_pair(self):
        """Pair of aces + 3 kickers returns tuple starting with (7, ...)"""
        cards = [make_card(c) for c in ["Ah", "As", "Kd", "Qc", "Jh"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 7, f"One pair should have class 7, got {result}"

    def test_high_card(self):
        """A-K-Q-J-9 no flush no straight returns tuple starting with (8, ...)"""
        cards = [make_card(c) for c in ["Ah", "Ks", "Qd", "Jc", "9h"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 8, f"High card should have class 8, got {result}"

    # --- Wheel straight tests ---

    def test_wheel_straight(self):
        """A-2-3-4-5 rainbow returns tuple starting with (4, ...) NOT (8, ...)"""
        cards = [make_card(c) for c in ["Ah", "2s", "3d", "4c", "5h"]]
        result = self.bot._eval_5(cards)
        assert result[0] == 4, f"Wheel straight should have class 4, got {result}"

    def test_wheel_straight_flush(self):
        """A-2-3-4-5 suited returns (0, -3) -- 5-high straight flush"""
        cards = [make_card(c) for c in ["Ah", "2h", "3h", "4h", "5h"]]
        result = self.bot._eval_5(cards)
        assert result == (0, -3), f"Wheel straight flush should be (0, -3), got {result}"

    # --- Ordering tests (lower tuple = better hand) ---

    def test_straight_flush_beats_quads(self):
        sf = [make_card(c) for c in ["Ah", "Kh", "Qh", "Jh", "Th"]]
        quads = [make_card(c) for c in ["Ah", "As", "Ad", "Ac", "Kh"]]
        assert self.bot._eval_5(sf) < self.bot._eval_5(quads)

    def test_quads_beats_full_house(self):
        quads = [make_card(c) for c in ["Ah", "As", "Ad", "Ac", "Kh"]]
        fh = [make_card(c) for c in ["Ah", "As", "Ad", "Kh", "Ks"]]
        assert self.bot._eval_5(quads) < self.bot._eval_5(fh)

    def test_full_house_beats_flush(self):
        fh = [make_card(c) for c in ["Ah", "As", "Ad", "Kh", "Ks"]]
        flush = [make_card(c) for c in ["Ah", "Jh", "9h", "7h", "2h"]]
        assert self.bot._eval_5(fh) < self.bot._eval_5(flush)

    def test_flush_beats_straight(self):
        flush = [make_card(c) for c in ["Ah", "Jh", "9h", "7h", "2h"]]
        straight = [make_card(c) for c in ["Ah", "Ks", "Qd", "Jc", "Th"]]
        assert self.bot._eval_5(flush) < self.bot._eval_5(straight)

    def test_straight_beats_trips(self):
        straight = [make_card(c) for c in ["Ah", "Ks", "Qd", "Jc", "Th"]]
        trips = [make_card(c) for c in ["Ah", "As", "Ad", "Kh", "Qs"]]
        assert self.bot._eval_5(straight) < self.bot._eval_5(trips)

    def test_trips_beats_two_pair(self):
        trips = [make_card(c) for c in ["Ah", "As", "Ad", "Kh", "Qs"]]
        two_pair = [make_card(c) for c in ["Ah", "As", "Kh", "Ks", "Qd"]]
        assert self.bot._eval_5(trips) < self.bot._eval_5(two_pair)

    def test_two_pair_beats_pair(self):
        two_pair = [make_card(c) for c in ["Ah", "As", "Kh", "Ks", "Qd"]]
        pair = [make_card(c) for c in ["Ah", "As", "Kd", "Qc", "Jh"]]
        assert self.bot._eval_5(two_pair) < self.bot._eval_5(pair)

    def test_pair_beats_high_card(self):
        pair = [make_card(c) for c in ["Ah", "As", "Kd", "Qc", "Jh"]]
        high = [make_card(c) for c in ["Ah", "Ks", "Qd", "Jc", "9h"]]
        assert self.bot._eval_5(pair) < self.bot._eval_5(high)

    # --- Tiebreaker tests ---

    def test_higher_pair_wins(self):
        """AA pair < KK pair (better hand = lower tuple)"""
        aa = [make_card(c) for c in ["Ah", "As", "Kd", "Qc", "Jh"]]
        kk = [make_card(c) for c in ["Kh", "Ks", "Qd", "Jc", "9h"]]
        assert self.bot._eval_5(aa) < self.bot._eval_5(kk)

    def test_kicker_matters(self):
        """AA with K kicker < AA with Q kicker (K kicker is better)"""
        aa_k = [make_card(c) for c in ["Ah", "As", "Kd", "3c", "2h"]]
        aa_q = [make_card(c) for c in ["Ah", "As", "Qd", "3c", "2h"]]
        assert self.bot._eval_5(aa_k) < self.bot._eval_5(aa_q)


class TestEval7:
    """Test _eval_7 for 7-card evaluation using COMBO_INDICES."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_eval7_picks_best(self):
        """7 cards containing a flush among the 21 combos, _eval_7 returns flush rank."""
        # 5 hearts + 2 non-hearts -- the flush is hidden in the 7 cards
        cards = [
            make_card("Ah"), make_card("Jh"), make_card("9h"),
            make_card("7h"), make_card("2h"),
            make_card("Ks"), make_card("Qd")
        ]
        result = self.bot._eval_7(cards)
        assert result[0] == 3, f"Should find flush (class 3) in 7 cards, got {result}"

    def test_eval7_uses_combo_indices(self):
        """_eval_7 returns better rank than any single arbitrary 5-card subset."""
        # 7 cards: a pair of aces + assorted cards including a flush possibility
        cards = [
            make_card("Ah"), make_card("As"), make_card("Kh"),
            make_card("Qh"), make_card("Jh"), make_card("9h"),
            make_card("2d")
        ]
        # Best 5 should be the flush: Ah, Kh, Qh, Jh, 9h
        result = self.bot._eval_7(cards)
        # An arbitrary subset like first 5 might not be the best
        arbitrary = self.bot._eval_5(cards[:5])
        assert result <= arbitrary, "eval_7 should find a rank at least as good as arbitrary subset"

    def test_eval7_straight_in_7(self):
        """7 cards with embedded straight, _eval_7 finds it."""
        cards = [
            make_card("Ah"), make_card("Ks"), make_card("Qd"),
            make_card("Jc"), make_card("Th"), make_card("3s"),
            make_card("2d")
        ]
        result = self.bot._eval_7(cards)
        # Should find the broadway straight (A-K-Q-J-T)
        assert result[0] == 4, f"Should find straight (class 4) in 7 cards, got {result}"


# =====================================================================
# Phase 3, Plan 02: MC Equity, Draw Detection, Board Texture, EHS
# =====================================================================


class TestMCEquity:
    """Test _mc_equity Monte Carlo equity estimation (POST-02)."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_aa_high_equity(self):
        """AA on a random flop should have equity > 0.70."""
        random.seed(42)
        hole = [make_card("Ah"), make_card("As")]
        board = [make_card("7d"), make_card("3c"), make_card("9h")]
        eq = self.bot._mc_equity(hole, board)
        assert eq > 0.70, f"AA equity {eq} should be > 0.70"

    def test_72o_low_equity(self):
        """7h-2c on a random flop should have equity < 0.50."""
        random.seed(42)
        hole = [make_card("7h"), make_card("2c")]
        board = [make_card("Ks"), make_card("Td"), make_card("8h")]
        eq = self.bot._mc_equity(hole, board)
        assert eq < 0.50, f"72o equity {eq} should be < 0.50"

    def test_flop_iterations(self):
        """Flop (3 board cards) should use exactly 300 iterations."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("2d"), make_card("5c"), make_card("9s")]
        random.seed(42)
        eq = self.bot._mc_equity(hole, board)
        # Equity from 300 iterations is a multiple of 1/300 (or half-steps for ties)
        # Verify granularity: eq * 300 should be close to an integer or half-integer
        scaled = eq * 300
        remainder = scaled - round(scaled * 2) / 2
        assert abs(remainder) < 0.01, f"Flop equity {eq} not consistent with 300 iterations"

    def test_turn_iterations(self):
        """Turn (4 board cards) should use 400 iterations."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("2d"), make_card("5c"), make_card("9s"), make_card("Jh")]
        random.seed(42)
        eq = self.bot._mc_equity(hole, board)
        scaled = eq * 400
        remainder = scaled - round(scaled * 2) / 2
        assert abs(remainder) < 0.01, f"Turn equity {eq} not consistent with 400 iterations"

    def test_river_iterations(self):
        """River (5 board cards) should use 500 iterations."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("2d"), make_card("5c"), make_card("9s"), make_card("Jh"), make_card("3d")]
        random.seed(42)
        eq = self.bot._mc_equity(hole, board)
        scaled = eq * 500
        remainder = scaled - round(scaled * 2) / 2
        assert abs(remainder) < 0.01, f"River equity {eq} not consistent with 500 iterations"

    def test_equity_range(self):
        """Equity should always be between 0.0 and 1.0."""
        random.seed(42)
        hands = [
            ([make_card("Ah"), make_card("As")], [make_card("7d"), make_card("3c"), make_card("9h")]),
            ([make_card("7h"), make_card("2c")], [make_card("Ks"), make_card("Td"), make_card("8h")]),
            ([make_card("Kh"), make_card("Qh")], [make_card("Jh"), make_card("Th"), make_card("2d")]),
        ]
        for hole, board in hands:
            eq = self.bot._mc_equity(hole, board)
            assert 0.0 <= eq <= 1.0, f"Equity {eq} out of range [0.0, 1.0]"

    def test_no_duplicate_cards(self):
        """MC should never evaluate hands with duplicate cards (T-03-04 mitigation)."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("Qh"), make_card("Jh"), make_card("Th")]
        # If deck filtering works, this should run without error and produce valid equity
        random.seed(42)
        eq = self.bot._mc_equity(hole, board)
        assert 0.0 <= eq <= 1.0, f"MC with 5 known cards should still produce valid equity"

    def test_preflop_guard(self):
        """_mc_equity with empty board (len 0) should return 0.5 as guard clause."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = []
        eq = self.bot._mc_equity(hole, board)
        assert eq == 0.5, f"Preflop guard should return 0.5, got {eq}"


class TestDrawDetection:
    """Test _detect_draws draw type detection (POST-03)."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_flush_draw(self):
        """4 hearts in hole+board -> flush_draw=True."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("Qh"), make_card("7h"), make_card("2c")]
        result = self.bot._detect_draws(hole, board)
        assert result["flush_draw"] is True, f"Should detect flush draw, got {result}"

    def test_no_flush_draw(self):
        """Only 3 of one suit -> flush_draw=False."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("Qh"), make_card("7d"), make_card("2c")]
        result = self.bot._detect_draws(hole, board)
        assert result["flush_draw"] is False, f"Should not detect flush draw with only 3 suited, got {result}"

    def test_made_flush_not_draw(self):
        """5 hearts -> flush_draw=False (made flush, not a draw)."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("Qh"), make_card("7h"), make_card("2h")]
        result = self.bot._detect_draws(hole, board)
        assert result["flush_draw"] is False, f"Made flush should not be reported as draw, got {result}"

    def test_oesd(self):
        """8h-9c on Td-Jh-2s -> oesd=True (7 or Q completes)."""
        hole = [make_card("8h"), make_card("9c")]
        board = [make_card("Td"), make_card("Jh"), make_card("2s")]
        result = self.bot._detect_draws(hole, board)
        assert result["oesd"] is True, f"Should detect OESD (8-9-T-J), got {result}"

    def test_gutshot(self):
        """8h-Tc on Jd-Qh-2s -> gutshot=True (9 fills the gap)."""
        hole = [make_card("8h"), make_card("Tc")]
        board = [make_card("Jd"), make_card("Qh"), make_card("2s")]
        result = self.bot._detect_draws(hole, board)
        assert result["gutshot"] is True, f"Should detect gutshot (8-T-J-Q needs 9), got {result}"

    def test_no_straight_draw(self):
        """Disconnected ranks -> oesd=False, gutshot=False."""
        hole = [make_card("2h"), make_card("7c")]
        board = [make_card("Ks"), make_card("Ad"), make_card("4h")]
        result = self.bot._detect_draws(hole, board)
        assert result["oesd"] is False, f"Should not detect OESD with disconnected ranks"
        assert result["gutshot"] is False, f"Should not detect gutshot with disconnected ranks"

    def test_combo_draw(self):
        """Flush draw + OESD simultaneously -> combo_draw=True."""
        hole = [make_card("8h"), make_card("9h")]
        board = [make_card("Th"), make_card("Jh"), make_card("2c")]
        result = self.bot._detect_draws(hole, board)
        assert result["flush_draw"] is True, f"Should detect flush draw in combo"
        assert result["oesd"] is True, f"Should detect OESD in combo"
        assert result["combo_draw"] is True, f"Should detect combo draw, got {result}"

    def test_ace_low_oesd_is_not_oesd(self):
        """A-2-3-4 is only one-ended (needs 5 high, nothing below A) -> oesd=False."""
        hole = [make_card("Ah"), make_card("2c")]
        board = [make_card("3d"), make_card("4h"), make_card("Ks")]
        result = self.bot._detect_draws(hole, board)
        assert result["oesd"] is False, f"A-2-3-4 should NOT be OESD (one-ended), got {result}"

    def test_broadway_not_oesd(self):
        """J-Q-K-A is one-ended (nothing above A) -> oesd=False."""
        hole = [make_card("Jh"), make_card("Qc")]
        board = [make_card("Kd"), make_card("Ah"), make_card("2s")]
        result = self.bot._detect_draws(hole, board)
        assert result["oesd"] is False, f"J-Q-K-A should NOT be OESD (one-ended), got {result}"


class TestBoardTexture:
    """Test _classify_board board texture classification (POST-05)."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_paired_board(self):
        """Board with a pair -> 'PAIRED'."""
        board = [make_card("Ks"), make_card("Kh"), make_card("2d")]
        result = self.bot._classify_board(board)
        assert result == "PAIRED", f"Paired board should be 'PAIRED', got {result}"

    def test_dry_board(self):
        """Rainbow, disconnected -> 'DRY'."""
        board = [make_card("Ks"), make_card("7h"), make_card("2d")]
        result = self.bot._classify_board(board)
        assert result == "DRY", f"Rainbow disconnected board should be 'DRY', got {result}"

    def test_wet_board(self):
        """Monotone + connected -> 'WET'."""
        board = [make_card("9h"), make_card("Th"), make_card("Jh")]
        result = self.bot._classify_board(board)
        assert result == "WET", f"Monotone connected board should be 'WET', got {result}"

    def test_semi_wet_flush_possible(self):
        """Two-tone connected -> 'SEMI_WET' (connected only, flush needs 3+ of suit)."""
        board = [make_card("9h"), make_card("Th"), make_card("8d")]
        result = self.bot._classify_board(board)
        # Ranks 6(8), 7(9), 8(T) span=2, connected=True. Only 2 hearts = flush_possible=False.
        # So this is SEMI_WET (connected only).
        assert result == "SEMI_WET", f"Connected two-tone board should be 'SEMI_WET', got {result}"

    def test_semi_wet_connected(self):
        """Rainbow but connected -> 'SEMI_WET'."""
        board = [make_card("9s"), make_card("Th"), make_card("Jd")]
        result = self.bot._classify_board(board)
        assert result == "SEMI_WET", f"Rainbow connected board should be 'SEMI_WET', got {result}"

    def test_paired_takes_priority(self):
        """Paired board with flush draw -> still 'PAIRED'."""
        board = [make_card("Kh"), make_card("Ks"), make_card("Qh")]
        result = self.bot._classify_board(board)
        assert result == "PAIRED", f"Paired board should always be 'PAIRED', got {result}"


class TestEHS:
    """Test _ehs Effective Hand Strength combining equity + draw bonus (POST-04)."""

    def setup_method(self):
        self.bot = HawkEyeBot()

    def test_ehs_no_draw(self):
        """On river (5 board cards), EHS equals mc_equity (no draw bonus)."""
        random.seed(42)
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("2d"), make_card("5c"), make_card("9s"), make_card("Jd"), make_card("3c")]
        eq = self.bot._mc_equity(hole, board)
        random.seed(42)
        ehs = self.bot._ehs(hole, board)
        assert abs(ehs - eq) < 0.001, f"River EHS {ehs} should equal mc_equity {eq}"

    def test_ehs_flush_draw_bonus(self):
        """On flop with flush draw, EHS = mc_equity + 0.06."""
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("Qh"), make_card("7h"), make_card("2c")]
        random.seed(42)
        eq = self.bot._mc_equity(hole, board)
        random.seed(42)
        ehs = self.bot._ehs(hole, board)
        expected = min(eq + 0.06, 1.0)
        assert abs(ehs - expected) < 0.001, f"EHS {ehs} should be mc_equity {eq} + 0.06 = {expected}"

    def test_ehs_oesd_bonus(self):
        """On flop with OESD, EHS = mc_equity + 0.05."""
        hole = [make_card("8h"), make_card("9c")]
        board = [make_card("Td"), make_card("Jh"), make_card("2s")]
        random.seed(42)
        eq = self.bot._mc_equity(hole, board)
        random.seed(42)
        ehs = self.bot._ehs(hole, board)
        expected = min(eq + 0.05, 1.0)
        assert abs(ehs - expected) < 0.001, f"EHS {ehs} should be mc_equity {eq} + 0.05 = {expected}"

    def test_ehs_gutshot_bonus(self):
        """On flop with gutshot, EHS = mc_equity + 0.03."""
        hole = [make_card("8h"), make_card("Tc")]
        board = [make_card("Jd"), make_card("Qh"), make_card("2s")]
        random.seed(42)
        eq = self.bot._mc_equity(hole, board)
        random.seed(42)
        ehs = self.bot._ehs(hole, board)
        expected = min(eq + 0.03, 1.0)
        assert abs(ehs - expected) < 0.001, f"EHS {ehs} should be mc_equity {eq} + 0.03 = {expected}"

    def test_ehs_combo_draw_bonus(self):
        """On flop with combo draw (flush + OESD), EHS = mc_equity + 0.09."""
        hole = [make_card("8h"), make_card("9h")]
        board = [make_card("Th"), make_card("Jh"), make_card("2c")]
        random.seed(42)
        eq = self.bot._mc_equity(hole, board)
        random.seed(42)
        ehs = self.bot._ehs(hole, board)
        expected = min(eq + 0.09, 1.0)
        assert abs(ehs - expected) < 0.001, f"EHS {ehs} should be mc_equity {eq} + 0.09 = {expected}"

    def test_ehs_capped_at_one(self):
        """High equity + draw bonus should not exceed 1.0."""
        # AA on flush draw board -- equity already high, bonus should cap at 1.0
        random.seed(42)
        hole = [make_card("Ah"), make_card("Kh")]
        board = [make_card("Qh"), make_card("Jh"), make_card("2c")]
        ehs = self.bot._ehs(hole, board)
        assert ehs <= 1.0, f"EHS {ehs} should never exceed 1.0"

    def test_ehs_returns_float(self):
        """_ehs returns a float between 0.0 and 1.0."""
        random.seed(42)
        hole = [make_card("7h"), make_card("2c")]
        board = [make_card("Ks"), make_card("Td"), make_card("8h")]
        ehs = self.bot._ehs(hole, board)
        assert isinstance(ehs, float), f"EHS should be a float, got {type(ehs)}"
        assert 0.0 <= ehs <= 1.0, f"EHS {ehs} should be in [0.0, 1.0]"

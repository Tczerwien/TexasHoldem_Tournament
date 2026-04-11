"""Postflop hand evaluator tests for HawkEyeBot.

Tests all 9 hand categories, relative ordering, kicker comparison,
wheel straight detection, and 7-card evaluation via COMBO_INDICES.
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

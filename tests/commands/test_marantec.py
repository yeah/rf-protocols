"""Tests for the Marantec RF command encoder.

Ground-truth timing fixtures are derived from the reference Flipper Zero
encoder (lib/subghz/protocols/marantec.c) for the documented sample keys,
including the unit-test key from Flipper's marantec.sub resource.
"""

from rf_protocols.commands.marantec import MarantecCommand

# Flipper marantec.sub unit-test key: 00 01 30 07 10 DF 86 9F -> 0x1300710DF869F
_TEST_KEY = 0x1300710DF869F

# Expected signed-microsecond timings for _TEST_KEY, generated from the
# reference Manchester encoder (mark-first, 49 half-bits merged, trailing gap).
_EXPECTED_TEST_KEY = [
    2000, -1000, 1000, -2000, 1000, -1000, 2000, -1000, 1000, -1000,
    1000, -1000, 1000, -1000, 1000, -1000, 1000, -1000, 1000, -1000,
    1000, -1000, 1000, -2000, 1000, -1000, 1000, -1000, 2000, -1000,
    1000, -1000, 1000, -2000, 2000, -1000, 1000, -1000, 1000, -1000,
    1000, -2000, 1000, -1000, 2000, -2000, 1000, -1000, 1000, -1000,
    1000, -1000, 1000, -1000, 1000, -1000, 2000, -1000, 1000, -1000,
    1000, -1000, 1000, -2000, 1000, -1000, 2000, -2000, 2000, -1000,
    1000, -2000, 1000, -1000, 1000, -1000, 1000, -1000, 1000, -1000,
    1000, -10000,
]


def test_marantec_defaults() -> None:
    """Default frequency, modulation and repeat are set correctly."""
    command = MarantecCommand(code=_TEST_KEY)
    assert command.frequency == 868_350_000
    assert command.modulation == "OOK"
    assert command.repeat_count == 3


def test_marantec_timings_match_reference() -> None:
    """Encoded timings match the reference Flipper output for the test key."""
    command = MarantecCommand(code=_TEST_KEY)
    assert command.get_raw_timings() == _EXPECTED_TEST_KEY


def test_marantec_timings_strictly_alternate() -> None:
    """Output strictly alternates between positive and negative durations."""
    timings = MarantecCommand(code=_TEST_KEY).get_raw_timings()
    for first, second in zip(timings, timings[1:]):
        assert (first > 0) != (second > 0)


def test_marantec_starts_with_mark() -> None:
    """The frame begins with a positive (mark) duration as required."""
    timings = MarantecCommand(code=_TEST_KEY).get_raw_timings()
    assert timings[0] > 0


def test_marantec_trailing_inter_frame_gap() -> None:
    """The frame ends with the inter-frame gap of te_long * 5."""
    timings = MarantecCommand(code=_TEST_KEY).get_raw_timings()
    assert timings[-1] == -10000


def test_marantec_custom_frequency() -> None:
    """The 433.92 MHz variant frequency is honored."""
    command = MarantecCommand(code=_TEST_KEY, frequency=433_920_000)
    assert command.frequency == 433_920_000


def test_marantec_rejects_oversized_code() -> None:
    """A code wider than 49 bits raises ValueError."""
    try:
        MarantecCommand(code=1 << 49)
    except ValueError:
        return
    raise AssertionError("expected ValueError for 50-bit code")

"""Tests for the Marantec RF command encoder."""

from itertools import pairwise

import pytest

from rf_protocols import ModulationType, RadioFrequencyCommand
from rf_protocols.commands.marantec import MarantecCommand

_TEST_KEY = 0x1300710DF869F

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


def test_marantec_command_rf_parameters() -> None:
    """MarantecCommand stores expected RF command metadata."""
    command = MarantecCommand(code=_TEST_KEY)
    assert command.frequency == 868_350_000
    assert command.modulation == ModulationType.OOK
    assert command.repeat_count == 4
    assert command.symbol_rate is None
    assert command.output_power is None


def test_marantec_command_is_radio_frequency_command() -> None:
    """MarantecCommand is a RadioFrequencyCommand subclass."""
    command = MarantecCommand(code=_TEST_KEY)
    assert isinstance(command, RadioFrequencyCommand)


def test_marantec_command_stores_code() -> None:
    """Constructor stores the code on the command."""
    command = MarantecCommand(code=_TEST_KEY)
    assert command.code == _TEST_KEY


def test_marantec_timings_match_reference() -> None:
    """Encoded timings match the reference Flipper output for the test key."""
    command = MarantecCommand(code=_TEST_KEY)
    assert command.get_raw_timings() == _EXPECTED_TEST_KEY


def test_marantec_timings_strictly_alternate() -> None:
    """Output strictly alternates between positive and negative durations."""
    timings = MarantecCommand(code=_TEST_KEY).get_raw_timings()
    for first, second in pairwise(timings):
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


def test_marantec_code_affects_timings() -> None:
    """Different codes produce different encoded timings."""
    first = MarantecCommand(code=_TEST_KEY).get_raw_timings()
    second = MarantecCommand(code=0x1307EDF6486C5).get_raw_timings()
    assert first != second


@pytest.mark.parametrize("code", [-1, 1 << 49])
def test_marantec_command_rejects_invalid_code(code: int) -> None:
    """Constructor rejects codes outside the 49-bit range."""
    with pytest.raises(ValueError, match="code"):
        MarantecCommand(code=code)

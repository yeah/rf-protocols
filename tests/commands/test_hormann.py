"""Tests for the Hörmann RF command encoder."""

from itertools import pairwise

import pytest

from rf_protocols import ModulationType, RadioFrequencyCommand
from rf_protocols.commands.hormann import HormannCommand

_TEST_KEY = 0xFF0F1234563


def test_hormann_command_rf_parameters() -> None:
    """HormannCommand stores expected RF command metadata."""
    command = HormannCommand(code=_TEST_KEY)
    assert command.frequency == 868_300_000
    assert command.modulation == ModulationType.OOK
    assert command.repeat_count == 10
    assert command.symbol_rate is None
    assert command.output_power is None


def test_hormann_command_is_radio_frequency_command() -> None:
    """HormannCommand is a RadioFrequencyCommand subclass."""
    assert isinstance(HormannCommand(code=_TEST_KEY), RadioFrequencyCommand)


def test_hormann_command_stores_code() -> None:
    """Constructor stores the code on the command."""
    assert HormannCommand(code=_TEST_KEY).code == _TEST_KEY


def test_hormann_timings_structure() -> None:
    """Output is the sync pair followed by 44 bit pairs."""
    timings = HormannCommand(code=_TEST_KEY).get_raw_timings()
    assert len(timings) == 2 + 44 * 2


def test_hormann_timings_start_with_sync_mark() -> None:
    """The frame begins with the long sync mark and a short space."""
    timings = HormannCommand(code=_TEST_KEY).get_raw_timings()
    assert timings[0] == 12000
    assert timings[1] == -500


def test_hormann_timings_strictly_alternate() -> None:
    """Output strictly alternates between positive and negative durations."""
    timings = HormannCommand(code=_TEST_KEY).get_raw_timings()
    for first, second in pairwise(timings):
        assert (first > 0) != (second > 0)


def test_hormann_timings_end_on_space() -> None:
    """The frame ends on a space so repeats concatenate cleanly."""
    timings = HormannCommand(code=_TEST_KEY).get_raw_timings()
    assert timings[-1] < 0


def test_hormann_bit_encoding() -> None:
    """Bit 1 encodes as long/short mark, bit 0 as short/long mark."""
    # 0xFF0F1234563: MSB (bit 43) is 1, so first data pair is long mark/short.
    timings = HormannCommand(code=_TEST_KEY).get_raw_timings()
    assert timings[2:4] == [1000, -500]


def test_hormann_custom_frequency() -> None:
    """The 433.92 MHz variant frequency is honored."""
    command = HormannCommand(code=_TEST_KEY, frequency=433_920_000)
    assert command.frequency == 433_920_000


def test_hormann_code_affects_timings() -> None:
    """Different codes produce different encoded timings."""
    first = HormannCommand(code=_TEST_KEY).get_raw_timings()
    second = HormannCommand(code=0xFF0F1234564).get_raw_timings()
    assert first != second


@pytest.mark.parametrize("code", [-1, 1 << 44])
def test_hormann_command_rejects_invalid_code(code: int) -> None:
    """Constructor rejects codes outside the 44-bit range."""
    with pytest.raises(ValueError, match="code"):
        HormannCommand(code=code)

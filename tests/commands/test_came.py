"""Tests for the CAME RF command encoder."""

from itertools import pairwise

import pytest

from rf_protocols import ModulationType, RadioFrequencyCommand
from rf_protocols.commands.came import CameCommand

_TEST_KEY_12 = 0xB35
_TEST_KEY_24 = 0xABC123


def test_came_command_rf_parameters() -> None:
    """CameCommand stores expected RF command metadata."""
    command = CameCommand(code=_TEST_KEY_12)
    assert command.frequency == 433_920_000
    assert command.modulation == ModulationType.OOK
    assert command.repeat_count == 10
    assert command.symbol_rate is None
    assert command.output_power is None


def test_came_command_is_radio_frequency_command() -> None:
    """CameCommand is a RadioFrequencyCommand subclass."""
    assert isinstance(CameCommand(code=_TEST_KEY_12), RadioFrequencyCommand)


def test_came_command_stores_code() -> None:
    """Constructor stores the code and bit count on the command."""
    command = CameCommand(code=_TEST_KEY_24, bit_count=24)
    assert command.code == _TEST_KEY_24
    assert command.bit_count == 24


def test_came_timings_structure_12bit() -> None:
    """12-bit output is the start mark, 12 bit pairs, and header low."""
    timings = CameCommand(code=_TEST_KEY_12).get_raw_timings()
    assert len(timings) == 1 + 12 * 2 + 1


def test_came_timings_structure_24bit() -> None:
    """24-bit output is the start mark, 24 bit pairs, and header low."""
    timings = CameCommand(code=_TEST_KEY_24, bit_count=24).get_raw_timings()
    assert len(timings) == 1 + 24 * 2 + 1


def test_came_timings_start_with_mark() -> None:
    """The frame begins with the short start mark."""
    timings = CameCommand(code=_TEST_KEY_12).get_raw_timings()
    assert timings[0] == 320


def test_came_timings_strictly_alternate() -> None:
    """Output strictly alternates between positive and negative durations."""
    timings = CameCommand(code=_TEST_KEY_24, bit_count=24).get_raw_timings()
    for first, second in pairwise(timings):
        assert (first > 0) != (second > 0)


def test_came_timings_end_on_header_low() -> None:
    """The frame ends on the header low sized by bit count."""
    assert CameCommand(code=_TEST_KEY_12).get_raw_timings()[-1] == -320 * 47
    assert (
        CameCommand(code=_TEST_KEY_24, bit_count=24).get_raw_timings()[-1] == -320 * 76
    )


def test_came_bit_encoding() -> None:
    """Bit 1 encodes as long space/short mark, bit 0 as short space/long mark."""
    # 0xB35 = 1011 0011 0101: MSB (bit 11) is 1, so first data pair is long/short.
    timings = CameCommand(code=_TEST_KEY_12).get_raw_timings()
    assert timings[1:3] == [-640, 320]


def test_came_custom_frequency() -> None:
    """The 315 MHz variant frequency is honored."""
    command = CameCommand(code=_TEST_KEY_12, frequency=315_000_000)
    assert command.frequency == 315_000_000


def test_came_code_affects_timings() -> None:
    """Different codes produce different encoded timings."""
    first = CameCommand(code=_TEST_KEY_12).get_raw_timings()
    second = CameCommand(code=0x123).get_raw_timings()
    assert first != second


@pytest.mark.parametrize("bit_count", [8, 16, 32])
def test_came_rejects_invalid_bit_count(bit_count: int) -> None:
    """Constructor rejects bit counts other than 12 or 24."""
    with pytest.raises(ValueError, match="bit_count"):
        CameCommand(code=0x1, bit_count=bit_count)


def test_came_rejects_oversized_code() -> None:
    """Constructor rejects a code that does not fit in bit_count bits."""
    with pytest.raises(ValueError, match="bit_count bits"):
        CameCommand(code=1 << 12, bit_count=12)

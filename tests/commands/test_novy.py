"""Tests for Novy cooker-hood command encoding."""

import pytest

from rf_protocols import ModulationType, RadioFrequencyCommand
from rf_protocols.codes.novy.cooker_hood import NovyCookerHoodButton
from rf_protocols.commands.novy import NovyCookerHoodCommand


def test_novy_command_rf_parameters() -> None:
    """NovyCookerHoodCommand stores expected RF command metadata."""
    cmd = NovyCookerHoodCommand(channel=1, key=0x2C, key_width=8)
    assert cmd.frequency == 433_920_000
    assert cmd.modulation == ModulationType.OOK
    assert cmd.repeat_count == 5
    assert cmd.symbol_rate is None
    assert cmd.output_power is None


def test_novy_command_is_radio_frequency_command() -> None:
    """NovyCookerHoodCommand is a RadioFrequencyCommand subclass."""
    cmd = NovyCookerHoodCommand(channel=1, key=0x2C, key_width=8)
    assert isinstance(cmd, RadioFrequencyCommand)


@pytest.mark.parametrize("channel", [0, 11, -1])
def test_novy_command_rejects_invalid_channel(channel: int) -> None:
    """Channel must be in range 1..10."""
    with pytest.raises(ValueError, match="channel"):
        NovyCookerHoodCommand(channel=channel, key=0x2C, key_width=8)


@pytest.mark.parametrize(
    ("key", "key_width"),
    [(0x4, 2), (-1, 2), (0x100, 8), (-1, 8)],
)
def test_novy_command_rejects_oversized_key(key: int, key_width: int) -> None:
    """key must fit within key_width bits."""
    with pytest.raises(ValueError, match="key"):
        NovyCookerHoodCommand(channel=1, key=key, key_width=key_width)


def test_novy_command_encodes_channel_1_power() -> None:
    """Channel 1 + power produces the expected PWM frame."""
    cmd = NovyCookerHoodCommand(channel=1, key=0x2C, key_width=8, timebase_us=360)
    short = 360
    long_ = 720
    bits = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0]
    expected: list[int] = [short]
    for bit in bits:
        expected += [-short, long_] if bit else [-long_, short]
    expected.append(-10_000)
    assert cmd.get_raw_timings() == expected


def test_novy_command_encodes_12_bit_frame() -> None:
    """A 2-bit key produces a 12-bit frame."""
    cmd = NovyCookerHoodCommand(channel=1, key=0x2, key_width=2, timebase_us=360)
    timings = cmd.get_raw_timings()
    # 1 leading mark + 12 bits * 2 timings + 1 trailing gap = 26 timings.
    assert len(timings) == 26


def test_novy_command_encodes_18_bit_frame() -> None:
    """An 8-bit key produces an 18-bit frame."""
    cmd = NovyCookerHoodCommand(channel=1, key=0x2C, key_width=8, timebase_us=360)
    timings = cmd.get_raw_timings()
    # 1 leading mark + 18 bits * 2 timings + 1 trailing gap = 38 timings.
    assert len(timings) == 38


@pytest.mark.parametrize("channel", range(1, 11))
def test_novy_command_encodes_every_channel(channel: int) -> None:
    """Every supported channel produces a valid frame."""
    cmd = NovyCookerHoodCommand(channel=channel, key=0x2C, key_width=8)
    timings = cmd.get_raw_timings()
    assert len(timings) == 38
    assert timings[-1] == -10_000


def test_novy_button_to_command_uses_button_code_and_width() -> None:
    """NovyCookerHoodButton.to_command builds a command with the button's code."""
    cmd = NovyCookerHoodButton.POWER.to_command(channel=1)
    assert isinstance(cmd, NovyCookerHoodCommand)
    assert cmd.channel == 1
    assert cmd.key == 0x2C
    assert cmd.key_width == 8


@pytest.mark.parametrize(
    ("button", "expected_width"),
    [
        (NovyCookerHoodButton.MINUS, 2),
        (NovyCookerHoodButton.PLUS, 2),
        (NovyCookerHoodButton.AMBIENT, 2),
        (NovyCookerHoodButton.POWER, 8),
        (NovyCookerHoodButton.LIGHT, 8),
        (NovyCookerHoodButton.LIGHT_MINUS, 8),
        (NovyCookerHoodButton.LIGHT_PLUS, 8),
        (NovyCookerHoodButton.AMBIENT_MINUS, 8),
        (NovyCookerHoodButton.AMBIENT_PLUS, 8),
        (NovyCookerHoodButton.MINUS_PLUS, 8),
    ],
)
def test_novy_button_width(
    button: NovyCookerHoodButton, expected_width: int
) -> None:
    """Each button declares the expected frame width."""
    assert button.width == expected_width

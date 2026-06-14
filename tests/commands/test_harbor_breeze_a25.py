"""Tests for Harbor Breeze A25 RF command encoding."""

import pytest

from rf_protocols import ModulationType, RadioFrequencyCommand
from rf_protocols.codes.harbor_breeze.a25 import HarborBreezeA25Button
from rf_protocols.commands.harbor_breeze_a25 import HarborBreezeA25Command

_BUNDLED_ADDRESS = 0b1101010111111


def _normalize_timings(timings: list[int]) -> str:
    symbols: list[str] = []
    for timing in timings:
        magnitude = abs(timing)
        if magnitude > 5_000:
            symbols.append("G")
        elif magnitude >= 700:
            symbols.append("L")
        else:
            symbols.append("S")
    return "".join(symbols)


def _decode_pair_bits(frame: str) -> tuple[str, str, str, str]:
    pairs = [frame[index : index + 2] for index in range(3, 49, 2)]
    pair_bits = {
        "LS": "0",
        "SL": "1",
    }
    bits = "".join(pair_bits[pair] for pair in pairs)
    return bits[:13], bits[13:15], bits[15:21], bits[21:23]


def test_harbor_breeze_a25_button_values() -> None:
    """Harbor Breeze button enum exposes the decoded 6-bit command values."""
    assert HarborBreezeA25Button.LIGHT == 0b011010
    assert HarborBreezeA25Button.POWER == 0b111110
    assert HarborBreezeA25Button.FAN_1 == 0b011110
    assert HarborBreezeA25Button.TIMER_8H == 0b001011


def test_harbor_breeze_a25_command_rf_parameters() -> None:
    """Harbor Breeze A25 uses fixed 315 MHz OOK timings."""
    cmd = HarborBreezeA25Command(address=_BUNDLED_ADDRESS, command=0b011010)
    assert cmd.frequency == 315_000_000
    assert cmd.modulation == ModulationType.OOK
    assert cmd.repeat_count == 0
    assert cmd.symbol_rate is None
    assert cmd.output_power is None


def test_harbor_breeze_a25_command_is_radio_frequency_command() -> None:
    """Harbor Breeze command implements the shared RF base class."""
    cmd = HarborBreezeA25Command(address=_BUNDLED_ADDRESS, command=0b011010)
    assert isinstance(cmd, RadioFrequencyCommand)


def test_harbor_breeze_a25_command_frame_layout() -> None:
    """The payload is encoded as prefix + 13-bit address + fixed + 6-bit command."""
    cmd = HarborBreezeA25Command(address=0x123, command=0b100101)
    timings = cmd.get_raw_timings()

    assert len(timings) == 300

    first_frame = _normalize_timings(timings[:50])
    address_bits, fixed_prefix_bits, command_bits, fixed_suffix_bits = (
        _decode_pair_bits(first_frame)
    )

    assert first_frame[:3] == "SLS"
    assert first_frame[-1] == "G"
    assert address_bits == format(0x123, "013b")
    assert fixed_prefix_bits == "00"
    assert command_bits == "100101"
    assert fixed_suffix_bits == "10"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"address": -1, "command": 0}, "address"),
        ({"address": 1 << 13, "command": 0}, "address"),
        ({"address": 0, "command": -1}, "command"),
        ({"address": 0, "command": 1 << 6}, "command"),
    ],
)
def test_harbor_breeze_a25_command_rejects_invalid_parameters(
    kwargs: dict[str, int],
    message: str,
) -> None:
    """Constructor rejects out-of-range address and command values."""
    with pytest.raises(ValueError, match=message):
        HarborBreezeA25Command(**kwargs)


def test_harbor_breeze_a25_button_to_command() -> None:
    """Buttons build the corresponding parameterized Harbor Breeze command."""
    cmd = HarborBreezeA25Button.FAN_3.to_command(address=_BUNDLED_ADDRESS)
    assert isinstance(cmd, HarborBreezeA25Command)
    assert cmd.address == _BUNDLED_ADDRESS
    assert cmd.command == HarborBreezeA25Button.FAN_3


def test_harbor_breeze_a25_command_address_affects_timings() -> None:
    """Changing the address changes the encoded transmission."""
    base = {"command": HarborBreezeA25Button.LIGHT}
    timings_a = HarborBreezeA25Command(**base, address=0).get_raw_timings()
    timings_b = HarborBreezeA25Command(
        **base,
        address=_BUNDLED_ADDRESS,
    ).get_raw_timings()
    assert timings_a != timings_b


def test_harbor_breeze_a25_command_command_affects_timings() -> None:
    """Changing the command changes the encoded transmission."""
    base = {"address": _BUNDLED_ADDRESS}
    timings_a = HarborBreezeA25Command(
        **base,
        command=HarborBreezeA25Button.LIGHT,
    ).get_raw_timings()
    timings_b = HarborBreezeA25Command(
        **base,
        command=HarborBreezeA25Button.POWER,
    ).get_raw_timings()
    assert timings_a != timings_b

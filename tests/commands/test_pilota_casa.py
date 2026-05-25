"""Tests for Pilota Casa PWM command encoding."""

import pytest

from rf_protocols import ModulationType, RadioFrequencyCommand
from rf_protocols.commands.pilota_casa import PilotaCasaCommand


def test_pilota_casa_command_rf_parameters() -> None:
	"""PilotaCasaCommand stores expected RF command metadata."""
	cmd = PilotaCasaCommand(id=12345, group=1, channel=1, on=True)
	assert cmd.frequency == 433_920_000
	assert cmd.modulation == ModulationType.OOK
	assert cmd.repeat_count == 5
	assert cmd.symbol_rate is None
	assert cmd.output_power is None


def test_pilota_casa_command_is_radio_frequency_command() -> None:
	"""PilotaCasaCommand is a RadioFrequencyCommand subclass."""
	cmd = PilotaCasaCommand(id=12345, group=1, channel=1, on=True)
	assert isinstance(cmd, RadioFrequencyCommand)


def test_pilota_casa_command_stores_parameters() -> None:
	"""Constructor parameters are stored on the command."""
	cmd = PilotaCasaCommand(id=54321, group=3, channel=2, on=False)
	assert cmd.id == 54321
	assert cmd.group == 3
	assert cmd.channel == 2
	assert cmd.on is False


def test_pilota_casa_command_id_validation() -> None:
	"""ID must be 16-bit (0..65535)."""
	# Valid boundary cases
	PilotaCasaCommand(id=0, group=0, channel=0, on=True)
	PilotaCasaCommand(id=65535, group=1, channel=1, on=True)

	# Invalid cases
	with pytest.raises(ValueError, match="id must be in range"):
		PilotaCasaCommand(id=-1, group=1, channel=1, on=True)
	with pytest.raises(ValueError, match="id must be in range"):
		PilotaCasaCommand(id=65536, group=1, channel=1, on=True)


def test_pilota_casa_command_group_validation() -> None:
	"""Group must be 0..4."""
	# Valid boundary cases
	PilotaCasaCommand(id=0, group=0, channel=0, on=True)
	PilotaCasaCommand(id=0, group=4, channel=3, on=True)

	# Invalid cases
	with pytest.raises(ValueError, match="group must be in range"):
		PilotaCasaCommand(id=0, group=-1, channel=1, on=True)
	with pytest.raises(ValueError, match="group must be in range"):
		PilotaCasaCommand(id=0, group=5, channel=1, on=True)


def test_pilota_casa_command_channel_validation() -> None:
	"""Channel must be 0..4 with specific group combinations."""
	# Valid combinations
	PilotaCasaCommand(id=0, group=0, channel=0, on=True)
	PilotaCasaCommand(id=0, group=1, channel=1, on=True)
	PilotaCasaCommand(id=0, group=2, channel=3, on=True)

	# Invalid cases
	with pytest.raises(ValueError, match="channel must be in range"):
		PilotaCasaCommand(id=0, group=1, channel=-1, on=True)
	with pytest.raises(ValueError, match="channel must be in range"):
		PilotaCasaCommand(id=0, group=1, channel=5, on=True)
	
	# Invalid combinations (not in lookup table)
	with pytest.raises(ValueError, match="Invalid group/channel/on combination"):
		PilotaCasaCommand(id=0, group=1, channel=0, on=True)


def test_pilota_casa_command_valid_combinations() -> None:
	"""Valid group/channel/on combinations from lookup table."""
	# Single device, group 1, channel 1, on
	PilotaCasaCommand(id=0, group=1, channel=1, on=True)
	# Group 2, channel 3, off
	PilotaCasaCommand(id=0, group=2, channel=3, on=False)
	# All groups/channels, on
	PilotaCasaCommand(id=0, group=0, channel=0, on=True)


def test_pilota_casa_command_timings_structure() -> None:
	"""Generated timings have correct structure."""
	cmd = PilotaCasaCommand(id=12345, group=1, channel=1, on=True, timebase_us=600)
	timings = cmd.get_raw_timings()

	# Now 66 timings: 33 symbol pairs (32 bits + pause)
	assert len(timings) == 66

	# Alternating positive (high) and negative (low)
	for i, timing in enumerate(timings):
		if i % 2 == 0:
			assert timing > 0, f"Even index {i} should be positive (high)"
		else:
			assert timing < 0, f"Odd index {i} should be negative (low)"


def test_pilota_casa_command_group1_channel1_on() -> None:
	"""Test group 1, channel 1 on command."""
	cmd = PilotaCasaCommand(id=47113, group=1, channel=1, on=True, timebase_us=600)
	timings = cmd.get_raw_timings()
	assert len(timings) == 66

	# Device type: 01 (bit "0" at index 0, bit "1" at index 1)
	# Bit 0 -> [1200, -600]
	assert timings[0] == 1200
	assert timings[1] == -600
	# Bit 1 -> [600, -1200]
	assert timings[2] == 600
	assert timings[3] == -1200


def test_pilota_casa_command_group_all_on() -> None:
	"""Test all groups/channels on command."""
	cmd = PilotaCasaCommand(id=47113, group=0, channel=0, on=True, timebase_us=600)
	timings = cmd.get_raw_timings()

	# Device type: 01
	assert timings[0:4] == [1200, -600, 600, -1200]


def test_pilota_casa_command_on_off() -> None:
	"""Test on/off bit encoding."""
	cmd_on = PilotaCasaCommand(id=47113, group=0, channel=0, on=True, timebase_us=600)
	cmd_off = PilotaCasaCommand(id=47113, group=0, channel=0, on=False, timebase_us=600)

	timings_on = cmd_on.get_raw_timings()
	timings_off = cmd_off.get_raw_timings()

	# Compare on and off timings
	# Both use lookup table, so pattern at positions 4-15 (6-bit code) should differ
	assert timings_on != timings_off


def test_pilota_casa_command_always_one_suffix() -> None:
	"""Last 8 bits are always 1."""
	cmd = PilotaCasaCommand(id=12345, group=1, channel=3, on=False, timebase_us=600)
	timings = cmd.get_raw_timings()

	# Last 8 symbols (16 timing values)
	# All bits are 1, so all symbols are [600, -1200]
	for i in range(48, 64, 2):
		assert timings[i] == 600, f"Bit at index {i} should be 600 (bit 1)"
		assert timings[i + 1] == -1200, f"Bit at index {i + 1} should be -1200 (bit 1)"
	# Final pause
	assert timings[64] == 600
	assert timings[65] == -6600

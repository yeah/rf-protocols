"""Marantec garage door / gate RF command definitions.

Marantec openers (e.g. Comfort / Digital series) use a static 49-bit OOK
protocol, Manchester-encoded. Unlike rolling-code systems the transmitted
code is fixed per remote, so a code learned once (for example with a Flipper
Zero, which reports it as a 49-bit ``Key``) remains valid indefinitely.

The 49-bit value embeds a constant prefix, a serial number, a button nibble, a
constant byte and a CRC-8 (polynomial ``0x1D``, init ``0x01``). This encoder
transmits a supplied 49-bit code verbatim; the field decomposition is not
required to reproduce a captured remote and is intentionally not exposed yet.

Protocol reference: Flipper Zero ``lib/subghz/protocols/marantec.c``.
"""

from __future__ import annotations

from typing import override

from . import ModulationType, RadioFrequencyCommand

# Marantec EU openers operate at 868.35 MHz; some variants use 433.92 MHz.
# rf_protocols repeat_count is the number of *additional* transmissions; the
# transmitter sends repeat_count + 1 frames total. Flipper sends ~4 frames.
_MARANTEC_FREQUENCY = 868_350_000
_MARANTEC_REPEAT_COUNT = 3

_TE_SHORT = 1000
_TE_LONG = 2000
_HEADER_LOW = _TE_LONG * 5

_BIT_COUNT = 49


class MarantecCommand(RadioFrequencyCommand):
    """Marantec static-code garage door / gate command.

    Transmits a 49-bit Marantec code, Manchester-encoded over OOK. The code is
    the value reported by a capture tool such as a Flipper Zero.
    """

    code: int

    def __init__(
        self,
        *,
        code: int,
        frequency: int = _MARANTEC_FREQUENCY,
    ) -> None:
        """Initialize the Marantec command.

        Args:
            code: 49-bit Marantec code (0..2**49-1), as captured from a remote.
            frequency: RF frequency in Hz (868.35 MHz default; 433.92 MHz for
                some variants).
        """
        if code < 0 or code >= (1 << _BIT_COUNT):
            raise ValueError("code must be a 49-bit value (0..2**49-1)")
        super().__init__(
            frequency=frequency,
            modulation=ModulationType.OOK,
            repeat_count=_MARANTEC_REPEAT_COUNT,
        )
        self.code = code

    @override
    def get_raw_timings(self) -> list[int]:
        """Compute Marantec frame timings (Manchester-coded OOK).

        Emits 49 Manchester half-bits (bit 0 = high then low, bit 1 = low then
        high), merging consecutive same-polarity halves into long pulses,
        followed by a trailing inter-frame gap of ``te_long * 5``.

        Ordering note (intentional divergence from the reference encoder):
        the reference Flipper encoder emits the inter-frame gap *first*, as a
        leading "header" low, then the data. This module instead starts with
        the first data mark and appends the gap at the end. The reason is that
        transmitters consuming these timings assign polarity by index parity --
        even indices are marks (high), odd indices are spaces (low) -- and
        ignore the sign of each value (e.g. the Broadlink encoder takes the
        absolute duration). A frame that began with the low gap would therefore
        be transmitted inverted. Starting with a mark keeps the polarity
        correct, and because the transmitter replays the timing list
        back-to-back ``repeat_count + 1`` times, the trailing gap of one frame
        becomes the leading gap before the next, reconstructing the reference
        waveform exactly at steady state.

        The leading low half of the first bit (when that bit is 1) is the part
        the reference encoder folds into its header low; here it is likewise
        absorbed into the preceding frame's trailing gap, so only the high half
        of the first bit is emitted.
        """
        timings: list[int] = []

        def add(us: int) -> None:
            if timings and (us > 0) == (timings[-1] > 0):
                timings[-1] += us
            else:
                timings.append(us)

        for idx in range(_BIT_COUNT):
            bit = (self.code >> (_BIT_COUNT - 1 - idx)) & 1
            if idx == 0 and bit:
                # First bit is 1 (low then high); its leading low half is
                # carried by the trailing gap, so start at the high half.
                add(_TE_SHORT)
                continue
            if bit:
                add(-_TE_SHORT)
                add(_TE_SHORT)
            else:
                add(_TE_SHORT)
                add(-_TE_SHORT)

        add(-_HEADER_LOW)
        return timings

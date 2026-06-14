"""Encoder for CAME garage door / gate RF remotes (fixed-code).

433.92 MHz OOK (315 MHz variant available), pulse-width coded. Encodes a
static, indefinitely valid (non-rolling) 12- or 24-bit code. Covers classic
CAME fixed-code remotes (e.g. TOP/TAM/TWIN series). The related Prastel and
Airforce variants share this encoding but are not claimed here.
"""

from __future__ import annotations

from typing import override

from . import ModulationType, RadioFrequencyCommand

_FREQUENCY_433 = 433_920_000
_REPEAT_COUNT = 10

_TE_SHORT = 320
_TE_LONG = 640

_HEADER_TE = {12: 47, 24: 76}


class CameCommand(RadioFrequencyCommand):
    """Encode a CAME fixed-code garage door / gate frame."""

    code: int
    bit_count: int

    def __init__(
        self,
        *,
        code: int,
        bit_count: int = 12,
        frequency: int = _FREQUENCY_433,
    ) -> None:
        """Initialize the CAME command."""
        if bit_count not in _HEADER_TE:
            raise ValueError("bit_count must be 12 or 24")
        if code < 0 or code >= (1 << bit_count):
            raise ValueError("code does not fit in bit_count bits")
        super().__init__(
            frequency=frequency,
            modulation=ModulationType.OOK,
            repeat_count=_REPEAT_COUNT,
        )
        self.code = code
        self.bit_count = bit_count

    @override
    def get_raw_timings(self) -> list[int]:
        """Compute the frame timings as signed mark/space microseconds.

        A short start mark precedes the data bits (bit 1 = long space then
        short mark, bit 0 = short space then long mark), MSB first, followed by
        the header low. The frame is mark-first and ends on that header space,
        which becomes the leading inter-frame gap of the next repeat.
        """
        timings: list[int] = [_TE_SHORT]

        for i in range(self.bit_count - 1, -1, -1):
            if (self.code >> i) & 1:
                timings.append(-_TE_LONG)
                timings.append(_TE_SHORT)
            else:
                timings.append(-_TE_SHORT)
                timings.append(_TE_LONG)

        timings.append(-_TE_SHORT * _HEADER_TE[self.bit_count])
        return timings

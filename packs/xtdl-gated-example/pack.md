# xtdl-gated-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the gate blocks of engine-spec 0.17: on a fixed layout, a field that
exists only when other bits of the message hold a value. The gating bits come
after the fields, and one bit chooses between two meanings of the same bits.

## Layout

7 bytes. Bits are numbered from 0, most significant first. Signed values are
two's complement.

| Bits | Key | When | Meaning |
|---|---|---|---|
| 0-23 | `lat` | bit 55 is 1 | latitude, steps of 1/50000 degree |
| 24-48 | `lon` | bit 55 is 1 | longitude, steps of 1/50000 degree |
| 49-53 | `xtdl.sector` | bit 54 is 0 | sector, 0 to 31 |
| 49-53 | `xtdl.lane_offset_m` | bit 54 is 1 | distance from the middle of the lane: sign bit, then 4 bits of magnitude, -15 to 15 m |
| 54 | (gate) | | 0: bits 49-53 are the sector; 1: the lane offset |
| 55 | (gate) | | 1: bits 0-48 hold a position; 0: they hold nothing |

When bit 55 is 0 the position bits are not read, whatever they hold. On
encode, the engine sets bit 55 when the entity has a position and bit 54 from
whichever of the sector and the lane offset the entity has. A report with
neither leaves bit 54 at 0, so its bits 49-53 are zero and read back as
sector 0.

## Not mapped

Nothing: every field is mapped.

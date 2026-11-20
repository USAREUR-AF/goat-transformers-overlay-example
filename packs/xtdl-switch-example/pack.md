# xtdl-switch-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the `switch` of engine-spec 0.20: in a sequential layout, a later
part of a message laid out according to a value read earlier in it.

## Layout

Bits are numbered from 0, most significant first.

| Bits | Key | Meaning |
|---|---|---|
| 0-4 | `xtdl.sector` | sector, 0 to 31 |
| 5-7 | `xtdl.report_type` | what follows: 1 a position, 2 a speed, 3 or 4 a lane offset, any other value nothing |
| then, type 1 | `lat`, `lon` | 32 bits each, two's complement, steps of 1e-7 degree |
| then, type 2 | `speed_ms` | 16 bits, unsigned, steps of 0.1 m/s |
| then, type 3 or 4 | `xtdl.lane_offset_m` | 8 bits: sign bit, then 7 bits of magnitude, meters |

The report is 1, 2, 3 or 9 bytes long. On encode the type comes from
`xtdl.report_type`. When the entity has no type, its three bits are zero, no
case holds, and the report is the first byte alone.

## Not mapped

Nothing: every field is mapped.

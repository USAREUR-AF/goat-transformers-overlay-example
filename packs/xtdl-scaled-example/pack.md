# xtdl-scaled-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the value transforms of engine-spec 0.15 on the `bits` wire: values
that before 0.15 could be carried only as raw bits. A time in microseconds is
read as whole milliseconds (`uiscale`), a position and an offset are in sign
and magnitude (`smscale`, `smag`), a speed is a scaled single-precision float
(`f32scale`), a code is written in octal digits (`octal`) and a call sign is
in six-bit characters (`chars:icao6`).

## Layout

30 bytes. Bits are numbered from 0, most significant first; every multi-bit
field is most significant bit first.

| Bits | Key | Encoding |
|---|---|---|
| 0-7 | (kind) | message type, always 60 (`0x3c`) |
| 8-63 | `time_ms` | unsigned, microseconds since 1970-01-01T00:00:00Z; read as milliseconds, rounded half away from zero (`uiscale:1/1000`) |
| 64-95 | `lat` | sign and magnitude, steps of 1e-7 degree; sign 1 with magnitude 0 means "no latitude" |
| 96-127 | `lon` | sign and magnitude, steps of 1e-7 degree; sign 1 with magnitude 0 means "no longitude" |
| 128-159 | `speed_ms` | IEEE single, big-endian, in steps of 0.1 m/s (`f32scale:1/10`) |
| 160-171 | `xtdl.lane_offset_m` | sign and magnitude, whole metres, -2047 to 2047 |
| 172-183 | `xtdl.unit_code` | four octal digits, `0000` to `7777` |
| 184-191 | `xtdl.sector` | unsigned |
| 192-239 | `callsign` | eight six-bit characters, first character first: `A`-`Z` are 1-26, space 32, `0`-`9` are 48-57; padded with spaces; eight spaces mean "no call sign" |

A sign bit is 1 for a negative value. A value that rounds to 0 is written with
sign 0, so 0 degrees is not the "no position" code. Sign 1 with magnitude 0
in the offset field reads as 0.

## Worked example

Time 2021-02-27T20:00:00Z, latitude 35.25, longitude 10.5, speed 12.5 m/s,
offset -3 m, unit code `0412`, sector 19, call sign `XT19`:

```
type      60                                      3c
time      1614456000000 ms = 1614456000000000 us  05 bc 56 d4 62 b0 00
lat       352500000, sign 0                       15 02 b9 20
lon       105000000, sign 0                       06 42 2c 40
speed     125.0 as a single                       42 fa 00 00
offset    sign 1, magnitude 3   = 0x803  \
code      0412 octal            = 0x10a   >       80 31 0a
sector    19                              /       13
callsign  X T 1 9 and four spaces:
          24 20 49 57 32 32 32 32                 61 4c 79 82 08 20
```

Southern and western values set the sign bit: latitude -35.25 is
`95 02 b9 20`.

## What the transforms do here

- `time_ms`: 1614456000000500 microseconds is 1614456000000.5 ms and reads
  as 1614456000001; 1614456000000499 reads as 1614456000000. Encode writes
  milliseconds times 1000, so a message read with sub-millisecond digits is
  written back without them.
- `speed_ms`: the float is read as a single, then multiplied by 1/10 in
  doubles (ruling 1 of 0.5). A speed that is not a whole number of 0.1 m/s
  steps keeps its single-precision bits through a round trip. A NaN or an
  infinity on the wire is `transform-decode`.
- `callsign`: decode removes trailing spaces. A code outside the set, such as
  0, is `transform-decode`. An entity with no call sign is written as eight
  spaces through `absent`, not as zero bits (ruling 16 of 0.15): zero bits
  would not read back.
- An absent `xtdl.unit_code` writes zero bits, which read back as `0000`; an
  absent `xtdl.lane_offset_m` or `xtdl.sector` reads back as 0. The format has
  no "no value" code for these.

## Not mapped

Nothing: every bit is a field.

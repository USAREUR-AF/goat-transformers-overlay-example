# xtdl-values-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the value transforms of engine-spec 0.15: values a binary message
holds in a form the plain integer and scale transforms cannot read.

## Layout

27 bytes. Bits are numbered from 0, most significant first.

| Bits | Key | Transform | Meaning |
|---|---|---|---|
| 0-14 | `uid` | `octal` | track code: five octal digits, `00000` to `77777` |
| 15-39 | `lat` | `smscale:1/100000` | latitude: sign bit (1 negative), then 24 bits of magnitude in steps of 1e-5 degree; sign 1 with magnitude 0 means "no latitude" (`absent 16777216`) |
| 40-65 | `lon` | `smscale:1/100000` | longitude: sign bit, then 25 bits of magnitude in steps of 1e-5 degree |
| 66-121 | `time_ms` | `uiscale:1/1000` | time: microseconds since 1970-01-01T00:00:00Z, unsigned; the key holds milliseconds, rounded half away from zero |
| 122-175 | `callsign` | `chars:icao6` | call sign: nine 6-bit characters (`A`-`Z`, space, `0`-`9`), padded with spaces |
| 176-207 | `speed_ms` | `f32scale:1/10` | ground speed: an IEEE-754 single holding tenths of a meter per second; NaN or an infinity is refused |
| 208-215 | `xtdl.lane_offset_m` | `smag` | distance from the middle of the lane, whole meters: sign bit, then 7 bits of magnitude, -127 to 127 |

A longitude with sign 1 and magnitude 0 reads as 0 and is written back with
sign 0. A key that is absent writes zero bits, except the latitude, which
writes its no-value code. Reading 500 microseconds or more past a millisecond
rounds up; less rounds down, so a round trip writes the time back in whole
milliseconds.

## Not mapped

Nothing: every field is mapped.

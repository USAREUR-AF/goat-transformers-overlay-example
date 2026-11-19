# xtdl-values-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the value transforms of engine-spec 0.15: values a binary message
holds in a form the plain integer and scale transforms cannot read.

## Layout

23 bytes. Bits are numbered from 0, most significant first.

| Bits | Key | Transform | Meaning |
|---|---|---|---|
| 0-14 | `uid` | `octal` | track code: five octal digits, `00000` to `77777` |
| 15-39 | `lat` | `smscale:1/100000` | latitude: sign bit (1 negative), then 24 bits of magnitude in steps of 1e-5 degree |
| 40-65 | `lon` | `smscale:1/100000` | longitude: sign bit, then 25 bits of magnitude in steps of 1e-5 degree |
| 66-97 | `time_ms` | `uiscale:1000` | time: whole seconds since 1970-01-01T00:00:00Z, unsigned; the key holds milliseconds |
| 98-151 | `callsign` | `chars:icao6` | call sign: nine 6-bit characters (`A`-`Z`, space, `0`-`9`), padded with spaces |
| 152-183 | `speed_ms` | `f32scale:1/10` | ground speed: an IEEE-754 single holding tenths of a meter per second |

A sign bit with a magnitude of 0 reads as 0 and is written back with sign 0.
A key that is absent writes zero bits.

## Not mapped

Nothing: every field is mapped.

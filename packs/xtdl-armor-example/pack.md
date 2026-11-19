# xtdl-armor-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows six-bit armor of engine-spec 0.14: a binary message written as
printable text in which each character carries six bits, and a text field
whose characters are six-bit codes.

## Layout

Bits are numbered from 0, most significant first. Signed values are two's
complement.

| Bits | Key | Meaning |
|---|---|---|
| 0-5 | (kind) | message type, always 9 |
| 6-10 | `xtdl.sector` | sector, 0 to 31 |
| 11-38 | `lat` | latitude, steps of 1/600000 degree; 54600000 (91 degrees) means "no latitude" |
| 39-67 | `lon` | longitude, steps of 1/600000 degree; 108600000 (181 degrees) means "no longitude" |
| 68-109 | `callsign` | seven six-bit characters, `@` to `_` for 0 to 31 and space to `?` for 32 to 63; trailing `@` and spaces removed |
| 110-119 | `speed_ms` | ground speed, steps of 0.1 m/s; optional: a message of 19 characters ends before it |

The text: each six bits, first to last, as one character, `0` to `W` for 0
to 39 and `` ` `` to `w` for 40 to 63. A message with the speed is 20
characters (120 bits); without it, 19 characters, the last four bits zero.
Bits past the last field are ignored when read.

## Not mapped

Nothing: every field is mapped. The sentence a real six-bit payload travels
in, its fill-bit count and the joining of payloads split over several
sentences are not part of the armor (ruling 1 of 0.14).

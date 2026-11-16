# Pack: xtdl-example (fictional)

An invented binary format. The layout encodes nothing real. It shows what a
binary pack looks like in an overlay: two message kinds chosen by a number on
the wire, a value table, a `default`, a `const` and a counted list.

Bits are numbered from the least significant bit of each byte. Integers of more
than one byte have the least significant byte first.

## Every message

| Bytes | Bits | Holds | Model key |
|---|---|---|---|
| 0 | 0-2 | message number: 1 position, 2 contacts | selects the kind |
| 0 | 3-7 | sector, 0 to 31 | `xtdl.sector` |
| 1-3 | | seconds since UTC midnight | `xtdl.day_s` |

## Message 1, `position` (13 bytes)

| Bytes | Bits | Holds | Model key |
|---|---|---|---|
| 4-7 | | latitude, signed, steps of 0.0000001 degree | `lat` |
| 8-11 | | longitude, signed, steps of 0.0000001 degree | `lon` |
| 12 | 0-1 | status: 0 idle, 1 active, 2 fault, 3 unknown | `xtdl.status` |
| 12 | 2-3 | not used, zero | |
| 12 | 4-7 | the constant 5 | |

A source with no status is written as 3 (`default xtdl.status unknown`); zero
bits would state `idle`.

## Message 2, `contacts` (5 bytes and 3 bytes per contact)

| Bytes | Holds | Model key |
|---|---|---|
| 4 | number of contacts | the length of `xtdl.contacts` |
| 5, 8, 11, ... | contact number | `xtdl.contact_id` |
| 6, 9, 12, ... | bearing, steps of 360/256 degree | `xtdl.bearing_deg` |
| 7, 10, 13, ... | range, steps of 100 meters | `xtdl.range_m` |

## Worked example

`99 401901 20b90215 402c4206 51` is a position:

| Bytes | Reading |
|---|---|
| `99` | binary `10011 001`: sector 19, message 1 |
| `40 19 01` | 0x011940 = 72000 seconds = 20:00:00 UTC |
| `20 b9 02 15` | 0x1502b920 = 352500000 steps = 35.25 degrees |
| `40 2c 42 06` | 0x06422c40 = 105000000 steps = 10.5 degrees |
| `51` | binary `0101 00 01`: constant 5, status 1 (active) |

`tools/vectors.py` computes the bytes of every vector the same way.

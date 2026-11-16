# Pack: xtdl-b-example (fictional)

A second invented binary format, 11 bytes, one layout. Bits are numbered from
the most significant bit of each byte. Integers of more than one byte have the
most significant byte first.

| Bytes | Bits | Holds | Model key |
|---|---|---|---|
| 0-3 | | latitude, signed, steps of 0.0000001 degree | `lat` |
| 4-7 | | longitude, signed, steps of 0.0000001 degree | `lon` |
| 8 | 0-4 | sector, 0 to 31 | `xtdl.sector` |
| 8 | 5-6 | status: 0 unknown, 1 idle, 2 active, 3 fault | `xtdl.status` |
| 8 | 7 | not used, zero | |
| 9-10 | | time of day, steps of 2 seconds since UTC midnight | `xtdl.day_s` |

## Worked example

`1502b920 06422c40 9c 8ca0`:

| Bytes | Reading |
|---|---|
| `15 02 b9 20` | 352500000 steps = 35.25 degrees |
| `06 42 2c 40` | 105000000 steps = 10.5 degrees |
| `9c` | binary `10011 10 0`: sector 19, status 2 (active) |
| `8c a0` | 36000 steps = 72000 seconds = 20:00:00 UTC |

It is the same report as the worked example of `xtdl-example`. The status is
number 1 there and number 2 here: each pack's value table maps its own number
to the word `active` in the model.

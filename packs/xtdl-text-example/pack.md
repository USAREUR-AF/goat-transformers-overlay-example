# xtdl-text-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the `text` wire of engine-spec 0.10: one line of ASCII text, a start
marker, fields separated by commas, and a two-digit checksum after `*`.

## Layout

`$XTPOS,<sector>,<lat>,<N|S>,<lon>,<E|W>,<hhmmss>,<status>*<checksum>`

| Field | Key | Encoding |
|---|---|---|
| 0 | | the tag `XTPOS`, which selects the kind |
| 1 | `xtdl.sector` | decimal, at least two digits |
| 2, 3 | `lat` | degrees (2 digits) and minutes with 4 decimals, then `N` or `S` |
| 4, 5 | `lon` | degrees (3 digits) and minutes with 4 decimals, then `E` or `W` |
| 6 | `xtdl.day_s` | time of day, `hhmmss` |
| 7 | `xtdl.status` | `idle`, `active`, `fault` or `unknown`; `unknown` is written when the entity has none |

The checksum is the exclusive or of every byte between `$` and `*`, as two
hexadecimal digits.

## Worked example

Sector 19, latitude 35.25, longitude 10.5, 20:00:00 UTC, active:

```
$XTPOS,19,3515.0000,N,01030.0000,E,200000,active*<xor>
```

35.25 degrees is 35 degrees 15.0000 minutes; 10.5 degrees is 010 degrees
30.0000 minutes. The same report converts byte for byte to `xtdl-example`.

## Not mapped

Nothing: every field is mapped.

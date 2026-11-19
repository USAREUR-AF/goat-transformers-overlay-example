# xtdl-track-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the `absent` field option of engine-spec 0.9: a value on the wire that
means "no value". On decode a field that holds its code leaves the key absent;
on encode a key the entity lacks is written as the code.

## Layout

11 bytes, every multi-byte field least significant byte first.

| Bytes | Key | Encoding | No-value code |
|---|---|---|---|
| 0-3 | `lat` | signed, 1e-7 degree steps | `0x80000000` |
| 4-7 | `lon` | signed, 1e-7 degree steps | `0x80000000` |
| 8-9 | `speed_ms` | unsigned, 0.1 m/s steps | `0xFFFF` |
| 10 | `xtdl.sector` | unsigned | `0xFF` |

## Worked example

Latitude 35.25, longitude 10.5, speed 12.5 m/s, sector 19:

```
lat    352500000 = 0x1502B920  ->  20 b9 02 15
lon    105000000 = 0x0642C840  ->  40 c8 42 06
speed  125       = 0x007D      ->  7d 00
sector 19        = 0x13        ->  13
```

The same report with no position: `00 00 00 80 00 00 00 80 7d 00 13`; decode
gives `speed_ms` and `xtdl.sector` and leaves `lat` and `lon` absent.

## Rounding and range (engine-spec 0.11)

A speed is written as the nearest number of 0.1 m/s steps, a value exactly
halfway rounded away from zero: 0.25 m/s is 2.5 steps and is written as 3.
A speed of more than 65535 steps (6553.5 m/s) does not fit the field and fails
with `transform-encode`; the field's low bits are never written.

## Not mapped

Nothing: every byte is a field.

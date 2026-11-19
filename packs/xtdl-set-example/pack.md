# xtdl-set-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the `tlv` wire of engine-spec 0.13: a message that is a set of
tag, length and value items, the shape of a KLV local set.

## Layout

The message is the four bytes `78 74 64 6c` (the key), a length, then the set.
Every item is a one-byte tag, a length and the value. A length below 128 is one
byte; a longer one is `0x81` to `0x88` followed by that many bytes (BER). Every
integer is big-endian.

| Tag | Key | Value |
|---|---|---|
| 2 | `time_ms` | 8 bytes, unsigned: milliseconds since 1970-01-01T00:00:00Z |
| 3 | `callsign` | UTF-8 text, any length |
| 4 | `lat` | 4 bytes, two's complement, steps of 1e-7 degree |
| 5 | `lon` | 4 bytes, two's complement, steps of 1e-7 degree |
| 6 | (a nested set) | items with the same tag and length encodings: |
| 6.1 | `xtdl.sector` | 1 byte, unsigned, 0 to 31 |
| 6.2 | `speed_ms` | 2 bytes, unsigned, steps of 0.1 m/s |
| 1 | (checksum) | 2 bytes, the last item of the set |

The checksum is the 16-bit sum of every byte from the first byte of the key to
the checksum item's length byte, a byte at an even offset counting 256 times
its value and a byte at an odd offset once, modulo 65536.

An item that is not sent is absent. An item with a tag the pack does not name
is kept as residue and written back, after the mapped items, when the message
is written in this same format. When neither 6.1 nor 6.2 is present the nested
set is not written.

## Not mapped

Nothing: every item is mapped.

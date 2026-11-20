# xtdl-text-ends-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the long and terminated fields of engine-spec 0.22 in a sequential
layout.

## Layout

Bits are numbered from 0, most significant first.

| Bits | Key | Meaning |
|---|---|---|
| 0-7 | `xtdl.sector` | sector |
| 8-103 | `xtdl.auth_tag` | a 96-bit tag kept as it is: 24 hex digits (`hex`) |
| 104-151 | `xtdl.class` | up to 5 characters of 8 bits, ended by a NUL, padded with NULs to 6 bytes (`chars:ascii8 stop 0`) |
| then | `callsign` | 7-bit characters (32 to 126), any number, ended by the code 127, which is not part of the text (`until:127 chars:ascii7`) |
| then | | zero bits to the next whole byte (`align 8`) |

A call sign with no terminator before the end of the message is
`malformed-wire`. A class of 6 characters leaves no room for its NUL and
cannot be written (`transform-encode`), though it can be read.

## Not mapped

Nothing: every field is mapped.

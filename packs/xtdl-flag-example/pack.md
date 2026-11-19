# xtdl-flag-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the `present` derive function of engine-spec 0.12: a value set from
whether another value is sent at all, not from what it is.

## Layout

A JSON object:

| Member | Key | Meaning |
|---|---|---|
| `position_sent` | `xtdl.position_sent` | 1 when the report carries a position, 0 when it carries none |
| `lat`, `lon` | `lat`, `lon` | the position, degrees |
| `speed_ms` | `speed_ms` | ground speed, m/s |

`model/xtdl.def` holds `derive xtdl.position_sent present lat`: in a conversion
from another format the flag becomes 1 when the source gave a latitude. When it
gave none, nothing sets the flag and this pack's `default` writes 0. A JSON
document read and written by this same pack keeps the flag it holds, whatever
the position members say (a same-format round trip applies no derivation).

## Not mapped

Nothing: every member is mapped.

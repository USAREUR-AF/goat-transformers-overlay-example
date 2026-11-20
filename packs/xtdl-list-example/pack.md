# xtdl-list-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the list forms of engine-spec 0.21 in a sequential layout.

## Layout

Bits are numbered from 0, most significant first.

| Bits | Key | Meaning |
|---|---|---|
| 0-4 | `xtdl.sector` | sector, 0 to 31 |
| 5-7 | (count) | number of contacts, 0 to 7: read here, before the speed (`count ncontacts 3`) |
| 8-23 | `speed_ms` | ground speed, steps of 0.1 m/s |
| then, 16 bits per contact | `xtdl.contacts`: `xtdl.contact_id` (8 bits), `xtdl.bearing_deg` (8 bits, steps of 360/256 degree) | the contacts the count states (`group ... count @ncontacts`) |
| then, 8 bits per mark | `xtdl.marks`: a flag bit (1 on the last mark), then `xtdl.mark_code` (7 bits) | at least one mark (`group ... last`) |
| then, 8 bits per byte, to the end | `xtdl.notes`: `xtdl.note_byte` | a note that fills the rest of the message (`group ... rest`) |

The count is written after the contacts are laid out, at its own place. A
report with no marks cannot be written: the last-item flag needs at least one
item (`transform-encode`).

## Not mapped

Nothing: every field is mapped.

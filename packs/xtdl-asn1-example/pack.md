# xtdl-asn1-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows ASN.1 unaligned PER (engine-spec 0.19): a message defined in ASN.1,
where every value takes the fewest bits its constraint allows.

## The ASN.1 module

```asn1
XtdlExample DEFINITIONS AUTOMATIC TAGS ::= BEGIN

XtdlTrack ::= SEQUENCE {
  sector    INTEGER (0..31),
  lat       INTEGER (-900000000..900000000),     -- 1e-7 degree
  lon       INTEGER (-1800000000..1800000000),   -- 1e-7 degree
  status    ENUMERATED { idle, active, fault, unknown },
  callsign  IA5String (SIZE (1..8)) OPTIONAL,
  motion    CHOICE {
    speed       INTEGER (0..1023),               -- 0.1 m/s
    laneOffset  INTEGER (-15..15)                -- m
  },
  contacts  SEQUENCE (SIZE (0..4)) OF Contact,
  ...
}

Contact ::= SEQUENCE {
  id     INTEGER (0..255),
  range  INTEGER (0..65535)                      -- 100 m
}

END
```

## Mapping

| Component | Key | Bits |
|---|---|---|
| extension bit | | 1 |
| presence of `callsign` | | 1 |
| `sector` | `xtdl.sector` | 5 |
| `lat`, `lon` | `lat`, `lon` | 31, 32 |
| `status` | `xtdl.status` (idle, active, fault, unknown) | 2 |
| `callsign` | `callsign` | 3 for the length, then 7 per character |
| `motion` | `speed_ms` or `xtdl.lane_offset_m` | 1 for the choice, then 10 or 5 |
| `contacts` | the list `xtdl.contacts`: `xtdl.contact_id`, `xtdl.range_m` | 3 for the count, then 24 per contact |

The message is padded with zero bits to a whole octet. When the entity has a
speed, `motion` is `speed`; otherwise, with a lane offset, `laneOffset`. A
status the source does not give is written as `unknown`. Extension additions
in a message from a later version of the module are skipped on decode.

## Not mapped

Nothing: every component is mapped.

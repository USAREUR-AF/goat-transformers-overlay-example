# xtdl-report-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows conditional output of engine-spec 0.18.

## Layout

An XML document with the root element `report`:

| Where | Key | Meaning |
|---|---|---|
| `@id` | `uid` | identifier of the reporter |
| `@time` | `time_ms` | time of the report, ISO 8601 in UTC, with no fraction when the milliseconds are 0 (`iso8601_short`) |
| `pos/@lat`, `pos/@lon` | `lat`, `lon` | position, degrees |
| `class` (text) | `xtdl.class` | what the reporter classifies the contact as |
| `class/@confidence` | `xtdl.confidence` | confidence in the class, 0 to 1; written only when there is a class (`with xtdl.class`) |
| `flags` (text) | `xtdl.flags` | flag tokens separated by spaces |
| `detail` | | always written, empty when nothing is in it (`element detail`) |

## The flag tokens

Two derive lines in `model/xtdl.def` handle the tokens:

- `tokens:space:positioned,sectored` builds the text from `xtdl.position_sent`
  (1 when the report has a position, engine-spec 0.12) and `xtdl.sector`
  (`sectored` when it is present and not 0). It applies only when the source
  gives no flags text.
- `has_token:space:degraded` sets `xtdl.degraded` to 1 when the text holds
  the token `degraded`, and to 0 otherwise.

## What a round trip keeps

Decode reads a confidence even without a class; encode then leaves it out,
because it is written only with a class.

## Not mapped

Nothing: every element and attribute is mapped.

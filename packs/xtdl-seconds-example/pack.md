# Pack: xtdl-seconds-example (fictional)

An invented JSON format whose schema allows a time to the whole second only
(engine-spec 0.26). One object:

```json
{"id": "XT-19", "time": "2021-02-27T20:00:00Z", "sector": 19, "position": {"lat": 35.25, "lon": 10.5}}
```

| Member | Model key | Transform |
|---|---|---|
| `id` | `uid` | `string` |
| `time` | `time_ms` | `iso8601_s`: read as `iso8601_ms` (a fraction on the wire is read, its milliseconds kept in the model); written `YYYY-MM-DDTHH:MM:SSZ`, the milliseconds dropped, never rounded |
| `sector` | `xtdl.sector` | `int` |
| `position.lat`, `position.lon` | `lat`, `lon` | `float` |

Every member is optional. Because `iso8601_s` drops the milliseconds on encode,
a same-format round trip of a time with a fraction is not byte-exact (vector
02); a time from `xtdl-json-example`, which writes milliseconds, loses them
here (vector 03) and comes back as `.000` (vector 04). A time just before the
epoch writes the second that holds it (vector 05).

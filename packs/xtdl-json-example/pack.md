# Pack: xtdl-json-example (fictional)

An invented JSON format. One object:

```json
{
  "id": "XT-19",
  "time": "2021-02-27T20:00:00.000Z",
  "sector": 19,
  "status": "active",
  "position": {"lat": 35.25, "lon": 10.5},
  "contacts": [
    {"id": 12, "bearing_deg": 90, "range_m": 1500},
    {"id": 200, "bearing_deg": 225, "range_m": 12000}
  ]
}
```

| Member | Model key |
|---|---|
| `id` | `uid` |
| `time` | `time_ms` |
| `sector` | `xtdl.sector` |
| `status` | `xtdl.status` |
| `position.lat`, `position.lon` | `lat`, `lon` |
| `contacts` | the list `xtdl.contacts` |
| `contacts[].id`, `.bearing_deg`, `.range_m` | `xtdl.contact_id`, `xtdl.bearing_deg`, `xtdl.range_m` |

Every member is optional. `contacts` maps the same list as the counted group of
`xtdl-example`, so a contact message converts to this array and back.

# xtdl-frame-example

A FICTIONAL format, invented for this example. It is not a real standard.

It shows the derive functions of engine-spec 0.16: a time and a position held
in a form other than the shared model's, converted by `derive` lines in the
model module rather than by the pack.

## Layout

A JSON object:

| Member | Key | Meaning |
|---|---|---|
| `t_s` | `xtdl.t_s` | whole seconds since 1970-01-01T00:00:00Z |
| `t_ns` | `xtdl.t_ns` | nanoseconds past `t_s` |
| `x`, `y`, `z` | `xtdl.ecef_x_m`, `xtdl.ecef_y_m`, `xtdl.ecef_z_m` | position, earth-centered, earth-fixed meters (WGS 84) |
| `geoid_m` | `xtdl.geoid_m` | height of the geoid above the ellipsoid at the position, meters |

## What the derive lines do

`model/xtdl.def` holds them; each fills its target only when it is absent.

| Target | Function | From |
|---|---|---|
| `time_ms` | `ms_of` | `xtdl.t_s`, `xtdl.t_ns` |
| `xtdl.t_s`, `xtdl.t_ns` | `sec_of`, `nsec_of` | `time_ms` |
| `lat`, `lon`, `hae` | `lat_of_ecef`, `lon_of_ecef`, `hae_of_ecef` | the three ECEF keys |
| the three ECEF keys | `ecef_x`, `ecef_y`, `ecef_z` | `lat`, `lon`, `hae` |
| `xtdl.h_msl_m` | `sub` | `hae` minus `xtdl.geoid_m` |

So a GeoJSON point with a height becomes ECEF coordinates here, and this
format's coordinates become a GeoJSON point. The height above mean sea level
is in the model for any format that maps it.

## Not mapped

Nothing: every member is mapped.

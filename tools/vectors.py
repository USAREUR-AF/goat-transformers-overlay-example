#!/usr/bin/env python3
"""Write the conformance vectors of this overlay's three fictional formats.

The expected bytes are computed here, from the layouts as the pack.md files
state them, with plain integer arithmetic. No engine is used: the engines are
then checked against these files (./check.sh).

  python3 tools/vectors.py           write packs/*/vectors/*.json
  python3 tools/vectors.py --check   exit 1 when a file on disk differs
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

X, B, J = "xtdl-example", "xtdl-b-example", "xtdl-json-example"
T, TX = "xtdl-track-example", "xtdl-text-example"
F = "xtdl-flag-example"
X_STATUS = {"idle": 0, "active": 1, "fault": 2, "unknown": 3}
B_STATUS = {"unknown": 0, "idle": 1, "active": 2, "fault": 3}


def le(value, nbytes):
    """An integer as bytes, least significant first (two's complement)."""
    return (value & ((1 << (8 * nbytes)) - 1)).to_bytes(nbytes, "little")


def be(value, nbytes):
    """An integer as bytes, most significant first (two's complement)."""
    return (value & ((1 << (8 * nbytes)) - 1)).to_bytes(nbytes, "big")


def deg7(degrees):
    """Degrees as a count of 1e-7 degree steps."""
    return round(degrees * 10_000_000)


def x_header(number, sector, day_s):
    # byte 0: message number in the low 3 bits, sector in the high 5
    return bytes([number | sector << 3]) + le(day_s, 3)


def x_position(sector, day_s, lat, lon, status, revision=5):
    # byte 12: status in the low 2 bits, the constant 5 in the high 4
    last = X_STATUS[status] | revision << 4
    return (x_header(1, sector, day_s) + le(deg7(lat), 4) + le(deg7(lon), 4) + bytes([last])).hex()


def x_contacts(sector, day_s, contacts):
    out = x_header(2, sector, day_s) + bytes([len(contacts)])
    for ident, bearing_deg, range_m in contacts:
        # bearing in steps of 360/256 degrees, range in steps of 100 meters
        out += bytes([ident, round(bearing_deg * 32 / 45), round(range_m / 100)])
    return out.hex()


def b_position(sector, day_s, lat, lon, status):
    # byte 8, most significant bit first: 5 bits sector, 2 bits status, 1 unused
    packed = sector << 3 | B_STATUS[status] << 1
    # bytes 9-10: time of day in steps of 2 seconds
    return (be(deg7(lat), 4) + be(deg7(lon), 4) + bytes([packed]) + be(day_s // 2, 2)).hex()


NO_POS = 0x80000000   # xtdl-track-example: the code for "no latitude" and "no longitude"
NO_SPEED = 0xFFFF     # xtdl-track-example: the code for "no speed"
NO_SECTOR = 0xFF      # xtdl-track-example: the code for "no sector"


def t_track(lat=None, lon=None, speed_ms=None, sector=None):
    """xtdl-track-example: an absent value is written as its no-value code."""
    raw_lat = NO_POS if lat is None else deg7(lat) & 0xFFFFFFFF
    raw_lon = NO_POS if lon is None else deg7(lon) & 0xFFFFFFFF
    raw_speed = NO_SPEED if speed_ms is None else round(speed_ms * 10)
    raw_sector = NO_SECTOR if sector is None else sector
    return (le(raw_lat, 4) + le(raw_lon, 4) + le(raw_speed, 2) + bytes([raw_sector])).hex()


def nmea_xor(body):
    x = 0
    for c in body.encode("ascii"):
        x ^= c
    return "%02X" % x


def dm(value, deg_digits, pos, neg):
    """Degrees as degrees and minutes with 4 decimals, then the hemisphere letter."""
    m = round(abs(value) * 60 * 10_000)
    d, rest = divmod(m, 60 * 10_000)
    text = "%0*d%02d.%04d" % (deg_digits, d, rest // 10_000, rest % 10_000)
    return text, (neg if value < 0 and m > 0 else pos)


def tx_position(sector, day_s, lat, lon, status):
    la, ns = dm(lat, 2, "N", "S")
    lo, ew = dm(lon, 3, "E", "W")
    h, rem = divmod(day_s, 3600)
    body = "XTPOS,%02d,%s,%s,%s,%s,%02d%02d%02d,%s" % (sector, la, ns, lo, ew, h, rem // 60, rem % 60, status)
    return "$" + body + "*" + nmea_xor(body)


def j(members):
    """Canonical JSON text: members in the order given, no whitespace."""
    return json.dumps(members, separators=(",", ":"))


def j_contacts(contacts):
    return [{"id": i, "bearing_deg": b, "range_m": r} for i, b, r in contacts]


# One position report and one contact report, used by every vector.
P = dict(sector=19, day_s=72000, lat=35.25, lon=10.5, status="active")      # 20:00:00 UTC
CONTACTS = [(12, 90, 1500), (200, 225, 12000)]
C = dict(sector=7, day_s=3600, contacts=CONTACTS)                            # 01:00:00 UTC

VECTORS = [
    (X, "01-position-roundtrip", dict(
        to=X, input=x_position(**P), expect=x_position(**P),
        model={"@kind": "position", "xtdl.sector": "19", "xtdl.day_s": "72000",
               "lat": "35.25", "lon": "10.5", "xtdl.status": "active"})),
    (X, "02-contacts-roundtrip", dict(
        to=X, input=x_contacts(**C), expect=x_contacts(**C),
        model={"@kind": "contacts", "xtdl.contacts.#": "2",
               "xtdl.contacts[0].xtdl.contact_id": "12",
               "xtdl.contacts[0].xtdl.bearing_deg": "90",
               "xtdl.contacts[1].xtdl.range_m": "12000"})),
    (X, "03-position-to-geojson", dict(
        to="geojson", input=x_position(**P),
        expect=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                  "properties": {}}))),
    (X, "04-position-to-xtdl-b", dict(
        to=B, input=x_position(**P), expect=b_position(**P))),
    (X, "05-contacts-to-xtdl-json", dict(
        to=J, input=x_contacts(**C),
        expect=j({"sector": 7, "contacts": j_contacts(CONTACTS)}))),
    (X, "06-no-contacts-to-xtdl-json", dict(
        to=J, input=x_contacts(7, 3600, []),
        expect=j({"sector": 7, "contacts": []}),
        model={"xtdl.contacts.#": "0"})),
    (X, "07-const-written-on-encode", dict(
        to=X, input=x_position(**P, revision=0), expect=x_position(**P))),
    (X, "08-unknown-message-number", dict(
        to=X, input=(bytes([7 | 19 << 3]) + bytes(12)).hex(), expect_error="no-kind")),
    (B, "01-roundtrip", dict(
        to=B, input=b_position(**P), expect=b_position(**P),
        model={"xtdl.sector": "19", "xtdl.status": "active", "xtdl.day_s": "72000"})),
    (B, "02-to-xtdl", dict(
        to=X, input=b_position(**P), expect=x_position(**P))),
    (J, "01-roundtrip", dict(
        to=J,
        input=j({"id": "XT-19", "time": "2021-02-27T20:00:00.000Z", "sector": 19, "status": "active",
                 "position": {"lat": 35.25, "lon": 10.5}, "contacts": j_contacts(CONTACTS)}),
        expect=j({"id": "XT-19", "time": "2021-02-27T20:00:00.000Z", "sector": 19, "status": "active",
                  "position": {"lat": 35.25, "lon": 10.5}, "contacts": j_contacts(CONTACTS)}))),
    (J, "02-contacts-to-xtdl-derives-time-of-day", dict(
        to=X,
        input=j({"id": "XT-7", "time": "2021-02-27T01:00:00.000Z", "sector": 7,
                 "contacts": j_contacts(CONTACTS)}),
        expect=x_contacts(**C),
        model={"@complete": True, "xtdl.day_s": "3600", "xtdl.contacts.#": "2"})),
    (J, "03-position-to-xtdl-default-status", dict(
        to=X,
        input=j({"time": "2021-02-27T20:00:00.000Z", "sector": 19,
                 "position": {"lat": 35.25, "lon": 10.5}}),
        expect=x_position(**dict(P, status="unknown")))),
    (T, "01-roundtrip", dict(
        to=T, input=t_track(35.25, 10.5, 12.5, 19), expect=t_track(35.25, 10.5, 12.5, 19),
        model={"lat": "35.25", "lon": "10.5", "speed_ms": "12.5", "xtdl.sector": "19"})),
    (T, "02-no-position-reads-absent", dict(
        to=T, input=t_track(None, None, 12.5, 19), expect=t_track(None, None, 12.5, 19),
        model={"speed_ms": "12.5", "xtdl.sector": "19", "@absent": ["lat", "lon"]})),
    (T, "03-from-xtdl-writes-no-speed", dict(
        from_=X, to=T, input=x_position(**P), expect=t_track(35.25, 10.5, None, 19))),
    (T, "04-no-speed-to-geojson", dict(
        to="geojson", input=t_track(35.25, 10.5, None, None),
        expect=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                  "properties": {}}),
        model={"lat": "35.25", "@absent": ["speed_ms", "xtdl.sector"]})),
    (T, "05-half-step-rounds-away-from-zero", dict(
        from_="geojson", to=T,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                 "properties": {"speed_ms": 0.25}}),
        # 0.25 m/s is 2.5 steps of 0.1 m/s: engine-spec 0.11 ruling 4a rounds half away from zero, to 3
        expect=(le(deg7(35.25), 4) + le(deg7(10.5), 4) + le(3, 2) + bytes([NO_SECTOR])).hex())),
    (T, "06-speed-too-large", dict(
        from_="geojson", to=T,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                 "properties": {"speed_ms": 6553.6}}),
        # 65536 steps do not fit 16 bits: engine-spec 0.11 ruling 4b
        expect_error="transform-encode")),
    (TX, "01-roundtrip", dict(
        to=TX, input=tx_position(**P), expect=tx_position(**P),
        model={"@kind": "position", "xtdl.sector": "19", "lat": "35.25", "lon": "10.5",
               "xtdl.day_s": "72000", "xtdl.status": "active"})),
    (TX, "02-to-xtdl", dict(
        to=X, input=tx_position(**P), expect=x_position(**P))),
    (TX, "03-from-xtdl", dict(
        from_=X, to=TX, input=x_position(**P), expect=tx_position(**P))),
    (TX, "04-southern-western", dict(
        to=TX, input=tx_position(19, 72000, -35.25, -10.5, "idle"),
        expect=tx_position(19, 72000, -35.25, -10.5, "idle"),
        model={"lat": "-35.25", "lon": "-10.5"})),
    (TX, "05-bad-checksum", dict(
        to=TX, input=tx_position(**P)[:-2] + "00", expect_error="malformed-wire")),
    (F, "01-position-sets-the-flag", dict(
        from_="geojson", to=F,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                 "properties": {"speed_ms": 12.5}}),
        expect=j({"position_sent": 1, "lat": 35.25, "lon": 10.5, "speed_ms": 12.5}))),
    (F, "02-no-position-writes-the-default", dict(
        from_=T, to=F, input=t_track(None, None, 12.5, 19),
        expect=j({"position_sent": 0, "speed_ms": 12.5}))),
    (F, "03-roundtrip-keeps-the-flag", dict(
        to=F, input=j({"position_sent": 0, "lat": 35.25, "lon": 10.5}),
        expect=j({"position_sent": 0, "lat": 35.25, "lon": 10.5}),
        model={"xtdl.position_sent": "0", "lat": "35.25"})),
]


def main():
    check = "--check" in sys.argv[1:]
    stale = 0
    for pack, name, body in VECTORS:
        body = dict(body)
        vector = {"name": name.split("-", 1)[1], "from": body.pop("from_", pack)}
        vector.update(body)
        text = json.dumps(vector, indent=2) + "\n"
        path = os.path.join(ROOT, "packs", pack, "vectors", name + ".json")
        if check:
            on_disk = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if on_disk != text:
                print("vectors: %s differs from tools/vectors.py" % os.path.relpath(path, ROOT))
                stale += 1
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
    if stale:
        return 1
    print("vectors: %d %s" % (len(VECTORS), "match tools/vectors.py" if check else "written"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

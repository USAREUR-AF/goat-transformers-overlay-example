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
]


def main():
    check = "--check" in sys.argv[1:]
    stale = 0
    for pack, name, body in VECTORS:
        vector = {"name": name.split("-", 1)[1], "from": pack}
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

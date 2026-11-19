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
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

X, B, J = "xtdl-example", "xtdl-b-example", "xtdl-json-example"
T, TX = "xtdl-track-example", "xtdl-text-example"
F = "xtdl-flag-example"
S = "xtdl-set-example"
A = "xtdl-armor-example"
SC = "xtdl-scaled-example"
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

S_KEY = bytes.fromhex("7874646c")   # xtdl-set-example: the four-byte key


def ber(n):
    """A BER length: one byte below 128, else 0x80 + count, then the count's bytes."""
    if n < 128:
        return bytes([n])
    size = (n.bit_length() + 7) // 8
    return bytes([0x80 | size]) + n.to_bytes(size, "big")


def tlv_item(tag, value):
    return bytes([tag]) + ber(len(value)) + value


def s_set(time_ms=None, callsign=None, lat=None, lon=None, sector=None, speed_ms=None, residue=b""):
    """xtdl-set-example: the mapped items in line order, residue, then the checksum item."""
    body = b""
    if time_ms is not None:
        body += tlv_item(2, be(time_ms, 8))
    if callsign is not None:
        body += tlv_item(3, callsign.encode("utf-8"))
    if lat is not None:
        body += tlv_item(4, be(deg7(lat), 4))
    if lon is not None:
        body += tlv_item(5, be(deg7(lon), 4))
    nested = b""
    if sector is not None:
        nested += tlv_item(1, bytes([sector]))
    if speed_ms is not None:
        nested += tlv_item(2, be(round(speed_ms * 10), 2))
    if nested:
        body += tlv_item(6, nested)
    body += residue
    # the checksum item (tag 1, length 2, two bytes) is the last item and counts in the length
    head = S_KEY + ber(len(body) + 4) + body + bytes([1, 2])
    total = sum(b * 256 if i % 2 == 0 else b for i, b in enumerate(head)) % 65536
    return (head + be(total, 2)).hex()


A_NO_LAT = 91 * 600000    # xtdl-armor-example: the code for "no latitude"
A_NO_LON = 181 * 600000   # xtdl-armor-example: the code for "no longitude"


def armor(bits):
    """A string of '0'/'1' as six-bit armored text, zero-filled to a multiple of 6."""
    bits += "0" * (-len(bits) % 6)
    out = ""
    for i in range(0, len(bits), 6):
        v = int(bits[i:i + 6], 2)
        out += chr(0x30 + v if v < 40 else 0x38 + v)
    return out


def ubits(value, width):
    return format(value & ((1 << width) - 1), "0%db" % width)


def sixbit_text(text, chars):
    """Text as six-bit character codes: '@'..'_' are 0..31, ' '..'?' are 32..63; '@' pads."""
    text = text.ljust(chars, "@")
    return "".join(ubits(ord(c) - 0x40 if ord(c) >= 0x40 else ord(c), 6) for c in text)


def a_position(sector, lat, lon, callsign, speed_ms=None, fill="", kind=9):
    """xtdl-armor-example; `fill` replaces the trailing zero fill bits of the last character."""
    raw_lat = A_NO_LAT if lat is None else round(lat * 600000)
    raw_lon = A_NO_LON if lon is None else round(lon * 600000)
    bits = (ubits(kind, 6) + ubits(sector, 5) + ubits(raw_lat, 28) + ubits(raw_lon, 29)
            + sixbit_text(callsign, 7))
    if speed_ms is not None:
        bits += ubits(round(speed_ms * 10), 10)
    return armor(bits + fill)


SC_NO_POS = 1 << 31   # xtdl-scaled-example: sign 1, magnitude 0 (a negative zero) means "no position"
ICAO6 = {**{chr(0x40 + i): i for i in range(1, 27)}, " ": 32, **{str(d): 48 + d for d in range(10)}}


def smag_bits(value, width):
    """Sign and magnitude: the first bit 1 for a negative value, then |value|."""
    assert abs(value) < 1 << (width - 1)
    return ("1" if value < 0 else "0") + ubits(abs(value), width - 1)


def icao6_text(text, chars):
    """Text as icao6 codes (A-Z 1-26, space 32, 0-9 48-57), padded with spaces."""
    return "".join(ubits(ICAO6[c], 6) for c in text.ljust(chars, " "))


def f32_bits(x):
    """A double narrowed to the nearest IEEE single, most significant byte first, as bits."""
    return ubits(int.from_bytes(struct.pack(">f", x), "big"), 32)


def sc_speed(speed_ms):
    """f32scale:1/10 encode (ruling 1 of 0.5): (x - 0) * 10 / 1 in doubles, then as f32."""
    return f32_bits((speed_ms - 0.0) * 10 / 1)


def sc_report(time_us=None, lat=None, lon=None, speed_ms=None, lane_offset_m=None, unit_code=None,
              sector=None, callsign=None, kind=60, raw_lat=None, raw_lon=None, raw_offset=None,
              raw_speed=None, raw_callsign=None):
    """xtdl-scaled-example. An absent key writes zero bits, or its no-value code where
    the pack has one; a raw_* argument writes those bits as they are."""
    def pos(value, raw):
        if raw is not None:
            return ubits(raw, 32)
        return ubits(SC_NO_POS, 32) if value is None else smag_bits(deg7(value), 32)
    bits = ubits(kind, 8) + ubits(time_us or 0, 56) + pos(lat, raw_lat) + pos(lon, raw_lon)
    if raw_speed is not None:
        bits += ubits(raw_speed, 32)
    else:
        bits += ubits(0, 32) if speed_ms is None else sc_speed(speed_ms)
    if raw_offset is not None:
        bits += ubits(raw_offset, 12)
    else:
        bits += ubits(0, 12) if lane_offset_m is None else smag_bits(lane_offset_m, 12)
    bits += ubits(0 if unit_code is None else int(unit_code, 8), 12)
    bits += ubits(sector or 0, 8)
    if raw_callsign is not None:
        bits += ubits(raw_callsign, 48)
    else:
        bits += icao6_text(callsign or "", 8)
    assert len(bits) == 240
    return int(bits, 2).to_bytes(30, "big").hex()


def j(members):
    """Canonical JSON text: members in the order given, no whitespace."""
    return json.dumps(members, separators=(",", ":"))


def j_contacts(contacts):
    return [{"id": i, "bearing_deg": b, "range_m": r} for i, b, r in contacts]


# One position report and one contact report, used by every vector.
P = dict(sector=19, day_s=72000, lat=35.25, lon=10.5, status="active")      # 20:00:00 UTC
CONTACTS = [(12, 90, 1500), (200, 225, 12000)]
C = dict(sector=7, day_s=3600, contacts=CONTACTS)                            # 01:00:00 UTC
AR = dict(sector=19, lat=35.25, lon=10.5, callsign="XT-19", speed_ms=12.5)
SC_T = 1614456000000 * 1000                                                    # 2021-02-27T20:00:00Z in microseconds
SCR = dict(time_us=SC_T, lat=35.25, lon=10.5, speed_ms=12.5, lane_offset_m=-3, unit_code="0412",
           sector=19, callsign="XT19")
SET = dict(time_ms=1614456000000, callsign="XT-19", lat=35.25, lon=10.5, sector=19, speed_ms=12.5)  # 2021-02-27T20:00:00Z

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
    (S, "01-roundtrip", dict(
        to=S, input=s_set(**SET), expect=s_set(**SET),
        model={"time_ms": "1614456000000", "callsign": "XT-19", "lat": "35.25", "lon": "10.5",
               "xtdl.sector": "19", "speed_ms": "12.5"})),
    (S, "02-unknown-item-kept-as-residue", dict(
        to=S, input=s_set(**SET, residue=tlv_item(9, b"\xab\xcd")),
        expect=s_set(**SET, residue=tlv_item(9, b"\xab\xcd")))),
    (S, "03-from-geojson", dict(
        from_="geojson", to=S,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                 "properties": {"time_ms": 1614456000000, "speed_ms": 12.5}}),
        expect=s_set(time_ms=1614456000000, lat=35.25, lon=10.5, speed_ms=12.5))),
    (S, "04-to-xtdl-track", dict(
        to=T, input=s_set(**SET), expect=t_track(35.25, 10.5, 12.5, 19))),
    (S, "05-long-callsign-long-form-lengths", dict(
        to=S, input=s_set(**dict(SET, callsign="X" * 200)),
        expect=s_set(**dict(SET, callsign="X" * 200)))),
    (S, "06-bad-checksum", dict(
        to=S, input=s_set(**SET)[:-2] + "00", expect_error="malformed-wire")),
    (S, "07-empty-nested-set-not-written", dict(
        from_=T, to=S, input=t_track(35.25, 10.5, None, None),
        expect=s_set(lat=35.25, lon=10.5))),
    (A, "01-roundtrip", dict(
        to=A, input=a_position(**AR), expect=a_position(**AR),
        model={"@kind": "position", "xtdl.sector": "19", "lat": "35.25", "lon": "10.5",
               "callsign": "XT-19", "speed_ms": "12.5"})),
    (A, "02-no-speed-is-19-characters", dict(
        to=A, input=a_position(**dict(AR, speed_ms=None)), expect=a_position(**dict(AR, speed_ms=None)),
        model={"@absent": ["speed_ms"]})),
    (A, "03-fill-bits-ignored", dict(
        # 114 bits: four fill bits in the last character, set here, written back as zero
        to=A, input=a_position(**dict(AR, speed_ms=None), fill="1111"),
        expect=a_position(**dict(AR, speed_ms=None)))),
    (A, "04-no-position-codes-read-absent", dict(
        to=A, input=a_position(**dict(AR, lat=None, lon=None)),
        expect=a_position(**dict(AR, lat=None, lon=None)),
        model={"@absent": ["lat", "lon"], "callsign": "XT-19"})),
    (A, "05-southern-western", dict(
        to=A, input=a_position(**dict(AR, lat=-35.25, lon=-10.5)),
        expect=a_position(**dict(AR, lat=-35.25, lon=-10.5)),
        model={"lat": "-35.25", "lon": "-10.5"})),
    (A, "06-to-xtdl-track", dict(
        to=T, input=a_position(**AR), expect=t_track(35.25, 10.5, 12.5, 19))),
    (A, "07-character-outside-the-armor", dict(
        to=A, input=a_position(**AR)[:-1] + "X", expect_error="malformed-wire")),
    (A, "08-too-short", dict(
        to=A, input=a_position(**AR)[:10], expect_error="malformed-wire")),
    (A, "09-unknown-message-type", dict(
        to=A, input=a_position(**dict(AR, kind=8)), expect_error="no-kind")),
    (SC, "01-roundtrip", dict(
        to=SC, input=sc_report(**SCR), expect=sc_report(**SCR),
        model={"@kind": "report", "time_ms": "1614456000000", "lat": "35.25", "lon": "10.5",
               "speed_ms": "12.5", "xtdl.lane_offset_m": "-3", "xtdl.unit_code": "0412",
               "xtdl.sector": "19", "callsign": "XT19"})),
    (SC, "02-half-millisecond-rounds-away-from-zero", dict(
        # 1614456000000500 us is 1614456000000.5 ms: rounds to ...001, written back as ...001000 us
        to=SC, input=sc_report(**dict(SCR, time_us=SC_T + 500)),
        expect=sc_report(**dict(SCR, time_us=SC_T + 1000)),
        model={"time_ms": "1614456000001"})),
    (SC, "03-sub-millisecond-rounds-down", dict(
        to=SC, input=sc_report(**dict(SCR, time_us=SC_T + 499)), expect=sc_report(**SCR),
        model={"time_ms": "1614456000000"})),
    (SC, "04-southern-western-and-largest-values", dict(
        to=SC, input=sc_report(**dict(SCR, lat=-35.25, lon=-10.5, lane_offset_m=-2047, unit_code="7777")),
        expect=sc_report(**dict(SCR, lat=-35.25, lon=-10.5, lane_offset_m=-2047, unit_code="7777")),
        model={"lat": "-35.25", "lon": "-10.5", "xtdl.lane_offset_m": "-2047", "xtdl.unit_code": "7777"})),
    (SC, "05-negative-zero-position-reads-absent", dict(
        to=SC, input=sc_report(**dict(SCR, lat=None, lon=None)),
        expect=sc_report(**dict(SCR, lat=None, lon=None)),
        model={"@absent": ["lat", "lon"], "callsign": "XT19"})),
    (SC, "06-negative-zero-offset-reads-0-written-with-sign-0", dict(
        to=SC, input=sc_report(**dict(SCR, lane_offset_m=None, raw_offset=0x800)),
        expect=sc_report(**dict(SCR, lane_offset_m=0)),
        model={"xtdl.lane_offset_m": "0"})),
    (SC, "07-zero-position-writes-sign-0", dict(
        to=SC, input=sc_report(**dict(SCR, lat=0.0, lon=0.0)),
        expect=sc_report(**dict(SCR, lat=0.0, lon=0.0)),
        model={"lat": "0", "lon": "0"})),
    (SC, "08-all-spaces-call-sign-reads-absent", dict(
        to=SC, input=sc_report(**dict(SCR, callsign=None)), expect=sc_report(**dict(SCR, callsign=None)),
        model={"@absent": ["callsign"]})),
    (SC, "09-call-sign-code-0-is-transform-decode", dict(
        # zero bits, as an encoder with no `absent` would write an absent call sign
        to=SC, input=sc_report(**dict(SCR, raw_callsign=0)), expect_error="transform-decode")),
    (SC, "10-speed-keeps-its-single-precision-bits", dict(
        # 123.4 as a single is 123.400001525878906 25; times 1/10 in doubles, then back
        to=SC, input=sc_report(**dict(SCR, speed_ms=12.34)), expect=sc_report(**dict(SCR, speed_ms=12.34)),
        model={"speed_ms": repr(struct.unpack(">f", struct.pack(">f", 123.4))[0] * 1 / 10)})),
    (SC, "11-speed-nan-is-transform-decode", dict(
        to=SC, input=sc_report(**dict(SCR, raw_speed=0x7FC00000)), expect_error="transform-decode")),
    (SC, "12-to-xtdl-track", dict(
        to=T, input=sc_report(**SCR), expect=t_track(35.25, 10.5, 12.5, 19))),
    (SC, "13-to-geojson", dict(
        to="geojson", input=sc_report(**SCR),
        expect=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                  "properties": {"time_ms": 1614456000000, "callsign": "XT19", "speed_ms": 12.5}}))),
    (SC, "14-from-geojson", dict(
        from_="geojson", to=SC,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                 "properties": {"time_ms": 1614456000000}}),
        expect=sc_report(time_us=SC_T, lat=35.25, lon=10.5))),
    (SC, "15-too-short", dict(
        to=SC, input=sc_report(**SCR)[:58], expect_error="malformed-wire")),
    (SC, "16-unknown-message-type", dict(
        to=SC, input=sc_report(**dict(SCR, kind=61)), expect_error="no-kind")),
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

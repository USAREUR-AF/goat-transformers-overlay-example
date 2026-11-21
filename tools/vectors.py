#!/usr/bin/env python3
"""Write the conformance vectors of this overlay's three fictional formats.

The expected bytes are computed here, from the layouts as the pack.md files
state them, with plain integer arithmetic. No engine is used: the engines are
then checked against these files (./check.sh).

  python3 tools/vectors.py           write packs/*/vectors/*.json
  python3 tools/vectors.py --check   exit 1 when a file on disk differs
"""
import json
import math
import struct
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

X, B, J = "xtdl-example", "xtdl-b-example", "xtdl-json-example"
T, TX = "xtdl-track-example", "xtdl-text-example"
F = "xtdl-flag-example"
S = "xtdl-set-example"
A = "xtdl-armor-example"
V = "xtdl-values-example"
FR = "xtdl-frame-example"
G = "xtdl-gated-example"
RP = "xtdl-report-example"
U = "xtdl-asn1-example"
SW = "xtdl-switch-example"
LI = "xtdl-list-example"
TE = "xtdl-text-ends-example"
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


def smag(value, width):
    """Sign and magnitude: the top bit is the sign (1 negative), the rest |value|."""
    return ("1" if value < 0 else "0") + ubits(abs(value), width - 1)


def icao6(text, chars):
    """6-bit characters: A-Z are 1-26, space 32, 0-9 are 48-57; padded with spaces."""
    return "".join(ubits(ord(c) - 64 if "A" <= c <= "Z" else ord(c), 6) for c in text.ljust(chars))


V_NO_LAT = 1 << 24   # xtdl-values-example: sign 1 with magnitude 0, the code for "no latitude"


def v_report(uid, lat, lon, time_us, callsign, speed_ms, lane, lat_bits=None, lon_bits=None, speed_bits=None):
    """xtdl-values-example: 216 bits, most significant first, as hex."""
    if lat_bits is None:
        lat_bits = ubits(V_NO_LAT, 25) if lat is None else smag(round(lat * 100000), 25)
    if lon_bits is None:
        lon_bits = smag(round(lon * 100000), 26)
    if speed_bits is None:
        speed_bits = ubits(struct.unpack(">I", struct.pack(">f", speed_ms * 10))[0], 32)
    bits = (ubits(int(uid, 8), 15) + lat_bits + lon_bits
            + ubits(time_us, 56)
            + icao6(callsign, 9)
            + speed_bits
            + smag(lane, 8))
    assert len(bits) == 216
    return int(bits, 2).to_bytes(27, "big").hex()


# WGS 84, as engine-spec 0.16 states it.
WGS_A = 6378137.0
WGS_F = 1 / 298.257223563
WGS_E2 = WGS_F * (2 - WGS_F)
WGS_B = WGS_A * (1 - WGS_F)


def ecef_of(lat, lon, hae):
    """Geodetic to earth-centered, earth-fixed meters."""
    phi, lam = lat * (math.pi / 180), lon * (math.pi / 180)
    n = WGS_A / math.sqrt(1 - WGS_E2 * math.sin(phi) ** 2)
    return ((n + hae) * math.cos(phi) * math.cos(lam),
            (n + hae) * math.cos(phi) * math.sin(lam),
            (n * (1 - WGS_E2) + hae) * math.sin(phi))


def geodetic_of(x, y, z):
    """Heikkinen's closed form, in the order engine-spec 0.16 gives it."""
    a, b, e2 = WGS_A, WGS_B, WGS_E2
    p = math.sqrt(x * x + y * y)
    F = 54 * b * b * z * z
    G = p * p + (1 - e2) * z * z - e2 * (a * a - b * b)
    c = e2 * e2 * F * p * p / (G ** 3)
    s_ = math.cbrt(1 + c + math.sqrt(c * c + 2 * c))
    k = s_ + 1 + 1 / s_
    P = F / (3 * k * k * G * G)
    Q = math.sqrt(1 + 2 * e2 * e2 * P)
    r0 = -P * e2 * p / (1 + Q) + math.sqrt(max(0.0, a * a / 2 * (1 + 1 / Q) - P * (1 - e2) * z * z / (Q * (1 + Q)) - P * p * p / 2))
    U = math.sqrt((p - e2 * r0) ** 2 + z * z)
    V = math.sqrt((p - e2 * r0) ** 2 + (1 - e2) * z * z)
    z0 = b * b * z / (a * V)
    h = U * (1 - b * b / (a * V))
    phi = math.atan2(z + (a * a - b * b) / (b * b) * z0, p)
    return phi * (180 / math.pi), math.atan2(y, x) * (180 / math.pi), h


def fr(t_s, t_ns, x, y, z, geoid_m=None):
    # the json wire writes an integral float without a fraction (6378137, 0)
    x, y, z = (int(v) if v == int(v) else v for v in (x, y, z))
    members = {"t_s": t_s, "t_ns": t_ns, "x": x, "y": y, "z": z}
    if geoid_m is not None:
        members["geoid_m"] = geoid_m
    return j(members)


def num(v):
    """A float as the model states it: integral values without a fraction."""
    return str(int(v)) if v == int(v) and abs(v) < 1e15 else repr(v)


def g_report(lat=None, lon=None, sector=None, lane=None, junk_position=False):
    """xtdl-gated-example: 56 bits, most significant first, as hex.

    bit 55 is 1 when a position is sent; bit 54 is 1 when bits 49-53 hold the
    lane offset instead of the sector. junk_position fills the position bits
    with ones while bit 55 says they hold nothing."""
    valid = lat is not None
    if valid:
        pos = ubits(round(lat * 50000), 24) + ubits(round(lon * 50000), 25)
    else:
        pos = "1" * 49 if junk_position else "0" * 49
    if lane is not None:
        mode, five = "1", smag(lane, 5)
    else:
        mode, five = "0", ubits(sector or 0, 5)
    bits = pos + five + mode + ("1" if valid else "0")
    assert len(bits) == 56
    return int(bits, 2).to_bytes(7, "big").hex()


def rp(uid=None, time=None, lat=None, lon=None, cls=None, confidence=None, flags=None):
    """xtdl-report-example as written: attributes and elements in line order,
    the confidence only beside a class, and an empty detail element always."""
    root = "<report"
    if uid is not None:
        root += ' id="%s"' % uid
    if time is not None:
        root += ' time="%s"' % time
    out = root + ">"
    if lat is not None:
        out += '<pos lat="%s" lon="%s"/>' % (lat, lon)
    if cls is not None:
        out += "<class" + (' confidence="%s"' % confidence if confidence is not None else "") + ">%s</class>" % cls
    if flags is not None:
        out += "<flags>%s</flags>" % flags
    return out + "<detail/></report>"


U_STATUS = {"idle": 0, "active": 1, "fault": 2, "unknown": 3}


def u_track(sector, lat, lon, status, callsign=None, speed=None, lane=None, contacts=(), addition=None):
    """xtdl-asn1-example in unaligned PER (X.691), packed here bit by bit.

    addition: the octets of one extension addition from a later version of
    the module, written after the root components (and skipped on decode)."""
    bits = "1" if addition is not None else "0"                      # extension bit
    bits += "1" if callsign is not None else "0"                     # presence of callsign
    bits += ubits(sector, 5)                                         # INTEGER (0..31)
    bits += ubits(round(lat * 10_000_000) + 900_000_000, 31)         # INTEGER (-900000000..900000000)
    bits += ubits(round(lon * 10_000_000) + 1_800_000_000, 32)       # INTEGER (-1800000000..1800000000)
    bits += ubits(U_STATUS[status], 2)                               # ENUMERATED, 4 values
    if callsign is not None:
        bits += ubits(len(callsign) - 1, 3) + "".join(ubits(ord(c), 7) for c in callsign)
    if speed is not None or lane is None:                            # CHOICE: the first alternative with content
        bits += "0" + ubits(round((speed or 0) * 10), 10)
    else:
        bits += "1" + ubits(lane + 15, 5)
    bits += ubits(len(contacts), 3)                                  # SEQUENCE (SIZE (0..4)) OF
    for ident, range_m in contacts:
        bits += ubits(ident, 8) + ubits(round(range_m / 100), 16)
    if addition is not None:
        bits += "0" + ubits(0, 6)                                    # one addition: m - 1 = 0
        bits += "1"                                                  # its presence bit
        bits += "0" + ubits(len(addition), 7)                        # open type: octet count
        bits += "".join(ubits(b, 8) for b in addition)
    bits += "0" * (-len(bits) % 8)
    return int(bits, 2).to_bytes(len(bits) // 8, "big").hex()


def sw(sector, report_type, lat=None, lon=None, speed_ms=None, lane=None):
    """xtdl-switch-example: 5 bits sector, 3 bits type, then the part the type selects."""
    bits = ubits(sector, 5) + ubits(report_type, 3)
    if report_type == 1:
        bits += ubits(round(lat * 10_000_000), 32) + ubits(round(lon * 10_000_000), 32)
    elif report_type == 2:
        bits += ubits(round(speed_ms * 10), 16)
    elif report_type in (3, 4):
        bits += smag(lane, 8)
    assert len(bits) % 8 == 0
    return int(bits, 2).to_bytes(len(bits) // 8, "big").hex()


def li(sector, speed_ms, contacts, marks, notes=b"", count=None):
    """xtdl-list-example: sector, the contact count, speed, contacts, marks with a
    last-item flag, then note bytes to the end. `count` overrides the count field."""
    bits = ubits(sector, 5) + ubits(len(contacts) if count is None else count, 3)
    bits += ubits(round(speed_ms * 10), 16)
    for ident, bearing in contacts:
        bits += ubits(ident, 8) + ubits(round(bearing * 32 / 45), 8)
    for i, code in enumerate(marks):
        bits += ("1" if i == len(marks) - 1 else "0") + ubits(code, 7)
    bits += "".join(ubits(b, 8) for b in notes)
    return int(bits, 2).to_bytes(len(bits) // 8, "big").hex()


TAG = "0123456789abcdef01234567"   # a fictional 96-bit tag


def te(sector, tag, cls, call, terminated=True):
    """xtdl-text-ends-example: sector, the tag as 24 hex digits, the class (8-bit
    characters, NUL-ended unless it fills all 6 bytes), the call sign (7-bit
    characters ended by 127), then zero bits to a whole byte."""
    bits = ubits(sector, 8) + "".join(ubits(int(d, 16), 4) for d in tag)
    body = "".join(ubits(ord(c), 8) for c in cls)
    if len(cls) < 6:
        body += ubits(0, 8)
    bits += body + "0" * (48 - len(body))
    bits += "".join(ubits(ord(c), 7) for c in call) + (ubits(127, 7) if terminated else "")
    bits += "0" * (-len(bits) % 8)
    return int(bits, 2).to_bytes(len(bits) // 8, "big").hex()


def j(members):
    """Canonical JSON text: members in the order given, no whitespace."""
    return json.dumps(members, separators=(",", ":"))


def j_contacts(contacts):
    return [{"id": i, "bearing_deg": b, "range_m": r} for i, b, r in contacts]


# One position report and one contact report, used by every vector.
P = dict(sector=19, day_s=72000, lat=35.25, lon=10.5, status="active")      # 20:00:00 UTC
CONTACTS = [(12, 90, 1500), (200, 225, 12000)]
C = dict(sector=7, day_s=3600, contacts=CONTACTS)                            # 01:00:00 UTC
FR_XYZ = ecef_of(35.25, 10.5, 100.0)
FR_GEO = geodetic_of(*FR_XYZ)
UT = dict(sector=19, lat=35.25, lon=10.5, status="active", callsign="XT19", speed=12.5,
          contacts=[(12, 1500), (200, 12000)])
VR = dict(uid="12345", lat=35.25, lon=-10.5, time_us=1614456000000000, callsign="XT19", speed_ms=12.5, lane=-3)
AR = dict(sector=19, lat=35.25, lon=10.5, callsign="XT-19", speed_ms=12.5)
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
    (V, "01-roundtrip", dict(
        to=V, input=v_report(**VR), expect=v_report(**VR),
        model={"uid": "12345", "lat": "35.25", "lon": "-10.5", "time_ms": "1614456000000",
               "callsign": "XT19", "speed_ms": "12.5", "xtdl.lane_offset_m": "-3"})),
    (V, "02-to-xtdl-track", dict(
        to=T, input=v_report(**VR), expect=t_track(35.25, -10.5, 12.5, None))),
    (V, "03-negative-zero-written-with-sign-0", dict(
        # longitude: sign bit 1 with magnitude 0 reads as 0 and is written back with sign 0
        to=V, input=v_report(**VR, lon_bits="1" + "0" * 25),
        expect=v_report(**dict(VR, lon=0)),
        model={"lon": "0"})),
    (V, "04-no-latitude-code-reads-absent", dict(
        # latitude: sign 1 with magnitude 0 is this pack's `absent` code, not a value
        to=V, input=v_report(**dict(VR, lat=None)), expect=v_report(**dict(VR, lat=None)),
        model={"@absent": ["lat"], "lon": "-10.5"})),
    (V, "05-leading-zero-octal-digits", dict(
        to=V, input=v_report(**dict(VR, uid="00017")), expect=v_report(**dict(VR, uid="00017")),
        model={"uid": "00017"})),
    (V, "06-character-outside-the-set", dict(
        # byte 16 holds the call sign's second character: code 0 is not a character of the 6-bit set
        to=V, input=v_report(**VR)[:32] + "00" + v_report(**VR)[34:], expect_error="transform-decode")),
    (V, "07-half-millisecond-rounds-away-from-zero", dict(
        # 500 microseconds is half a millisecond: engine-spec 0.15 rounds half away from zero
        to=V, input=v_report(**dict(VR, time_us=1614456000000500)),
        expect=v_report(**dict(VR, time_us=1614456000001000)),
        model={"time_ms": "1614456000001"})),
    (V, "08-sub-millisecond-rounds-down", dict(
        to=V, input=v_report(**dict(VR, time_us=1614456000000499)),
        expect=v_report(**VR),
        model={"time_ms": "1614456000000"})),
    (V, "09-sign-and-magnitude-integer", dict(
        # smag: the sign bit, then seven bits of magnitude; -127 is the most negative value
        to=V, input=v_report(**dict(VR, lane=-127)), expect=v_report(**dict(VR, lane=-127)),
        model={"xtdl.lane_offset_m": "-127"})),
    (V, "10-speed-nan-is-transform-decode", dict(
        to=V, input=v_report(**VR, speed_bits=ubits(0x7FC00000, 32)), expect_error="transform-decode")),
    (V, "11-to-geojson", dict(
        to="geojson", input=v_report(**VR),
        expect=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [-10.5, 35.25]},
                  "properties": {"time_ms": 1614456000000, "callsign": "XT19", "speed_ms": 12.5},
                  "id": "12345"}))),
    (V, "12-from-geojson", dict(
        # no id: uid writes zero bits, read back as 00000; no lane offset: zero bits
        from_="geojson", to=V,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [-10.5, 35.25]},
                 "properties": {"time_ms": 1614456000000, "callsign": "XT19", "speed_ms": 12.5}}),
        expect=v_report(**dict(VR, uid="00000", lane=0)))),
    (FR, "01-roundtrip-derives-lat-lon-hae", dict(
        to=FR, input=fr(1614456000, 500000000, *FR_XYZ, geoid_m=47.5),
        expect=fr(1614456000, 500000000, *FR_XYZ, geoid_m=47.5),
        model={"@complete": True, "time_ms": "1614456000500", "lat": num(FR_GEO[0]), "lon": num(FR_GEO[1]),
               "hae": num(FR_GEO[2]), "xtdl.h_msl_m": num(FR_GEO[2] - 47.5)})),
    (FR, "02-from-geojson-derives-ecef", dict(
        # latitude 0, longitude 0, height 0: every result is exact
        from_="geojson", to=FR,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0, 0]},
                 "properties": {"time_ms": 1614456000500}}),
        expect=fr(1614456000, 500000000, *ecef_of(0, 0, 0)))),
    (FR, "03-to-xtdl-track", dict(
        to=T, input=fr(1614456000, 500000000, *ecef_of(0, 0, 0)),
        expect=t_track(0, 0, None, None),
        model={"@complete": True, "lat": "0", "lon": "0", "hae": "0"})),
    (FR, "04-time-before-1970", dict(
        # time_ms -1: sec_of floors to -1, nsec_of gives 999000000
        from_="geojson", to=FR,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0, 0]},
                 "properties": {"time_ms": -1}}),
        expect=fr(-1, 999000000, *ecef_of(0, 0, 0)))),
    (FR, "05-nanoseconds-floor-to-milliseconds", dict(
        to=FR, input=fr(1, 1999999, *ecef_of(0, 0, 0)), expect=fr(1, 1999999, *ecef_of(0, 0, 0)),
        model={"@complete": True, "time_ms": "1001"})),
    (G, "01-roundtrip-position-and-sector", dict(
        to=G, input=g_report(35.25, 10.5, sector=19), expect=g_report(35.25, 10.5, sector=19),
        model={"lat": "35.25", "lon": "10.5", "xtdl.sector": "19", "@absent": ["xtdl.lane_offset_m"]})),
    (G, "02-position-not-valid-is-not-read", dict(
        # bit 55 is 0: the position bits are not read, and encode writes them zero
        to=G, input=g_report(sector=19, junk_position=True), expect=g_report(sector=19),
        model={"xtdl.sector": "19", "@absent": ["lat", "lon"]})),
    (G, "03-roundtrip-lane-offset", dict(
        # bit 54 is 1: bits 49-53 are the lane offset, not the sector
        to=G, input=g_report(35.25, -10.5, lane=-3), expect=g_report(35.25, -10.5, lane=-3),
        model={"xtdl.lane_offset_m": "-3", "@absent": ["xtdl.sector"]})),
    (G, "04-from-xtdl-values-sets-both-gates", dict(
        # the source has a position and a lane offset: encode sets bit 55 and bit 54
        from_=V, to=G, input=v_report(**VR), expect=g_report(35.25, -10.5, lane=-3))),
    (G, "05-from-xtdl-track-without-position", dict(
        # no-position codes in the source: bit 55 stays 0 and the position bits zero
        from_=T, to=G, input=t_track(None, None, 12.5, 19), expect=g_report(sector=19))),
    (G, "06-to-xtdl-track", dict(
        to=T, input=g_report(35.25, 10.5, sector=19), expect=t_track(35.25, 10.5, None, 19))),
    (RP, "01-roundtrip", dict(
        to=RP, input=rp("XT-19", "2021-02-27T20:00:00Z", 35.25, 10.5, "vehicle", 0.75, "positioned degraded"),
        expect=rp("XT-19", "2021-02-27T20:00:00Z", 35.25, 10.5, "vehicle", 0.75, "positioned degraded"),
        model={"@complete": True, "time_ms": "1614456000000", "xtdl.class": "vehicle",
               "xtdl.confidence": "0.75", "xtdl.degraded": "1"})),
    (RP, "02-time-with-a-fraction", dict(
        # iso8601_short writes the milliseconds without trailing zeros: .500 is .5
        to=RP, input=rp("XT-19", "2021-02-27T20:00:00.500Z"), expect=rp("XT-19", "2021-02-27T20:00:00.5Z"),
        model={"time_ms": "1614456000500"})),
    (RP, "03-confidence-without-class-is-not-written", dict(
        # decode reads the confidence; encode writes it only with a class
        to=RP, input='<report id="XT-19"><class confidence="0.75"/><detail/></report>',
        expect=rp("XT-19"),
        model={"xtdl.confidence": "0.75", "@absent": ["xtdl.class"]})),
    (RP, "04-from-geojson-builds-the-flags", dict(
        # a position sets xtdl.position_sent (0.12), and tokens turns it into the token positioned
        from_="geojson", to=RP,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                 "properties": {"time_ms": 1614456000000}, "id": "XT-19"}),
        expect=rp("XT-19", "2021-02-27T20:00:00Z", 35.25, 10.5, flags="positioned"))),
    (RP, "05-from-xtdl-track-sector-only", dict(
        # no position, sector 19: the only token is sectored
        from_=T, to=RP, input=t_track(None, None, 12.5, 19), expect=rp(flags="sectored"))),
    (RP, "06-empty-detail-is-written", dict(
        # sector 0 and no position: no token, so no flags element; detail is still written
        from_=T, to=RP, input=t_track(None, None, None, 0), expect=rp())),
    (U, "01-roundtrip", dict(
        to=U, input=u_track(**UT), expect=u_track(**UT),
        model={"xtdl.sector": "19", "lat": "35.25", "lon": "10.5", "xtdl.status": "active",
               "callsign": "XT19", "speed_ms": "12.5", "xtdl.contacts.#": "2",
               "xtdl.contacts[1].xtdl.contact_id": "200", "xtdl.contacts[1].xtdl.range_m": "12000"})),
    (U, "02-choice-lane-offset-no-callsign", dict(
        to=U, input=u_track(7, -35.25, -10.5, "fault", lane=-3), expect=u_track(7, -35.25, -10.5, "fault", lane=-3),
        model={"xtdl.lane_offset_m": "-3", "xtdl.contacts.#": "0", "@absent": ["callsign", "speed_ms"]})),
    (U, "03-extension-addition-skipped", dict(
        # a message from a later version of the module: the addition is read past and not written back
        to=U, input=u_track(**UT, addition=b"\xab\xcd"), expect=u_track(**UT))),
    (U, "04-from-xtdl-example", dict(
        # no speed, lane offset or contacts in the source: the first alternative, speed 0, and no contacts
        from_=X, to=U, input=x_position(**P), expect=u_track(19, 35.25, 10.5, "active"))),
    (U, "05-from-geojson-default-status", dict(
        from_="geojson", to=U,
        input=j({"type": "Feature", "geometry": {"type": "Point", "coordinates": [10.5, 35.25]},
                 "properties": {"callsign": "XT19", "speed_ms": 12.5}}),
        expect=u_track(0, 35.25, 10.5, "unknown", callsign="XT19", speed=12.5))),
    (U, "06-to-xtdl-track", dict(
        to=T, input=u_track(**UT), expect=t_track(35.25, 10.5, 12.5, 19))),
    (U, "07-five-contacts-do-not-fit", dict(
        # SIZE (0..4): a fifth contact is transform-encode
        from_=X, to=U, input=x_contacts(7, 3600, [(i, 90, 1500) for i in range(5)]),
        expect_error="transform-encode")),
    (SW, "01-position", dict(
        to=SW, input=sw(19, 1, lat=35.25, lon=10.5), expect=sw(19, 1, lat=35.25, lon=10.5),
        model={"xtdl.sector": "19", "xtdl.report_type": "1", "lat": "35.25", "lon": "10.5",
               "@absent": ["speed_ms", "xtdl.lane_offset_m"]})),
    (SW, "02-speed", dict(
        to=SW, input=sw(19, 2, speed_ms=12.5), expect=sw(19, 2, speed_ms=12.5),
        model={"speed_ms": "12.5", "@absent": ["lat", "lon"]})),
    (SW, "03-lane-offset-type-3", dict(
        to=SW, input=sw(7, 3, lane=-3), expect=sw(7, 3, lane=-3), model={"xtdl.lane_offset_m": "-3"})),
    (SW, "04-lane-offset-type-4-same-case", dict(
        # case 3,4: one case for two values; the type read is written back
        to=SW, input=sw(7, 4, lane=5), expect=sw(7, 4, lane=5),
        model={"xtdl.report_type": "4", "xtdl.lane_offset_m": "5"})),
    (SW, "05-other-type-reads-nothing-more", dict(
        # type 6: no case holds, else reads nothing; the report is one byte
        to=SW, input=sw(7, 6), expect=sw(7, 6),
        model={"xtdl.report_type": "6", "@absent": ["lat", "speed_ms", "xtdl.lane_offset_m"]})),
    (SW, "06-from-xtdl-track-has-no-type", dict(
        # the source has a position and a speed but no report type: type bits zero, else, one byte
        from_=T, to=SW, input=t_track(35.25, 10.5, 12.5, 19), expect=sw(19, 0))),
    (SW, "07-to-xtdl-track", dict(
        to=T, input=sw(19, 1, lat=35.25, lon=10.5), expect=t_track(35.25, 10.5, None, 19))),
    (LI, "01-roundtrip", dict(
        to=LI, input=li(19, 12.5, [(12, 90), (200, 225)], [3, 9], b"AB"),
        expect=li(19, 12.5, [(12, 90), (200, 225)], [3, 9], b"AB"),
        model={"xtdl.contacts.#": "2", "xtdl.contacts[1].xtdl.contact_id": "200",
               "xtdl.marks.#": "2", "xtdl.marks[1].xtdl.mark_code": "9",
               "xtdl.notes.#": "2", "xtdl.notes[0].xtdl.note_byte": "65", "speed_ms": "12.5"})),
    (LI, "02-no-contacts-no-note", dict(
        # count 0, one mark (its flag 1), nothing after it: the note list is present and empty
        to=LI, input=li(7, 0.5, [], [1]), expect=li(7, 0.5, [], [1]),
        model={"xtdl.contacts.#": "0", "xtdl.marks.#": "1", "xtdl.notes.#": "0"})),
    (LI, "03-count-beyond-the-message", dict(
        # the count says 3 contacts; the message holds 2 and one mark: reading runs out
        to=LI, input=li(19, 12.5, [(12, 90), (200, 225)], [3], count=3), expect_error="malformed-wire")),
    (LI, "04-to-xtdl-example-contacts", dict(
        # contacts carry over; xtdl-example's time of day and contact ranges are absent and write zero
        to=X, input=li(19, 12.5, [(12, 90), (200, 225)], [3]),
        expect=x_contacts(19, 0, [(12, 90, 0), (200, 225, 0)]))),
    (LI, "05-no-marks-cannot-be-written", dict(
        # xtdl-example's contacts report has no marks; the last-item flag needs one: transform-encode
        from_=X, to=LI, input=x_contacts(**C), expect_error="transform-encode")),
    (TE, "01-roundtrip", dict(
        to=TE, input=te(19, TAG, "jeep", "XT19"), expect=te(19, TAG, "jeep", "XT19"),
        model={"xtdl.auth_tag": TAG, "xtdl.class": "jeep", "callsign": "XT19"})),
    (TE, "02-empty-call-sign", dict(
        # the terminator straight away: the call sign is "", present
        to=TE, input=te(19, TAG, "jeep", ""), expect=te(19, TAG, "jeep", ""),
        model={"callsign": ""})),
    (TE, "03-long-call-sign", dict(
        # no fixed length: 20 characters, then 127
        to=TE, input=te(7, TAG, "boat", "XT19 ALPHA BRAVO 220"), expect=te(7, TAG, "boat", "XT19 ALPHA BRAVO 220"),
        model={"callsign": "XT19 ALPHA BRAVO 220"})),
    (TE, "04-no-terminator", dict(
        # the call sign runs to the end of the message without its 127
        to=TE, input=te(19, TAG, "jeep", "XT19", terminated=False), expect_error="malformed-wire")),
    (TE, "05-full-class-cannot-be-written", dict(
        # 6 characters fill the class field: it reads, but there is no room for the NUL on encode
        to=TE, input=te(19, TAG, "jeeps1", "XT19"), expect_error="transform-encode")),
]


# Tool vectors (engine-spec 0.23, the command-line contract; vector-format.md,
# Tool vectors). Each expected text follows from the contract and the pack
# files alone, never from an engine's output: list-formats from the `format`,
# `version` and `wire` lines; capability and matrix from ruling 6 of 0.11
# (the mapped keys of each pack, in the order of first appearance).


def pack_lines(pack):
    with open(os.path.join(ROOT, "packs", pack, "pack.def"), encoding="utf-8") as f:
        for line in f:
            t = line.split("#")[0].split()
            if t:
                yield t


def pack_header(pack):
    head = {}
    for t in pack_lines(pack):
        if t[0] in ("format", "version", "wire") and t[0] not in head:
            head[t[0]] = " ".join(t[1:]).strip('"')
    return head


def model_keys(pack):
    """Ruling 6a and 6b: field and also lines map a key; a group adds <list>[]
    and prefixes the keys inside it until its `end`."""
    keys, prefix = [], []
    def add(entry):
        if entry not in keys:
            keys.append(entry)
    for t in pack_lines(pack):
        if t[0] in ("field", "also"):
            add("".join(prefix) + t[1])
        elif t[0] == "group":
            add("".join(prefix) + t[1] + "[]")
            prefix.append(t[1] + "[].")
        elif t[0] == "end" and prefix:
            prefix.pop()
    return keys


def capability_line(a, b):
    """Ruling 6d and 6e, as one matrix line of 0.23."""
    ka, kb = model_keys(a), model_keys(b)
    carried = [k for k in ka if k in kb]
    dropped = [k for k in ka if k not in kb]
    grade = "none" if not carried else ("full" if not dropped else "partial")
    return "\t".join([pack_header(a)["format"], pack_header(b)["format"], grade,
                      " ".join(carried), " ".join(dropped)]) + "\n"


def tool_vectors():
    two = sorted([X, J], key=lambda p: pack_header(p)["format"].encode())
    listing = "".join("%s\t%s\t%s\n" % (h["format"], h["version"], h["wire"])
                      for h in map(pack_header, two))
    matrix = "from\tto\tgrade\tcarried\tdropped\n" + "".join(
        capability_line(a, b) for a in two for b in two)
    geojson = '{"type":"Feature","geometry":{"type":"Point","coordinates":[10.5,35.25]},"properties":{"time_ms":1614456000000}}'
    # 1614456000000 ms is 20:00:00, day second 72000; sector 0 and status unknown
    # are what xtdl-example writes for a GeoJSON point (README, What carries)
    position = x_position(0, 72000, 35.25, 10.5, "unknown")
    assert position == "0140190120b90215402c420653"   # the conversion check.sh shows
    packs = ["--packs", "{packs}"]
    return [
        ("01-list-formats-two-overlay-formats", dict(
            args=["list-formats", "--packs-only", "%s,%s" % (X, J)] + packs, exit=0, stdout_text=listing)),
        ("02-matrix-two-overlay-formats", dict(
            args=["matrix", "--packs-only", "%s,%s" % (X, J)] + packs, exit=0, stdout_text=matrix)),
        ("03-capability-overlay-to-overlay", dict(
            args=["capability", "--from", J, "--to", X, "--packs-only", "%s,%s" % (J, X)] + packs,
            exit=0, stdout_text=capability_line(J, X))),
        ("04-convert-public-to-overlay", dict(
            args=["convert", "--from", "geojson", "--to", X, "--packs-only", "geojson," + X] + packs,
            stdin_hex=geojson.encode().hex(), exit=0, stdout_text=position)),
        ("05-public-only-engine-refuses-the-overlay", dict(
            # engine-spec 0.4: a controlled module is refused by a public-only engine
            args=["list-formats", "--packs-only", X, "--max-distribution", "public"] + packs,
            exit=1, error_kind="distribution-refused")),
        ("06-usage-error-before-loading", dict(
            # a trailing comma leaves an empty name: usage error 10, exit 2
            args=["matrix", "--packs-only", X + ","] + packs, exit=2)),
    ]


# Tool vectors for a build with only the `json` and `geojson` wires (engine-spec
# 0.24): the json format loads as in a full build (ruling 1b), and a pack on a
# wire the build lacks is `unknown-wire` (ruling 1c). check.sh builds the engine
# with `--no-default-features --features json,geojson` to run them.
REDUCED_WIRES = ("json", "geojson")


def reduced_tool_vectors():
    T = "xtdl-text-example"
    assert pack_header(J)["wire"] in REDUCED_WIRES
    assert pack_header(X)["wire"] not in REDUCED_WIRES and pack_header(T)["wire"] not in REDUCED_WIRES
    h = pack_header(J)
    packs = ["--packs", "{packs}"]
    return [
        ("01-json-format-loads", dict(
            args=["list-formats", "--packs-only", J] + packs, exit=0,
            stdout_text="%s\t%s\t%s\n" % (h["format"], h["version"], h["wire"]))),
        ("02-json-format-capability-unchanged", dict(
            args=["matrix", "--packs-only", J] + packs, exit=0,
            stdout_text="from\tto\tgrade\tcarried\tdropped\n" + capability_line(J, J))),
        ("03-bits-format-is-unknown-wire", dict(
            args=["list-formats", "--packs-only", X] + packs, exit=1, error_kind="unknown-wire")),
        ("04-text-format-is-unknown-wire", dict(
            args=["list-formats", "--packs-only", T] + packs, exit=1, error_kind="unknown-wire")),
        ("05-load-stops-at-the-first-missing-wire", dict(
            # packs load in the order given: the json pack loads, the bits pack fails
            args=["list-formats", "--packs-only", "%s,%s" % (J, X)] + packs, exit=1, error_kind="unknown-wire")),
    ]


# The benchmark set of engine-spec 0.25 (ruling 2) for this overlay's formats:
# the first vector with an `expect` of each pack, so it covers every wire the
# overlay uses. check.sh runs the engine's benchmark on it; no number fails a
# run, a vector whose output differs does.
BENCH_ITERATIONS = 2000


def bench_set():
    first = {}
    for pack, name, body in VECTORS:
        if pack not in first and "expect" in body:
            first[pack] = "packs/%s/vectors/%s.json" % (pack, name)
    return {"about": "The benchmark set of engine-spec 0.25 for the overlay's fictional formats: the first "
                     "vector with an expected output of each pack. Written by tools/vectors.py.",
            "iterations": BENCH_ITERATIONS,
            "vectors": [first[p] for p in sorted(first)]}


def main():
    check = "--check" in sys.argv[1:]
    stale = 0
    tools = [("tool-vectors", n, b) for n, b in tool_vectors()] + \
            [("tool-vectors-json-only", n, b) for n, b in reduced_tool_vectors()]
    for folder, name, body in tools:
        text = json.dumps(dict(name=name, **body), indent=2) + "\n"
        path = os.path.join(ROOT, folder, name + ".json")
        if check:
            on_disk = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if on_disk != text:
                print("vectors: %s differs from tools/vectors.py" % os.path.relpath(path, ROOT))
                stale += 1
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
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
    text = json.dumps(bench_set(), indent=2) + "\n"
    path = os.path.join(ROOT, "bench", "overlay-set.json")
    if check:
        on_disk = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if on_disk != text:
            print("vectors: bench/overlay-set.json differs from tools/vectors.py")
            stale += 1
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    if stale:
        return 1
    print("vectors: %d and %d tool vectors %s" % (len(VECTORS), len(tools), "match tools/vectors.py" if check else "written"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

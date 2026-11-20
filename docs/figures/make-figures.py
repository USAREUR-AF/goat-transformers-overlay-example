#!/usr/bin/env python3
"""Draw this repository's figure from the tree.

    python3 -I docs/figures/make-figures.py           # write docs/figures/*.svg
    python3 -I docs/figures/make-figures.py --check   # exit 1 if a committed figure is out of date

The figure is written twice, `<name>-light.svg` and `<name>-dark.svg`, for a
`<picture>` element. It uses the visual language of the goat-transformers hub
figure: the public ring in blue, the private overlay ring dashed in amber.
Every format name, wire, vector count, model module and key is read from the
tree (packs/*/pack.def, packs/*/vectors/, model/*.def, core.ref). The output
is deterministic. Standard library only.
"""

import glob
import os
import sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

THEMES = {
    "light": {"ink": "#1f2328", "quiet": "#59636e", "pub": "#0969da", "ovl": "#9a6700",
              "box": ".08", "hub": ".18"},
    "dark": {"ink": "#e6edf3", "quiet": "#9198a1", "pub": "#4493f8", "ovl": "#d29922",
             "box": ".14", "hub": ".28"},
}
SANS = '-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
# How a pack's `wire` (and `armor`) line is said in words.
WIRE_WORDS = {"bits": "binary", "json": "JSON", "tlv": "TLV", "text": "text line"}
NUMBER_WORDS = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight",
                9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve"}


def n(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def tw(s, size, mono=False, bold=False):
    """Text width estimate; the browser render in docs/figures/README.md confirms it."""
    if mono:
        return len(s) * size * 0.61
    w = 0.0
    for c in s:
        if c in "il.,:;|!'`1 ":
            w += 0.30
        elif c in "ft()[]/-":
            w += 0.36
        elif c in "mwMW@%":
            w += 0.86
        elif c.isupper() or c.isdigit():
            w += 0.64
        else:
            w += 0.55
    return w * size * (1.06 if bold else 1.0)


# ---------------------------------------------------------------- tree facts

def directives(path):
    """The first word and the rest of every non-comment line of a .def file."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                word, _, rest = line.partition(" ")
                out.append((word, rest.strip()))
    return out


def packs():
    found = []
    for d in sorted(glob.glob(os.path.join(ROOT, "packs", "*", "pack.def"))):
        kv = {}
        for word, rest in directives(d):
            kv.setdefault(word, rest)
        wire = WIRE_WORDS.get(kv["wire"], kv["wire"])
        if kv.get("armor") == "sixbit":
            wire = "six-bit text"
        vectors = len(glob.glob(os.path.join(os.path.dirname(d), "vectors", "*.json")))
        found.append({"name": kv["format"], "wire": wire, "vectors": vectors,
                      "distribution": kv["distribution"]})
    return found


def modules():
    found = []
    for d in sorted(glob.glob(os.path.join(ROOT, "model", "*.def"))):
        kv, keys = {}, []
        for word, rest in directives(d):
            kv.setdefault(word, rest)
            if word in ("key", "list"):
                keys.append(rest.split()[0])
        found.append({"name": kv["module"], "distribution": kv["distribution"], "keys": keys})
    return found


def public_keys():
    """Public model keys the overlay's packs map, most used first."""
    count = {}
    for d in glob.glob(os.path.join(ROOT, "packs", "*", "pack.def")):
        for word, rest in directives(d):
            key = rest.split()[0] if rest else ""
            if word in ("field", "item", "group", "derive", "default", "const") and key.replace("_", "").isalnum() \
                    and not key[0].isdigit():
                count[key] = count.get(key, 0) + 1
    return sorted(count, key=lambda k: (-count[k], k))


def core_ref():
    with open(os.path.join(ROOT, "core.ref"), encoding="utf-8") as fh:
        return fh.read().strip()[:7]


# ---------------------------------------------------------------- drawing

class SVG:
    def __init__(self, w, h, title, desc):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.items = []

    def add(self, s):
        self.items.append(s)

    def rect(self, x, y, w, h, cls, rx=8):
        self.add('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" class="%s"/>' % (n(x), n(y), n(w), n(h), n(rx), cls))

    def text(self, x, y, s, size=14, cls="ink", anchor="start", bold=False, mono=False):
        self.add('<text x="%s" y="%s" class="%s %s" font-size="%s" text-anchor="%s"%s>%s</text>'
                 % (n(x), n(y), "m" if mono else "t", cls, n(size), anchor,
                    ' font-weight="600"' if bold else "", escape(s)))

    def path(self, d, cls):
        self.add('<path d="%s" class="%s"/>' % (d, cls))

    def render(self, theme):
        t = THEMES[theme]
        style = (
            "  .ink{fill:%(ink)s} .quiet{fill:%(quiet)s} .pub{fill:%(pub)s} .ovl{fill:%(ovl)s}\n"
            "  .t{font-family:%(sans)s}\n  .m{font-family:%(mono)s}\n"
            "  .box{fill:%(pub)s;fill-opacity:%(box)s;stroke:%(pub)s;stroke-width:1.5}\n"
            "  .hub{fill:%(pub)s;fill-opacity:%(hub)s;stroke:%(pub)s;stroke-width:2}\n"
            "  .obox{fill:%(ovl)s;fill-opacity:%(box)s;stroke:%(ovl)s;stroke-width:1.5;stroke-dasharray:6 4}\n"
            "  .ring{fill:none;stroke:%(pub)s;stroke-width:1.5}\n"
            "  .oring{fill:none;stroke:%(ovl)s;stroke-width:1.5;stroke-dasharray:8 6}\n"
            "  .ln{stroke:%(pub)s;stroke-width:1.5;fill:none}\n"
            "  .oln{stroke:%(ovl)s;stroke-width:1.5;fill:none;stroke-dasharray:6 4}\n"
            % dict(t, sans=SANS, mono=MONO))
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
                'aria-labelledby="t d">\n<title id="t">%s</title>\n<desc id="d">%s</desc>\n<style>\n%s</style>\n%s\n</svg>\n'
                % (self.w, self.h, self.w, self.h, escape(self.title), escape(self.desc), style, "\n".join(self.items)))


def fig_overlay_ring():
    ps, ms, ref = packs(), modules(), core_ref()
    if len(ps) > 12:
        raise SystemExit("make-figures: %d packs; two columns of six is the most the ring holds" % len(ps))
    mod = ms[0]
    count = NUMBER_WORDS.get(len(ps), str(len(ps)))
    # hub: the shared model, public keys and the overlay's module
    ix0, ix1 = 220, 660
    cx, hy0, hw = (ix0 + ix1) / 2, 192, 284

    def rows_of(keys):
        rows = [""]
        for k in keys:
            t = (rows[-1] + " " + k).strip()
            if tw(t, 13, mono=True) <= hw - 28 or not rows[-1]:
                rows[-1] = t
            else:
                rows.append(k)
        return rows
    pub_rows, mod_rows = rows_of(public_keys()), rows_of(mod["keys"])
    if len(pub_rows) != 2 or not 1 <= len(mod_rows) <= 6:
        raise SystemExit("make-figures: key rows changed (%d public, %d module); re-lay the hub"
                         % (len(pub_rows), len(mod_rows)))
    # the module's key rows start at hy0 + 148, 18 apart, with 16 below the last
    hy1 = hy0 + 148 + 18 * (len(mod_rows) - 1) + 16
    # the captions under the hub need 70 below it and 12 above the inner ring's
    # bottom (512 on the base canvas); a taller hub makes the canvas taller
    grow = max(0, hy1 + 70 - (512 - 12))
    W, H = 880, 592 + grow
    title = "%s fictional formats fill the private overlay ring" % count
    desc = ("goat-transformers, public, at core.ref %s, holds the engines, the shared model and the public packs such as "
            "geojson. Around it, a dashed ring is this private overlay: %s fictional formats (%s) and the model module %s, "
            "all marked distribution %s. Every format connects to the same shared model. An engine started with "
            "--max-distribution public loads nothing from the overlay."
            % (ref, count.lower(), ", ".join(p["name"] for p in ps), mod["name"], mod["distribution"]))
    f = SVG(W, H, title, desc)

    # rings
    f.rect(16, 16, W - 32, H - 32, "oring", rx=18)
    f.text(34, 44, "This repository, the private overlay: %s fictional formats and the model module %s"
           % (count.lower(), mod["name"]), 14, cls="ovl", bold=True)
    iy0, iy1 = 72, 512 + grow
    f.rect(ix0, iy0, ix1 - ix0, iy1 - iy0, "ring", rx=14)
    f.text(ix0 + 18, iy0 + 28, "goat-transformers, public, at core.ref %s" % ref, 14, cls="pub", bold=True)

    hx0, hx1 = cx - hw / 2, cx + hw / 2
    cy = (hy0 + hy1) / 2

    # public packs above the hub
    pubs = [("geojson", 104), ("other public packs", 164)]
    gap = 16
    total = sum(w for _, w in pubs) + gap * (len(pubs) - 1)
    x = cx - total / 2
    for i, (name, w) in enumerate(pubs):
        bx = x + w / 2
        f.path("M%s %s L%s %s" % (n(bx), 150, n(cx - 50 + 100 * i), hy0), "ln")
        x += w + gap
    x = cx - total / 2
    for name, w in pubs:
        f.rect(x, 118, w, 32, "box")
        f.text(x + w / 2, 139, name, 14, anchor="middle")
        x += w + gap

    # overlay packs, two columns in the outer band; with an odd count the left column has one more
    left = (len(ps) + 1) // 2
    cols = (ps[:left], ps[left:])
    bw, bh, bg = 176, 52, 12

    def col_top(col):
        k = len(cols[col])
        return cy - (k * bh + (k - 1) * bg) / 2
    for col, xs in ((0, 30), (1, W - 30 - bw)):
        top, k = col_top(col), len(cols[col])
        for i, p in enumerate(cols[col]):
            y = top + i * (bh + bg)
            ey = cy - 48 + 96 * i / max(k - 1, 1)
            if col == 0:
                f.path("M%s %s L%s %s" % (n(xs + bw), n(y + bh / 2), n(hx0), n(ey)), "oln")
            else:
                f.path("M%s %s L%s %s" % (n(xs), n(y + bh / 2), n(hx1), n(ey)), "oln")
    for col, xs in ((0, 30), (1, W - 30 - bw)):
        top = col_top(col)
        for i, p in enumerate(cols[col]):
            y = top + i * (bh + bg)
            f.rect(xs, y, bw, bh, "obox")
            f.text(xs + bw / 2, y + 22, p["name"], 14, anchor="middle")
            f.text(xs + bw / 2, y + 41, "%s · %d vectors" % (p["wire"], p["vectors"]), 13, cls="quiet", anchor="middle")

    f.rect(hx0, hy0, hw, hy1 - hy0, "hub", rx=12)
    f.text(cx, hy0 + 32, "shared model", 19, anchor="middle", bold=True)
    f.text(cx, hy0 + 58, "public keys the overlay maps", 13, cls="quiet", anchor="middle", bold=True)
    f.text(cx, hy0 + 128, "module %s, %s" % (mod["name"], mod["distribution"]), 13, cls="ovl", anchor="middle", bold=True)
    for i, r in enumerate(pub_rows):
        f.text(cx, hy0 + 78 + 18 * i, r, 13, cls="quiet", anchor="middle", mono=True)
    for i, r in enumerate(mod_rows):
        f.text(cx, hy0 + 148 + 18 * i, r, 13, cls="ovl", anchor="middle", mono=True)

    # what the picture says, in the ring and below it
    f.text(cx, hy1 + 26, "Overlay packs map a public key wherever one fits,", 14, anchor="middle")
    f.text(cx, hy1 + 46, "so they convert to and from the public formats.", 14, anchor="middle")
    f.text(cx, hy1 + 70, "The engines are not copied or changed.", 14, cls="quiet", anchor="middle")
    f.text(W / 2, H - 40, "An engine started with --max-distribution public loads nothing from the dashed ring.",
           14, cls="ovl", anchor="middle")
    return f


FIGURES = [("overlay-ring", fig_overlay_ring)]


def main(argv):
    check = "--check" in argv
    stale = []
    for name, fn in FIGURES:
        fig = fn()
        for theme in THEMES:
            p = os.path.join(HERE, "%s-%s.svg" % (name, theme))
            out = fig.render(theme)
            if check:
                if not os.path.isfile(p) or open(p, encoding="utf-8").read() != out:
                    stale.append(os.path.relpath(p, ROOT))
            else:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(out)
                print(os.path.relpath(p, ROOT))
    if stale:
        print("out of date: " + ", ".join(stale) + "; run python3 -I docs/figures/make-figures.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

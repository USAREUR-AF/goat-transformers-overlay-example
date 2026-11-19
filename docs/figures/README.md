# Figures

`make-figures.py` draws the figure in this directory from the tree. Nothing in it
is typed by hand: format names, wires and vector counts come from
`packs/*/pack.def` and `packs/*/vectors/`, the module and its keys from
`model/*.def`, the public keys from the packs' `field` lines, and the library
commit from `core.ref`. It is written in a light and a dark variant for a
`<picture>` element, in the visual language of the goat-transformers hub figure:
the public library in blue, the private overlay ring dashed in amber.

```sh
python3 -I docs/figures/make-figures.py           # write the SVG files
python3 -I docs/figures/make-figures.py --check   # exit 1 if a committed file is out of date
```

| Figure | Shows |
|---|---|
| `overlay-ring` | the overlay's formats in the outer ring around the public library, all connected to one shared model; the overlay's model module and the public keys its packs map |

Regenerate after a pack, a vector, a model module or `core.ref` changes.

The figure was rendered in headless Chromium as an `<img>` at 830 px and 400 px
wide in both themes and inspected. Text is at least 13 units on an 880-unit
canvas.

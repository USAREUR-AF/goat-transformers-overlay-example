#!/usr/bin/env bash
# Assemble a working tree from the public library and this overlay.
#
#   goat-transformers at the commit in core.ref   (engines, spec, public packs)
#     + this overlay's model/ and packs/
#     = an assembled tree where the engines run the overlay's formats
#
#   ./assemble.sh <output-dir>                    fetch the library at core.ref
#   ./assemble.sh --core-dir <dir> <output-dir>   copy it from a local checkout
#
# <output-dir> must not exist or must be empty. An overlay file never replaces
# a library file: a module or pack name that the library already has is refused.
set -euo pipefail
OVERLAY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_URL="${CORE_URL:-https://github.com/USAREUR-AF/goat-transformers}"
PLACEHOLDER="0000000000000000000000000000000000000000"
MARKER=".goat-transformers-assembled"

usage() { echo "usage: assemble.sh [--core-dir DIR] <output-dir>" >&2; exit 2; }
die() { echo "assemble: $*" >&2; exit 1; }

CORE_DIR=""; OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --core-dir) [ $# -ge 2 ] || usage; CORE_DIR="$2"; shift 2 ;;
    -h|--help)  usage ;;
    -*)         usage ;;
    *)          [ -z "$OUT" ] || usage; OUT="$1"; shift ;;
  esac
done
[ -n "$OUT" ] || usage

ref="$(tr -d '[:space:]' < "$OVERLAY/core.ref")"
case "$ref" in *[!0-9a-f]*|"") die "core.ref is not a commit id" ;; esac
[ "${#ref}" -eq 40 ] || die "core.ref must be a full 40-character commit id"

if [ -e "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then
  die "$OUT exists and is not empty; give a new or empty directory"
fi

if [ -n "$CORE_DIR" ]; then
  git -C "$CORE_DIR" rev-parse --git-dir >/dev/null 2>&1 || die "$CORE_DIR is not a git checkout"
  if [ "$ref" != "$PLACEHOLDER" ] && git -C "$CORE_DIR" cat-file -e "$ref^{commit}" 2>/dev/null; then
    commit="$ref"
  else
    commit="$(git -C "$CORE_DIR" rev-parse HEAD)"
    if [ "$ref" = "$PLACEHOLDER" ]; then
      echo "assemble: core.ref is the placeholder; using HEAD of $CORE_DIR ($commit)"
    else
      echo "assemble: $CORE_DIR does not have commit $ref; using its HEAD ($commit)"
    fi
  fi
  echo "assemble: copying the library from $CORE_DIR @ $commit"
  mkdir -p "$OUT"
  git -C "$CORE_DIR" archive "$commit" | tar -x -C "$OUT"
else
  if [ "$ref" = "$PLACEHOLDER" ]; then
    echo "assemble: core.ref holds the placeholder $PLACEHOLDER, not a commit." >&2
    echo "  Do one of these:" >&2
    echo "    1. write the full commit id of $CORE_URL to build with into core.ref:" >&2
    echo "         git ls-remote $CORE_URL HEAD" >&2
    echo "    2. use a local checkout of the library at its current commit:" >&2
    echo "         ./assemble.sh --core-dir <checkout> <output-dir>" >&2
    exit 1
  fi
  commit="$ref"
  echo "assemble: fetching the library $CORE_URL @ $commit"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  git -C "$tmp" init -q
  git -C "$tmp" remote add origin "$CORE_URL"
  git -C "$tmp" fetch -q --depth 1 origin "$commit" || die "cannot fetch $commit from $CORE_URL"
  mkdir -p "$OUT"
  git -C "$tmp" archive FETCH_HEAD | tar -x -C "$OUT"
fi

# Lay the overlay's model modules and packs over the library's. A name is used
# once: an overlay file may not replace a library file.
for d in model packs; do
  [ -d "$OVERLAY/$d" ] || continue
  for src in "$OVERLAY/$d"/*; do
    [ -e "$src" ] || continue
    name="$(basename "$src")"
    [ ! -e "$OUT/$d/$name" ] || die "$d/$name exists in the library; an overlay may not replace it"
  done
done
for d in model packs; do
  [ -d "$OVERLAY/$d" ] || continue
  echo "assemble: overlaying $d/"
  mkdir -p "$OUT/$d"
  cp -R "$OVERLAY/$d/." "$OUT/$d/"
done

echo "$commit" > "$OUT/$MARKER"
echo "assemble: done -> $OUT (library commit recorded in $MARKER)"

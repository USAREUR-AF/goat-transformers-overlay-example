#!/usr/bin/env bash
# Check this overlay against the library it pins.
#
#   ./check.sh                    assemble with the commit in core.ref
#   ./check.sh --core-dir <dir>   assemble from a local checkout of the library
#
# Steps:
#   1. the vector files equal what tools/vectors.py computes
#   2. assemble.sh builds a tree from the library and this overlay
#   3. the Rust engine's tests pass on that tree (library and overlay vectors)
#   4. the engine lists the nine overlay formats
#   5. a public format converts into an overlay format
#   6. an engine limited to public content refuses the tree: distribution-refused
set -euo pipefail
OVERLAY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
usage() { echo "usage: check.sh [--core-dir DIR]" >&2; exit 2; }
fail() { echo "check: FAIL: $*" >&2; exit 1; }

ASSEMBLE_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --core-dir) [ $# -ge 2 ] || usage; ASSEMBLE_ARGS=(--core-dir "$2"); shift 2 ;;
    *)          usage ;;
  esac
done

python3 "$OVERLAY/tools/vectors.py" --check || fail "run python3 tools/vectors.py and review the difference"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
tree="$work/assembled"
"$OVERLAY/assemble.sh" ${ASSEMBLE_ARGS[@]+"${ASSEMBLE_ARGS[@]}"} "$tree"

cd "$tree/engines/rust"
overlay_vectors="$(ls "$OVERLAY"/packs/*/vectors/*.json | wc -l | tr -d ' ')"
echo "check: running the Rust engine's tests on the assembled tree ($overlay_vectors overlay vectors with the library's)"
cargo test --release 2>&1 | tee "$work/test.log" | grep -E '^(test |test result:|error)' || true
[ "${PIPESTATUS[0]}" -eq 0 ] || { cat "$work/test.log"; fail "cargo test failed on the assembled tree"; }

formats="$(cargo run --release -q -- list-formats)"
for f in xtdl-example xtdl-b-example xtdl-json-example xtdl-track-example xtdl-text-example xtdl-flag-example xtdl-set-example xtdl-armor-example xtdl-scaled-example; do
  echo "$formats" | grep -qx "$f" || fail "the engine does not list $f"
done
echo "check: the engine lists the nine overlay formats"

# A public format into an overlay format: position carries, the time of day is
# derived from time_ms, and the status is the pack's default.
geojson='{"type":"Feature","geometry":{"type":"Point","coordinates":[10.5,35.25]},"properties":{"time_ms":1614456000000}}'
want="0140190120b90215402c420653"
got="$(printf '%s' "$geojson" | cargo run --release -q -- convert --from geojson --to xtdl-example)"
[ "$got" = "$want" ] || fail "geojson to xtdl-example gave $got, expected $want"
echo "check: geojson -> xtdl-example gives $got"

set +e
refusal="$(cargo run --release -q -- list-formats --max-distribution public 2>&1)"
status=$?
set -e
[ "$status" -ne 0 ] || fail "an engine limited to public content loaded the overlay"
echo "$refusal" | grep -q 'distribution-refused' || fail "expected distribution-refused, got: $refusal"
echo "check: list-formats --max-distribution public is refused (exit $status):"
echo "$refusal" | grep 'distribution-refused' | sed 's/^/  /'
echo "check: ok"

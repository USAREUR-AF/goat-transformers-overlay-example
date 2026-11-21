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
#   4. the engine lists the sixteen overlay formats
#   5. a public format converts into an overlay format
#   6. an engine limited to public content refuses the tree: distribution-refused
#   7. the library's tool vectors (the command-line contract, engine-spec 0.23)
#      pass on the assembled tree, but for the one that a controlled module
#      must fail, and the overlay's own tool vectors (tool-vectors/) pass
#   8. an engine built with only the json and geojson wires (engine-spec 0.24)
#      loads the json overlay format and refuses the others with unknown-wire
#      (tool-vectors-json-only/)
#   9. the engine's benchmark (engine-spec 0.25) runs the overlay's set
#      (bench/overlay-set.json): every output matches its vector; the timings
#      are printed and never fail the run
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
# The test binaries record the tree's path when they are built, so a target
# directory shared with an earlier run would test that run's (deleted) tree.
export CARGO_TARGET_DIR="$work/target"
overlay_vectors="$(ls "$OVERLAY"/packs/*/vectors/*.json | wc -l | tr -d ' ')"
echo "check: running the Rust engine's tests on the assembled tree ($overlay_vectors overlay vectors with the library's)"
# Keep cargo's own exit status: a `|| true` after a pipeline would reset PIPESTATUS.
set +e
cargo test --release > "$work/test.log" 2>&1
test_status=$?
set -e
grep -E '^(test |test result:|error)' "$work/test.log" || true
[ "$test_status" -eq 0 ] || { cat "$work/test.log"; fail "cargo test failed on the assembled tree"; }

# list-formats writes format<TAB>version<TAB>wire (engine-spec 0.23)
formats="$(cargo run --release -q -- list-formats | cut -f1)"
for f in xtdl-example xtdl-b-example xtdl-json-example xtdl-track-example xtdl-text-example xtdl-flag-example xtdl-set-example xtdl-armor-example xtdl-values-example xtdl-frame-example xtdl-gated-example xtdl-report-example xtdl-asn1-example xtdl-switch-example xtdl-list-example xtdl-text-ends-example; do
  grep -qx "$f" <<<"$formats" || fail "the engine does not list $f"
done
echo "check: the engine lists the sixteen overlay formats"

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
grep -q 'distribution-refused' <<<"$refusal" || fail "expected distribution-refused, got: $refusal"
echo "check: list-formats --max-distribution public is refused (exit $status):"
echo "$refusal" | grep 'distribution-refused' | sed 's/^/  /'

# The command-line contract. The library's vector 010 loads one public pack with
# --max-distribution public; in an overlay tree the controlled module in model/
# is refused first, which is step 6 again. Every other library vector must pass.
tool="$CARGO_TARGET_DIR/release/goat-xf"
cd "$tree"
set +e
library_tools="$(python3 -I tools/tool-vectors.py -- "$tool" 2>&1)"
set -e
unexpected="$(grep '^FAIL ' <<<"$library_tools" | grep -v '^FAIL 010-max-distribution-public-loads-a-public-pack.json: .*distribution-refused' || true)"
[ -z "$unexpected" ] || { echo "$library_tools"; fail "library tool vectors failed: $unexpected"; }
echo "check: library $(tail -n 1 <<<"$library_tools") (010 is refused: the overlay's module is controlled)"
python3 -I tools/tool-vectors.py --vectors "$OVERLAY/tool-vectors" -- "$tool" \
  || fail "the overlay's tool vectors failed"

# A build with fewer wires (engine-spec 0.24): only json and geojson.
echo "check: building the engine with only the json and geojson wires"
(cd "$tree/engines/rust" && CARGO_TARGET_DIR="$work/target-json" \
  cargo build --release -q --no-default-features --features json,geojson) \
  || fail "the build with only json and geojson failed"
json_tool="$work/target-json/release/goat-xf"
python3 -I tools/tool-vectors.py --vectors "$OVERLAY/tool-vectors-json-only" -- "$json_tool" \
  || fail "the overlay's json-only tool vectors failed"
set +e
missing="$("$json_tool" list-formats --packs "$tree/packs" --packs-only xtdl-example 2>&1)"
set -e
grep -q 'unknown-wire' <<<"$missing" && grep -q 'bits' <<<"$missing" \
  || fail "a bits pack on the json-only build should be unknown-wire naming bits, got: $missing"
echo "check: the json-only build refuses xtdl-example:"
echo "  $(head -n 1 <<<"$missing")"

# The benchmark of engine-spec 0.25 on the overlay's own set, from the tree root.
cd "$tree"
bench="$(cargo run --release -q --manifest-path engines/rust/Cargo.toml --example bench -- "$OVERLAY/bench/overlay-set.json")" \
  || fail "the benchmark found an output that differs from its vector"
want=$(( $(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["vectors"]))' "$OVERLAY/bench/overlay-set.json") + 1 ))
got="$(grep -c '^{' <<<"$bench")"
[ "$got" -eq "$want" ] || fail "the benchmark printed $got lines, expected $want (one per vector, one for the load)"
echo "check: benchmark of the overlay set ($((want - 1)) vectors, every output as expected):"
tail -n 1 <<<"$bench" | sed 's/^/  /'
echo "check: ok"

#!/usr/bin/env bash
# Fetch the OASIS DITA 1.3 grammars (DTD and RELAX NG) and their XML catalog from the
# DITA-OT source repository, pinned to a release, into .grammar/ (git-ignored).
#
#   tools/fetch_grammar.sh            # then: export XML_CATALOG_FILES="$PWD/.grammar/catalog.xml"
#
# Why from the DITA-OT repo: it ships the OASIS grammars as the org.oasis-open.dita.v1_3
# plug-in, with a catalog that maps every public ID to a local file, so validation never
# touches the network.
set -euo pipefail
DITA_OT_TAG="${DITA_OT_TAG:-4.4.1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/.grammar"
PLUGIN=src/main/plugins/org.oasis-open.dita.v1_3

if [ -f "$DEST/catalog.xml" ]; then echo "$DEST/catalog.xml"; exit 0; fi
TMP="$(mktemp -d)"
git clone -q --depth 1 --branch "$DITA_OT_TAG" --filter=blob:none --sparse \
  https://github.com/dita-ot/dita-ot "$TMP/dita-ot"
git -C "$TMP/dita-ot" sparse-checkout set "$PLUGIN" >/dev/null
rm -rf "$DEST" && mkdir -p "$DEST"
cp -R "$TMP/dita-ot/$PLUGIN/." "$DEST/"
rm -rf "$TMP"
echo "$DEST/catalog.xml"

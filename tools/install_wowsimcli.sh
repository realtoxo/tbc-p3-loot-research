#!/usr/bin/env bash
# Install the wowsims TBC command line simulator into a gitignored directory.
#
# WHY A SCRIPT AND NOT A README LINE. `tools/run_sims.py` shells out to
# wowsimcli, and until it exists every sim result in this repository is
# hypothetical. The binary is 5 MB and platform specific, so it cannot be
# committed, and a hand-typed download is the kind of step that gets done
# slightly differently by each person and then explains a result nobody can
# reproduce.
#
# THE VERSION IS PINNED AND RECORDED. A simulator is a measuring instrument, and
# two runs from two versions are not comparable. Pass a tag to override, but the
# default is written down so a figure can name the build that produced it.
#
# THE BINARY IS NOT THE DATABASE. wowsimcli carries its own item data compiled
# in, which is a different copy from the db.json this repository reads for
# items.csv. If the two ever disagree about an item, that disagreement is a
# finding and not a rounding error.
#
# Usage:
#   tools/install_wowsimcli.sh              # the pinned version
#   tools/install_wowsimcli.sh v0.0.117     # a specific tag
#   tools/install_wowsimcli.sh latest       # whatever is newest right now

set -euo pipefail

REPO="wowsims/tbc-new"
PINNED="v0.0.116"
DEST="vendor/wowsims"

TAG="${1:-$PINNED}"

cd "$(dirname "$0")/.."

# THE ASSET NAME IS BUILT FROM THE HOST, because picking the wrong one gives a
# binary that fails with a format error rather than a useful message. Release
# assets are named wowsimcli-<arch>-<os>.zip, with Windows the odd one out.
case "$(uname -s)" in
  Darwin) OS="darwin" ;;
  Linux)  OS="linux" ;;
  *) echo "install_wowsimcli.sh: unsupported operating system $(uname -s)." >&2
     echo "  Releases exist for darwin, linux and windows. Download by hand" >&2
     echo "  from https://github.com/${REPO}/releases and unzip into ${DEST}." >&2
     exit 1 ;;
esac

case "$(uname -m)" in
  arm64|aarch64) ARCH="arm64" ;;
  x86_64|amd64)  ARCH="amd64" ;;
  *) echo "install_wowsimcli.sh: unsupported architecture $(uname -m)." >&2
     exit 1 ;;
esac

ASSET="wowsimcli-${ARCH}-${OS}.zip"

# LINUX SHIPS AMD64 ONLY at the pinned release, so an arm64 Linux host would ask
# for an asset that does not exist. Say that plainly rather than let the
# download fail on a 404 the reader has to interpret.
if [ "$OS" = "linux" ] && [ "$ARCH" = "arm64" ]; then
  echo "install_wowsimcli.sh: the release publishes wowsimcli for linux on" >&2
  echo "  amd64 only. Build from source, or run the amd64 build under" >&2
  echo "  emulation." >&2
  exit 1
fi

echo "wowsimcli ${TAG} for ${OS}/${ARCH}"

if ! command -v gh >/dev/null 2>&1; then
  echo "install_wowsimcli.sh: the gh command line tool is not installed." >&2
  echo "  Install it, or download ${ASSET} by hand from" >&2
  echo "  https://github.com/${REPO}/releases/tag/${TAG} and unzip into ${DEST}." >&2
  exit 1
fi

mkdir -p "$DEST"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ "$TAG" = "latest" ]; then
  TAG="$(gh release view --repo "$REPO" --json tagName --jq .tagName)"
  echo "  latest resolves to ${TAG}"
fi

echo "  downloading ${ASSET}"
gh release download "$TAG" --repo "$REPO" --pattern "$ASSET" --dir "$WORK" --clobber

unzip -q -o "$WORK/$ASSET" -d "$WORK"

# THE ARCHIVE'S LAYOUT IS NOT PROMISED. Find the executable rather than assume
# it sits at the root under a particular name, so a repackaged release does not
# silently install nothing.
BIN="$(find "$WORK" -type f -name 'wowsimcli*' ! -name '*.zip' | head -1)"
if [ -z "$BIN" ]; then
  echo "install_wowsimcli.sh: no wowsimcli executable inside ${ASSET}." >&2
  echo "  The archive layout changed. Look inside it and update this script." >&2
  exit 1
fi

install -m 755 "$BIN" "$DEST/wowsimcli"

# PROVE IT RUNS BEFORE CLAIMING SUCCESS. An unusable binary that reports
# "installed" is worse than a failed download, because the failure then surfaces
# in the middle of a sim run.
if ! "$DEST/wowsimcli" --help >/dev/null 2>&1; then
  echo "install_wowsimcli.sh: ${DEST}/wowsimcli installed but will not run." >&2
  echo "  On macOS this is usually Gatekeeper. Try:" >&2
  echo "    xattr -d com.apple.quarantine ${DEST}/wowsimcli" >&2
  exit 1
fi

# The version that produced a figure has to be recoverable from the repository,
# not from someone's shell history.
printf '%s\n' "$TAG" > "$DEST/VERSION"

echo "installed ${DEST}/wowsimcli (${TAG})"
echo "  ${DEST} is gitignored; the binary is never committed"

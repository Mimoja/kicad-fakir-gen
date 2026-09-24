#!/usr/bin/env bash
set -euo pipefail

FAKIR_REF="${FAKIR_REF:-main}"
FAKIR_ZIP_URL="${FAKIR_ZIP_URL:-https://github.com/Mimoja/kicad-fakir-gen/archive/refs/heads/$FAKIR_REF.zip}"

# FAKIR_HOME points at a checkout instead of downloading one; that is how
# the generator's own tests and CI run against the working tree.
REPO="${FAKIR_HOME:-}"

NAME="fakir"
PROJECT=""
FORCE=0
MAKE_ENV=1

die()  { printf 'error: %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*"; }

usage() {
    cat <<'EOF'
Fakir board generator setup script. Point it at a KiCad project and it will create a fakir project for you

  ./install.sh                 
  ./install.sh ~/boards/Widget 

options:
  --name NAME     folder and fixture name (default: fakir)
  --force         overwrite an existing fixture folder
  --no-env        do not create the Python environment
  -h, --help      this
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --name)        NAME="${2:-}"; shift 2 ;;
        --force)       FORCE=1; shift ;;
        --no-env)      MAKE_ENV=0; shift ;;
        -h|--help)     usage; exit 0 ;;
        -*)            die "unknown option: $1 (try --help)" ;;
        *)             [ -n "$PROJECT" ] && die "only one project, please"
                       PROJECT="$1"; shift ;;
    esac
done

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || die "$PYTHON not found; fakir needs Python 3"

# The trap outlives the function, so the directory cannot be local.
DOWNLOAD=""
fetch_repo() {
    DOWNLOAD="$(mktemp -d)"
    trap 'rm -rf "$DOWNLOAD"' EXIT
    note "source:  $FAKIR_ZIP_URL"
    "$PYTHON" - "$FAKIR_ZIP_URL" "$DOWNLOAD" <<'PY' || die "could not download the generator"
import io, sys, urllib.request, zipfile
url, into = sys.argv[1], sys.argv[2]
with urllib.request.urlopen(url) as response:
    zipfile.ZipFile(io.BytesIO(response.read())).extractall(into)
PY
    # a GitHub zip holds one <repo>-<ref> directory
    REPO="$DOWNLOAD/$(ls "$DOWNLOAD" | head -1)"
}

[ -n "$REPO" ] || fetch_repo
LIB="$REPO/fakir"
TEMPLATE="$REPO/template"
[ -d "$LIB" ] && [ -d "$TEMPLATE" ] || die \
"$REPO does not hold the generator (no fakir/ and template/ in it)"

# CadQuery needs Python 3.10; uv fetches one, pip has to find it here.
supports_cadquery() {
    command -v "$1" >/dev/null 2>&1 &&
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
        >/dev/null 2>&1
}

find_modern_python() {
    for candidate in "$PYTHON" python3.14 python3.13 python3.12 python3.11 \
                     python3.10 python3; do
        if supports_cadquery "$candidate"; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

if command -v uv >/dev/null 2>&1; then
    ENV_TOOL="uv"
else
    ENV_TOOL="pip"
fi

[ -n "$PROJECT" ] || PROJECT="."

if [ -d "$PROJECT" ]; then
    SRC_DIR="$(cd "$PROJECT" && pwd)"
    # Skip fixtures we generated earlier; they are KiCad projects too.
    SRC_PRO=""
    for candidate in "$SRC_DIR"/*.kicad_pro; do
        [ -e "$candidate" ] || continue
        grep -q 'generated_by_fakir' "$candidate" && continue
        SRC_PRO="$candidate"
        break
    done
    if [ -z "$SRC_PRO" ]; then
        if [ -f "$SRC_DIR/config.yaml" ] && [ -d "$SRC_DIR/fakir_tools" ]; then
            die "$SRC_DIR is a fixture folder, not a project; run the installer from the project instead"
        fi
        die "no .kicad_pro in $SRC_DIR"
    fi
elif [ -f "$PROJECT" ]; then
    SRC_DIR="$(cd "$(dirname "$PROJECT")" && pwd)"
    case "$PROJECT" in
        *.kicad_pro) SRC_PRO="$SRC_DIR/$(basename "$PROJECT")" ;;
        *.kicad_pcb) SRC_PRO="$SRC_DIR/$(basename "${PROJECT%.kicad_pcb}").kicad_pro" ;;
        *) die "$PROJECT is not a KiCad project" ;;
    esac
else
    die "no such file or directory: $PROJECT"
fi

SRC_NAME="$(basename "${SRC_PRO%.kicad_pro}")"
[ -f "$SRC_DIR/$SRC_NAME.kicad_pcb" ] || die "no board next to $SRC_PRO"

DEST="$SRC_DIR/$NAME"
note "project: $SRC_NAME  ($SRC_DIR)"

if [ -f "$DEST/fakir/__init__.py" ] || [ "$DEST" = "$REPO" ]; then
    die "$DEST is fakir's own source tree; pass --name to use another folder"
fi

if [ -e "$DEST" ] && [ "$FORCE" != 1 ]; then
    [ -f "$DEST/config.yaml" ] || die "$DEST already exists; --force to replace it"
    note "note: $DEST exists; refreshing the generator, keeping config.yaml"
fi

rm -rf "$DEST/fakir_tools"
mkdir -p "$DEST/fakir_tools"

mkdir -p "$DEST/fakir_tools/_fakir"
# tests/test_install.py fails if this list and fakir/ diverge.
for f in __init__.py config.py sexpr.py model.py pogo.py screws.py stock.py \
         geometry.py extract.py project.py emit.py workflow.py spec.py \
         parts.py body.py kicadcli.py; do
    [ -f "$LIB/$f" ] || die "missing library module: $f"
    cp "$LIB/$f" "$DEST/fakir_tools/_fakir/$f"
done

cp "$TEMPLATE/fakir_tools/generate.py" "$DEST/fakir_tools/generate.py"
cp "$TEMPLATE/generate.sh"             "$DEST/generate.sh"
cp "$TEMPLATE/gitignore"                   "$DEST/.gitignore"
chmod +x "$DEST/generate.sh"

# Leftovers from older layouts.
rm -rf "$DEST/tools" "$DEST/_fakir"
rm -f  "$DEST/generate_pcb.py" "$DEST/generate_pcb.sh" "$DEST/generate_3d.sh" \
       "$DEST/run" "$DEST/config.py" \
       "$DEST/pyproject.toml" "$DEST/uv.lock"

SLUG="$(printf '%s' "$NAME" | tr '[:upper:]_' '[:lower:]-')"
REL_SRC="../$(basename "$SRC_PRO")"

fill() {  # fill <template> <destination>
    sed -e "s|@@SOURCE_PROJECT@@|$REL_SRC|g" \
        -e "s|@@SOURCE_NAME@@|$SRC_NAME|g" \
        -e "s|@@FIXTURE_NAME@@|$NAME|g" \
        -e "s|@@SLUG@@|$SLUG|g" \
        "$1" > "$2" || die "could not write $2"

    # A half-filled file would break at run time instead of here.
    [ -s "$2" ] || die "$2 came out empty"
    ! grep -q '@@' "$2" || die "$2 still has an unfilled placeholder"
}

fill "$TEMPLATE/fakir_tools/pyproject.toml" "$DEST/fakir_tools/pyproject.toml"
fill "$TEMPLATE/README.md"      "$DEST/README.md"

if [ -f "$DEST/config.yaml" ]; then
    note "kept:    $NAME/config.yaml (your settings)"
else
    fill "$TEMPLATE/config.yaml" "$DEST/config.yaml"
    note "wrote:   $NAME/config.yaml"
fi
note "copied:  $NAME/fakir_tools/ + generate.sh"

if [ "$MAKE_ENV" = 1 ]; then
    if [ "$ENV_TOOL" = uv ]; then
        note "env:     uv sync"
        ( cd "$DEST/fakir_tools" && uv sync --quiet ) || die "uv sync failed"
    else
        VENV_PYTHON="$(find_modern_python)" || die \
            "CadQuery needs Python 3.10 or newer and none was found ($PYTHON is $("$PYTHON" -V 2>&1 | cut -d' ' -f2)).
Install uv (https://docs.astral.sh/uv/), which fetches a suitable Python by itself,
or install a newer Python and re-run."
        note "env:     uv not found, using venv + pip ($VENV_PYTHON)"
        ( cd "$DEST/fakir_tools" && "$VENV_PYTHON" -m venv .venv \
          && .venv/bin/python -m pip install --quiet --upgrade pip \
          && .venv/bin/python -m pip install --quiet "cadquery>=2.5" "pyyaml>=6" ) \
          || die "could not build the environment with pip"
    fi
else
    note "env:     skipped (--no-env)"
fi

cat <<EOF

done. next:
  cd $(python3 -c "import os,sys;print(os.path.relpath(sys.argv[1]))" "$DEST")
  \$EDITOR config.yaml          # the probe, and everything else
  ./generate.sh --pcb          # PCB + schematic
  ./generate.sh --3d           # the printed parts and the stackup picture
EOF

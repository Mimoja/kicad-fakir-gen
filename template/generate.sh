#!/usr/bin/env bash
# ./generate.sh --pcb                      PCB and schematic
# ./generate.sh --3d                       printed parts, 3D models, picture
# Both flags together run one after the other.
set -euo pipefail
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fakir_tools"

if [ -x "$TOOLS/.venv/bin/python" ]; then
    exec "$TOOLS/.venv/bin/python" "$TOOLS/generate.py" "$@"
elif command -v uv >/dev/null 2>&1; then
    exec uv run --project "$TOOLS" python "$TOOLS/generate.py" "$@"
else
    echo "no environment yet: run 'uv sync' in fakir_tools/, or" >&2
    echo "'python3 -m venv fakir_tools/.venv && fakir_tools/.venv/bin/pip install cadquery pyyaml'" >&2
    exit 1
fi

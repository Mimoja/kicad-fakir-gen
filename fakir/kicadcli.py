from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional, Sequence

_CANDIDATES = (
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
    "/usr/lib/kicad/bin/kicad-cli",
    "/usr/local/bin/kicad-cli",
    r"C:\Program Files\KiCad\bin\kicad-cli.exe",
)

# Isometric from the front left, pulled back far enough to fit what stands
# above and below the board: kicad-cli frames the PCB, not its models.
# "high" quality doubles the time for a picture that looks the same.
_VIEW = ("--rotate", "'-65,0,-35'", "--zoom", "0.6", "--floor",
         "--quality", "basic", "--background", "opaque")


class KicadCliError(RuntimeError):
    pass


def find(hint: Optional[str] = None) -> str:
    for candidate in (hint, os.environ.get("FAKIR_KICAD_CLI")):
        if candidate:
            found = shutil.which(candidate) or (
                candidate if os.path.exists(candidate) else None)
            if found:
                return found
            raise KicadCliError("%s is not a kicad-cli" % candidate)
    found = shutil.which("kicad-cli")
    if found:
        return found
    for candidate in _CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise KicadCliError("kicad-cli not found; set FAKIR_KICAD_CLI")


def _run(arguments: Sequence[str], target: str, cli: Optional[str],
         timeout: float = 600.0) -> str:
    tool = find(cli)
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    try:
        done = subprocess.run([tool] + list(arguments), capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise KicadCliError("kicad-cli took longer than %.0f s" % timeout)
    except OSError as exc:
        raise KicadCliError("could not run %s: %s" % (tool, exc))
    if done.returncode != 0 or not os.path.exists(target):
        detail = (done.stderr or done.stdout or "").strip().splitlines()
        raise KicadCliError("kicad-cli failed: %s"
                            % (detail[-1] if detail else "no output"))
    return target


def up_to_date(board: str, target: str) -> bool:
    return (os.path.exists(target)
            and os.path.getmtime(target) >= os.path.getmtime(board))


def export_step(board: str, target: str, origin: Sequence[float],
                cli: Optional[str] = None) -> str:
    if not os.path.exists(board):
        raise KicadCliError("%s does not exist" % board)
    if up_to_date(board, target):
        return target
    return _run(["pcb", "export", "step", "--force", "--no-dnp",
                 "--subst-models", "--include-silkscreen",
                 "--include-soldermask",
                 "--user-origin", "%.6fx%.6fmm" % tuple(origin),
                 "-o", target, board], target, cli)


def render(board: str, target: str, size: Sequence[int],
           centre_z: float = 0.0, cli: Optional[str] = None) -> str:
    if os.path.exists(target):
        os.remove(target)
    return _run(["pcb", "render", *_VIEW,
                 "--pivot", "0,0,%.2f" % (centre_z / 10.0),      # in cm
                 "--width", str(int(size[0])),
                 "--height", str(int(size[1])), "-o", target, board],
                target, cli)

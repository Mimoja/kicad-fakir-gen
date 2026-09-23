from __future__ import annotations

import os
from typing import List

from . import pogo, project
from .model import FixtureConfig
from .spec import HolderError, spec_from_board

# What CadQuery can write and a slicer can read.
HOLDER_FORMATS = ("step", "stl", "3mf", "amf")


def holder_formats(config) -> List[str]:
    raw = config.get("render.holder_format")
    names = raw.replace(",", " ").split() if isinstance(raw, str) else raw
    chosen: List[str] = []
    for name in names:
        key = str(name).strip().lower().lstrip(".")
        if key not in HOLDER_FORMATS:
            raise HolderError("holder format %r is not one of: %s"
                              % (name, ", ".join(HOLDER_FORMATS)))
        if key not in chosen:
            chosen.append(key)
    if not chosen:
        raise HolderError("holder_format is empty")
    return chosen


def _step(text: str, path: str = "") -> None:
    print("%s %s" % (text, os.path.relpath(path)) if path else text,
          flush=True)


def render(config, folder: str) -> List[str]:
    name = project.fixture_name(folder)
    board_path = os.path.join(folder, "%s.kicad_pcb" % name)
    if not os.path.exists(board_path):
        raise HolderError("%s not found; run ./generate.sh --pcb first"
                          % board_path)

    _step("reading probe and screw positions from", board_path)
    spec = spec_from_board(board_path, config)
    for problem in spec.check():
        print("warning: %s" % problem)

    # CadQuery is only needed from here on.  Loading it takes seconds, and
    # the first time after an install or a reboot, a good deal longer.
    _step("loading CadQuery")
    try:
        from . import parts
    except ImportError as exc:
        raise HolderError("CadQuery is missing (%s); ./generate.sh uses the "
                          "fixture's own environment, which has it" % exc)

    _step("building the parts")
    printed = parts.printable(spec)
    written = []
    prints = os.path.join(folder, config.get("render.print_dir"))
    for key in holder_formats(config):
        for part, solid in printed.items():
            target = os.path.join(prints, "%s-%s.%s" % (name, part, key))
            _step("writing", target)
            written.append(parts.export(solid, target))

    target = os.path.join(prints, "plate.3mf")
    _step("writing every part on one bed to", target)
    written.append(parts.export(parts.prepare_for_printing(printed), target))

    models = os.path.join(folder, "%s.%s"
                          % (name, config.get("render.model_dir")))
    probe = pogo.get(config.get("pogo_pin"))
    footprint = FixtureConfig(pogo_key=probe.key).footprint_name
    target = os.path.join(models, "%s.step" % footprint)
    _step("writing the probe model", target)
    written.append(parts.export(parts.probe_solid(probe), target))
    return written

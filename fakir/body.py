from __future__ import annotations

import os
from typing import List

from . import kicadcli, pogo, project
from .extract import board_bbox_from_file
from .model import ASSEMBLY_PARTS, DUT_MODEL, FixtureConfig
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

    placed = {child.name: child
              for child in parts.assembly(spec, printed).children}
    for part in ASSEMBLY_PARTS:
        target = os.path.join(models, "%s.step" % part)
        if part in placed:
            _step("writing the 3D-view model", target)
            written.append(parts.export(placed[part], target))
        elif os.path.exists(target):
            _step("removing a part this config turned off:", target)
            os.remove(target)

    try:
        written += _pictures(config, folder, board_path, models,
                             spec.stack_centre)
    except kicadcli.KicadCliError as exc:
        print("warning: no stackup picture (%s)" % exc)
    return written


def _pictures(config, folder: str, board_path: str, models: str,
              centre_z: float) -> List[str]:
    written = []
    try:
        source = project.for_fixture(folder).board_path
    except project.ProjectError:
        source = None
    if source:
        with open(source, encoding="utf-8") as handle:
            min_x, min_y, max_x, max_y = board_bbox_from_file(handle.read())
        target = os.path.join(models, DUT_MODEL)
        if kicadcli.up_to_date(source, target):
            _step("keeping the model of the board under test,", target)
        else:
            _step("exporting %s with kicad-cli to" % os.path.basename(source),
                  target)
        written.append(kicadcli.export_step(
            source, target, ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)))
    if config.get("render.stackup"):
        target = os.path.join(folder, "%s-stackup.png"
                              % project.fixture_name(folder))
        _step("rendering the stack with kicad-cli to", target)
        written.append(kicadcli.render(
            board_path, target, config.get("render.stackup_size"), centre_z))
    return written

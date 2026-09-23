from __future__ import annotations

import os
import sys
from typing import Tuple

from . import emit, pogo, project, screws
from .extract import from_file, outline_segments
from .model import FixtureConfig


def config_to_fixture(config, folder: str) -> Tuple[FixtureConfig, str]:
    source = project.for_fixture(folder)
    probe = pogo.get(config.get("pogo_pin"))
    screw = screws.from_config(config)
    cfg = FixtureConfig(
        name=project.fixture_name(folder),
        side=config.get("test_point_side"),
        pogo_key=probe.key,
        screw_key=screw.key,
        drill_mm=pogo.drill_from_config(config, probe),
        board_note_top=config.get("pcb.note_top"),
        board_note_bottom=config.get("pcb.note_bottom"),
        margin_mm=screw.margin_mm,
        thickness_mm=float(config.get("pcb.thickness")),
        mount_drill_mm=screw.pcb_drill_mm,
        board_clearance_mm=float(config.get("holder.board_clearance")),
        body_border_mm=float(config.get("holder.body_border")),
        boss_mm=screw.boss_mm,
        model_dir=config.get("render.model_dir"),
    )
    return cfg, source.board_path


def regenerate_pcb(config, folder) -> int:
    folder = str(folder)
    try:
        cfg, board = config_to_fixture(config, folder)
    except project.ProjectError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    print("reading test points from %s" % os.path.relpath(board), flush=True)
    points, bbox, source_name = from_file(
        board, ref_pattern=config.get("ref_pattern"))
    cfg.source_bbox = bbox
    with open(board, encoding="utf-8") as handle:
        cfg.dut_outline = outline_segments(handle.read())

    selected = [p for p in points if p.side == cfg.side]
    if not selected:
        print("error: no test points on %s in %s" % (cfg.side, board),
              file=sys.stderr)
        return 1
    print("source: %s -- %d test point(s) on %s"
          % (source_name, len(selected), cfg.side))

    result = emit.build(selected, cfg, source_name)
    for warning in result.warnings:
        print("warning: %s" % warning, file=sys.stderr)

    for path, content in sorted(result.files.items()):
        target = os.path.join(folder, path)
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(content)
        print("wrote %s" % target)
    _prune_library(result, cfg, folder)
    return 0


def _prune_library(result, cfg: FixtureConfig, folder: str) -> None:
    library = os.path.join(folder, "%s.pretty" % cfg.footprint_lib)
    if not os.path.isdir(library):
        return
    wanted = {os.path.basename(path) for path in result.files
              if path.startswith("%s.pretty/" % cfg.footprint_lib)}
    for name in sorted(os.listdir(library)):
        if name.endswith(".kicad_mod") and name not in wanted:
            os.remove(os.path.join(library, name))
            print("removed stale %s" % os.path.join(library, name))

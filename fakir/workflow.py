from __future__ import annotations

import os
import sys
from typing import Dict, Optional, Sequence, Tuple

from . import emit, pogo, project, screws
from .extract import DEFAULT_REF_PATTERN, from_file, outline_segments
from .model import FixtureConfig

Contacts = Dict[str, Tuple[float, float]]


def config_to_fixture(config, folder: str) -> Tuple[FixtureConfig, str]:
    source = project.for_fixture(folder)
    probe = pogo.get(config.get("pogo_pin"))
    screw = screws.from_config(config)
    cfg = FixtureConfig(
        name=project.fixture_name(folder),
        side=config.get("test_point_side"),
        pogo_key=probe.key,
        drill_mm=pogo.drill_from_config(config, probe),
        screw_key=screw.key,
        board_note_top=config.get("pcb.note_top"),
        board_note_bottom=config.get("pcb.note_bottom"),
        margin_mm=float(config.get("pcb.margin")),
        thickness_mm=float(config.get("pcb.thickness")),
        solder_length_mm=float(config.get("pcb.solder_length")),
        mount_drill_mm=screw.pcb_drill_mm,
        print_board_allowance_mm=float(
            config.get("holder.print_board_allowance")),
        body_border_mm=float(config.get("holder.body_border")),
        boss_mm=screw.boss_mm,
        model_dir=config.get("render.model_dir"),
    )
    return cfg, source.board_path


def contacts_of(board_path: str) -> Contacts:
    if not os.path.exists(board_path):
        return {}
    points, _, _ = from_file(board_path, ref_pattern=DEFAULT_REF_PATTERN)
    return {p.ref: (round(p.x_mm, 4), round(p.y_mm, 4)) for p in points}


def contacts_changed(existing: Contacts, fresh: Contacts) -> Optional[str]:
    if not existing:
        return None
    gone = sorted(set(existing) - set(fresh))
    added = sorted(set(fresh) - set(existing))
    if gone or added:
        parts = []
        if added:
            parts.append("%d new (%s)" % (len(added), ", ".join(added[:5])))
        if gone:
            parts.append("%d gone (%s)" % (len(gone), ", ".join(gone[:5])))
        return "the test points have changed: " + ", ".join(parts)
    moved = [ref for ref in fresh if existing[ref] != fresh[ref]]
    if moved:
        return "%d test point(s) have moved (%s)" % (
            len(moved), ", ".join(sorted(moved)[:5]))
    return None


def _ask(prompt: str, choices: Sequence[str], stream, output) -> Optional[str]:
    if not (hasattr(stream, "isatty") and stream.isatty()):
        return None
    while True:
        print(prompt, end="", file=output)
        output.flush()
        answer = stream.readline()
        if not answer:
            print(file=output)
            return None
        answer = answer.strip().lower()
        if not answer:
            return choices[0]
        for choice in choices:
            if choice.startswith(answer):
                return choice
        print("  please answer one of: %s" % ", ".join(choices), file=output)


def regenerate_pcb(config, folder, mode: Optional[str] = None,
                   argv: Optional[Sequence[str]] = None,
                   stream=None, output=None) -> int:
    folder = str(folder)
    stream = stream or sys.stdin
    output = output or sys.stdout

    argv = list(sys.argv[1:] if argv is None else argv)
    if "--full" in argv:
        mode = "full"
    elif "--bottom" in argv:
        mode = "bottom"

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

    board_path = os.path.join(folder, "%s.kicad_pcb" % cfg.name)
    existing = contacts_of(board_path)
    fresh = {p.ref: (round(x, 4), round(y, 4)) for p, x, y in result.placed}

    if existing and mode is None:
        reason = contacts_changed(existing, fresh)
        if reason:
            print("%s, so the board has to be rebuilt in full." % reason)
            answer = _ask("Replace %s entirely? [yes/no]: " % cfg.name,
                          ("yes", "no"), stream, output)
            if answer != "yes":
                print("nothing written.")
                return 0
            mode = "full"
        else:
            print("A %s board already exists and its contacts are unchanged."
                  % cfg.name)
            answer = _ask(
                "  [bottom] refresh only the probe side, keeping your "
                "top-layer work\n"
                "  [full]   delete and rebuild everything\n"
                "  [cancel] leave it alone\n"
                "Choice [bottom]: ", ("bottom", "full", "cancel"),
                stream, output)
            if answer is None:
                print("not a terminal and no --full/--bottom given; "
                      "nothing written.", file=sys.stderr)
                return 3
            if answer == "cancel":
                print("nothing written.")
                return 0
            mode = answer

    return _write(result, cfg, folder, mode or "full")


def _write(result, cfg: FixtureConfig, folder: str, mode: str) -> int:
    for path, content in sorted(result.files.items()):
        target = os.path.join(folder, path)
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)

        if mode == "bottom" and os.path.exists(target):
            if path.endswith(".kicad_pcb"):
                with open(target, encoding="utf-8") as handle:
                    current = handle.read()
                try:
                    content = emit.merge_board(current, content, cfg)
                except ValueError as exc:
                    print("warning: could not merge %s (%s); rebuilt in full"
                          % (path, exc), file=sys.stderr)
                else:
                    with open(target, "w", encoding="utf-8") as handle:
                        handle.write(content)
                    print("refreshed the probe side of %s" % target)
                    continue
            elif path.endswith(".kicad_sch"):
                print("kept %s" % target)
                continue

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

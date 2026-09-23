from __future__ import annotations

import json
import os
from typing import Optional

GENERATED_MARKER = "generated_by_fakir"


class ProjectError(ValueError):
    pass


class Source:
    __slots__ = ("board_path", "project_path", "name")

    def __init__(self, board_path: str, project_path: Optional[str],
                 name: str):
        self.board_path = board_path
        self.project_path = project_path
        self.name = name

    def __repr__(self) -> str:
        return "Source(name=%r, board=%r)" % (self.name, self.board_path)


def is_generated(project_path: str) -> bool:
    try:
        with open(project_path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and GENERATED_MARKER in data


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _sibling_board(project_path: str) -> str:
    board = os.path.splitext(project_path)[0] + ".kicad_pcb"
    if not os.path.exists(board):
        raise ProjectError("%s has no board next to it" % project_path)
    return board


def _scan(directory: str) -> Source:
    entries = sorted(os.listdir(directory))
    projects = [e for e in entries if e.endswith(".kicad_pro")]
    boards = [e for e in entries if e.endswith(".kicad_pcb")]

    # Skip fixtures generated earlier and the boards belonging to them.
    generated = [e for e in projects
                 if is_generated(os.path.join(directory, e))]
    if generated and len(projects) > len(generated):
        projects = [e for e in projects if e not in generated]
        stems = {os.path.splitext(e)[0] for e in generated}
        boards = [e for e in boards if os.path.splitext(e)[0] not in stems]

    if len(projects) > 1:
        raise ProjectError("%s holds %d KiCad projects (%s); name the one "
                           "you want"
                           % (directory, len(projects), ", ".join(projects)))
    if projects:
        project = os.path.join(directory, projects[0])
        return Source(_sibling_board(project), project, _stem(project))
    if len(boards) > 1:
        raise ProjectError("%s holds %d boards (%s); name the one you want"
                           % (directory, len(boards), ", ".join(boards)))
    if boards:
        board = os.path.join(directory, boards[0])
        return Source(board, None, _stem(board))
    raise ProjectError("no .kicad_pro or .kicad_pcb found in %s" % directory)


def for_fixture(folder: str) -> Source:
    parent = os.path.dirname(os.path.abspath(folder))
    try:
        return _scan(parent)
    except ProjectError as exc:
        raise ProjectError("%s: %s" % (fixture_name(folder), exc)) from None


def fixture_name(folder: str) -> str:
    return os.path.basename(os.path.abspath(folder)) or "fakir"

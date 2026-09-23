from __future__ import annotations

from typing import Dict, List, Sequence


class Screw:
    __slots__ = ("key", "nominal_mm", "pcb_drill_mm", "clearance_mm",
                 "head_mm", "head_depth_mm", "insert_drill_mm",
                 "insert_depth_mm", "insert_floor_mm", "tap_mm", "boss_mm")

    def __init__(self, key: str, nominal_mm: float, pcb_drill_mm: float,
                 clearance_mm: float, head_mm: float, head_depth_mm: float,
                 insert_drill_mm: float, insert_depth_mm: float,
                 insert_floor_mm: float, tap_mm: float, boss_mm: float):
        self.key = key
        self.nominal_mm = nominal_mm
        self.pcb_drill_mm = pcb_drill_mm        # hole in the fixture PCB
        self.clearance_mm = clearance_mm        # passage through plastic
        self.head_mm = head_mm                  # counterbore for the head
        self.head_depth_mm = head_depth_mm
        self.insert_drill_mm = insert_drill_mm
        self.insert_depth_mm = insert_depth_mm
        self.insert_floor_mm = insert_floor_mm  # plastic under the insert
        self.tap_mm = tap_mm                    # drill for a self-tapped hole
        self.boss_mm = boss_mm                  # boss the insert sits in

    @property
    def margin_mm(self) -> float:
        return self.boss_mm

    def __repr__(self) -> str:
        return "Screw(%s)" % self.key


_SCREWS: Sequence[Screw] = (
    Screw("M2", 2.0, 2.2, 2.4, 3.8, 2.0, 3.2, 4.0, 2.0, 1.6, 5.0),
    Screw("M3", 3.0, 3.2, 3.4, 5.6, 3.0, 4.0, 6.0, 3.0, 2.5, 7.0),
    Screw("M4", 4.0, 4.3, 4.5, 7.0, 4.0, 5.6, 8.0, 4.0, 3.3, 9.0),
    Screw("M5", 5.0, 5.3, 5.5, 8.5, 5.0, 6.4, 9.5, 5.0, 4.2, 11.0),
)

CATALOGUE: Dict[str, Screw] = {screw.key: screw for screw in _SCREWS}

DEFAULT_KEY = "M3"


def keys() -> List[str]:
    return [screw.key for screw in _SCREWS]


def get(key: str) -> Screw:
    folded = {k.lower(): v for k, v in CATALOGUE.items()}
    try:
        return folded[str(key).strip().lower()]
    except KeyError:
        raise KeyError("unknown screw %r; choose one of: %s"
                       % (key, ", ".join(keys()))) from None


def from_config(config) -> Screw:
    return get(config.get("screw"))


def catalogue_comment() -> str:
    columns = ("PCB_HOLE", "SCREW_PASSAGE", "INSERT_BORE", "INSERT_DEPTH",
               "INSERT_FLOOR", "HEAD_BORE", "TAP", "BOSS")
    widths = [max(len(name), 5) for name in columns]
    lines = ["# %-6s %s" % ("SCREW", " ".join(
        "%*s" % (width, name) for width, name in zip(widths, columns)))]
    for screw in _SCREWS:
        values = (screw.pcb_drill_mm, screw.clearance_mm,
                  screw.insert_drill_mm, screw.insert_depth_mm,
                  screw.insert_floor_mm, screw.head_mm, screw.tap_mm,
                  screw.boss_mm)
        lines.append("# %-6s %s" % (screw.key, " ".join(
            "%*.1f" % (width, value)
            for width, value in zip(widths, values))))
    return "\n".join(lines)

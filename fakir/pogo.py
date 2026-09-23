from __future__ import annotations

import math
from typing import Dict, List, Sequence

CLEARANCE_MM = 0.15

_GRID_FINE, _GRID_COARSE, _GRID_BREAK = 0.05, 0.10, 2.0


class PogoPin:
    __slots__ = ("key", "head", "barrel_mm", "tip_mm", "length_mm",
                 "stroke_mm")

    def __init__(self, key: str, head: str, barrel_mm: float, tip_mm: float,
                 length_mm: float, stroke_mm: float):
        self.key = key
        self.head = head
        self.barrel_mm = barrel_mm
        self.tip_mm = tip_mm
        self.length_mm = length_mm
        self.stroke_mm = stroke_mm

    @property
    def drill_mm(self) -> float:
        return recommended_drill(self.barrel_mm)

    @property
    def pad_mm(self) -> float:
        return round(self.drill_mm + 0.70, 2)

    def board_height(self, pcb_thickness: float) -> float:
        return board_height(self.length_mm, self.stroke_mm, pcb_thickness)

    def guide_bore_mm(self, allowance: float = 0.0) -> float:
        return round(self.barrel_mm + allowance, 2)

    def __repr__(self) -> str:
        return "PogoPin(%s, barrel=%.2f)" % (self.key, self.barrel_mm)


def board_height(length_mm: float, stroke_mm: float,
                 pcb_thickness: float) -> float:
    preload = round(stroke_mm * 2.0 / 3.0, 2)
    return round(length_mm - pcb_thickness - preload, 2)


def snap_to_fab_grid(value: float) -> float:
    grid = _GRID_FINE if value < _GRID_BREAK else _GRID_COARSE
    return round(math.ceil(value / grid - 1e-9) * grid, 2)


def recommended_drill(barrel_mm: float,
                      clearance: float = CLEARANCE_MM) -> float:
    return snap_to_fab_grid(barrel_mm + clearance)


def drill_from_config(config, probe: PogoPin) -> float:
    return recommended_drill(probe.barrel_mm,
                             float(config.get("pcb.drill_hole_extra")))


# Barrel diameters follow the published P-series conventions.  Every probe
# is modelled as the round-head (B1) variant; the head does not affect any
# dimension the generator works out.
_PINS: Sequence[PogoPin] = (
    PogoPin("P50", "round", 0.68, 0.48, 16.40, 2.65),
    PogoPin("P75", "round", 1.02, 0.74, 16.60, 2.65),
    PogoPin("P100", "round", 1.36, 1.50, 33.40, 6.35),
    PogoPin("P125", "round", 1.67, 2.00, 33.40, 6.35),
    PogoPin("P160", "round", 2.03, 2.50, 44.50, 4.00),
)

CATALOGUE: Dict[str, PogoPin] = {pin.key: pin for pin in _PINS}

DEFAULT_KEY = "P75"


def keys() -> List[str]:
    return [pin.key for pin in _PINS]


def get(key: str) -> PogoPin:
    folded = {k.lower(): v for k, v in CATALOGUE.items()}
    for candidate in (key, key.split("-")[0]):
        try:
            return folded[candidate.strip().lower()]
        except KeyError:
            continue
    raise KeyError("unknown pogo pin %r; choose one of: %s"
                   % (key, ", ".join(keys()))) from None


def catalogue_comment() -> str:
    lines = ["# %-6s %6s %6s %6s" % ("NAME", "BARREL", "LENGTH", "STROKE")]
    for pin in _PINS:
        lines.append("# %-6s %6.2f %6.1f %6.2f"
                     % (pin.key, pin.barrel_mm, pin.length_mm, pin.stroke_mm))
    return "\n".join(lines)

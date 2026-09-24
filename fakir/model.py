from __future__ import annotations

import re
import uuid as _uuid
from dataclasses import dataclass
from typing import Optional, Tuple

from . import pogo, screws, stock

CORNER_RADIUS_MM = 3.0

ASSEMBLY_PARTS = ("holder", "lid", "caps", "key", "feet")
DUT_MODEL = "board-under-test.step"

DEFAULT_BOARD_NOTE_TOP = "Only the pogo pins on this side"
DEFAULT_BOARD_NOTE_BOTTOM = "Business logic goes on this side"

# Fixed namespace, so regenerating keeps the same UUIDs and therefore the
# same schematic <-> board links.
_NS = _uuid.UUID("6f2b1c40-9a1e-5d3a-8c77-2f1d5a6b3e90")

_REF_DIGITS = re.compile(r"(\d+)")


@dataclass(frozen=True)
class TestPoint:
    ref: str
    value: str
    x_mm: float
    y_mm: float
    rotation_deg: float = 0.0
    side: str = "F.Cu"
    net: Optional[str] = None
    source_footprint: str = ""
    source_uuid: Optional[str] = None

    @property
    def sort_key(self) -> Tuple[int, str]:
        match = _REF_DIGITS.search(self.ref)
        return (int(match.group(1)) if match else 0, self.ref)

    @property
    def label(self) -> str:
        if self.value and self.value.upper() not in ("TESTPOINT", "TP", "~"):
            return self.value
        return self.net or self.ref


@dataclass
class FixtureConfig:
    name: str = "fakir"
    side: str = "B.Cu"                       # side of the source board probed
    pogo_key: str = pogo.DEFAULT_KEY
    drill_mm: Optional[float] = None         # None: the probe's own
    screw_key: str = screws.DEFAULT_KEY
    board_note_top: str = DEFAULT_BOARD_NOTE_TOP
    board_note_bottom: str = DEFAULT_BOARD_NOTE_BOTTOM
    margin_mm: float = 6.0                   # fixture past the source board
    corner_radius_mm: float = CORNER_RADIUS_MM
    thickness_mm: float = 1.6
    solder_length_mm: float = 1.5           # barrel left under the board
    mount_drill_mm: float = 3.2
    body_border_mm: float = 2.5              # printed plate past the board
    boss_mm: float = 7.0
    print_board_allowance_mm: float = 0.5
    probe_model: bool = True                 # reference a STEP per footprint
    model_dir: str = "3dshapes"              # KiCad's folder for them
    source_bbox: Optional[Tuple[float, float, float, float]] = None
    dut_outline: Optional[list] = None       # Edge.Cuts of the source board

    mating_layer = "B.Cu"
    top_layer = "F.Cu"
    silk_layer = "B.SilkS"
    note_layer = "F.SilkS"
    fab_layer = "B.Fab"
    courtyard_layer = "B.CrtYd"

    @property
    def pogo(self) -> pogo.PogoPin:
        return pogo.get(self.pogo_key)

    @property
    def drill(self) -> float:
        if self.drill_mm is not None:
            return self.drill_mm
        return self.pogo.drill_mm

    @property
    def pad(self) -> float:
        return self.pogo.pad_mm

    @property
    def footprint_lib(self) -> str:
        return self.name

    @property
    def footprint_name(self) -> str:
        return "PogoPin_%s" % self.pogo.key.replace("-", "_")

    @property
    def footprint_id(self) -> str:
        return "%s:%s" % (self.footprint_lib, self.footprint_name)

    @property
    def assembly_name(self) -> str:
        return "Assembly"

    @property
    def assembly_id(self) -> str:
        return "%s:%s" % (self.footprint_lib, self.assembly_name)

    @property
    def board_height(self) -> float:
        return self.pogo.board_height(self.thickness_mm,
                                      self.solder_length_mm)

    @property
    def stock_mount(self):
        return stock.mounting_hole(self.mount_drill_mm)

    @property
    def mount_footprint_id(self) -> str:
        name = stock.mounting_hole_name(self.mount_drill_mm)
        if name is None:
            raise ValueError("KiCad has no MountingHole for a %.2f mm drill"
                             % self.mount_drill_mm)
        return "MountingHole:%s" % name

    @property
    def mount_inset(self) -> float:
        return self.margin_mm / 2.0

    @property
    def dut_size(self) -> Optional[Tuple[float, float]]:
        if self.source_bbox is None:
            return None
        min_x, min_y, max_x, max_y = self.source_bbox
        return (max_x - min_x, max_y - min_y)

    def uid(self, *parts: str) -> str:
        return str(_uuid.uuid5(_NS, "%s|%s" % (self.name, "|".join(parts))))

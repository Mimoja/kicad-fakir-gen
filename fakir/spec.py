from __future__ import annotations

import os
from typing import List, Optional, Sequence, Tuple

from . import pogo, project
from .extract import board_bbox_from_file, from_file
from .model import CORNER_RADIUS_MM

Point = Tuple[float, float]


class HolderError(RuntimeError):
    pass


# Everything an M3 fixes, in mm.
class Screw:
    nominal_mm = 3.0
    pcb_drill_mm = 3.2       # hole in the fixture PCB
    clearance_mm = 3.4       # passage through plastic
    head_mm = 5.6            # counterbore for the head
    head_depth_mm = 3.0
    insert_drill_mm = 4.0
    insert_depth_mm = 6.0
    insert_floor_mm = 3.0    # plastic under the insert
    tap_mm = 2.5             # drill for a self-tapped hole
    boss_mm = 7.0            # boss the insert sits in


class BodySpec:
    __slots__ = ("side", "corner_radius", "pins", "screws", "bore",
                 "probe_length", "probe_stroke", "screw", "dut_size",
                 "board_clearance", "pcb_thickness", "border", "feet",
                 "foot_height", "base_thickness", "guide_wall",
                 "threaded_inserts", "fixture_size")

    def __init__(self, side: float, corner_radius: float,
                 pins: Sequence[Point], screws: Sequence[Point], bore: float,
                 probe_length: float, probe_stroke: float,
                 dut_size: Optional[Point] = None,
                 board_clearance: float = 0.4, pcb_thickness: float = 1.6,
                 border: float = 2.5, feet: bool = True,
                 foot_height: float = 8.0, base_thickness: float = 3.0,
                 guide_wall: float = 1.1, threaded_inserts: bool = True,
                 fixture_size: Optional[Point] = None):
        self.side = side
        self.corner_radius = corner_radius
        self.pins = list(pins)
        self.screws = list(screws)
        self.bore = bore
        self.probe_length = probe_length
        self.probe_stroke = probe_stroke
        self.screw = Screw
        self.dut_size = dut_size
        self.board_clearance = board_clearance
        self.pcb_thickness = pcb_thickness
        self.border = border
        self.feet = feet
        self.foot_height = foot_height
        self.base_thickness = base_thickness
        self.guide_wall = guide_wall
        self.threaded_inserts = threaded_inserts
        self.fixture_size = fixture_size or (side, side)

    # what the probe decides

    @property
    def probe_stand(self) -> float:
        return self.probe_length - self.pcb_thickness

    @property
    def dut_height(self) -> float:
        return pogo.board_height(self.probe_length, self.probe_stroke,
                                 self.pcb_thickness)

    @property
    def guide_height(self) -> float:
        return round(self.probe_stand * 2.0 / 3.0, 2)

    @property
    def pillar_diameter(self) -> float:
        return self.bore + 2.0 * self.guide_wall

    @property
    def height(self) -> float:
        return max(self.base_thickness, self.guide_height, self.boss_height)

    # what the screw decides

    @property
    def insert_drill(self) -> float:
        return self.screw.insert_drill_mm

    @property
    def insert_depth(self) -> float:
        return self.screw.insert_depth_mm

    @property
    def insert_floor(self) -> float:
        return self.screw.insert_floor_mm

    @property
    def screw_hole(self) -> float:
        return self.screw.clearance_mm

    @property
    def head_diameter(self) -> float:
        return self.screw.head_mm

    @property
    def head_depth(self) -> float:
        return self.screw.head_depth_mm

    @property
    def boss(self) -> float:
        return self.screw.boss_mm

    @property
    def foot_diameter(self) -> float:
        return self.boss

    @property
    def boss_height(self) -> float:
        return self.insert_depth + self.insert_floor

    # the board and the plate

    @property
    def board_footprint(self) -> Optional[Point]:
        if not self.dut_size:
            return None
        return (self.dut_size[0] + self.board_clearance,
                self.dut_size[1] + self.board_clearance)

    @property
    def body_size(self) -> Point:
        if not self.dut_size:
            return (self.side, self.side)
        width, depth = self.board_footprint
        return (width + 2.0 * self.border, depth + 2.0 * self.border)

    def check(self) -> List[str]:
        out: List[str] = []
        if not self.pins:
            out.append("no probe positions; nothing to guide")
        if self.guide_height >= self.dut_height:
            out.append("the %.1f mm pillars reach the board at %.1f mm"
                       % (self.guide_height, self.dut_height))
        if self.guide_height <= self.base_thickness:
            out.append("the pillars are no taller than the %.1f mm base"
                       % self.base_thickness)
        if self.boss_height > self.dut_height:
            out.append("the %.1f mm screw bosses stand into the board at "
                       "%.1f mm" % (self.boss_height, self.dut_height))
        if self.feet and self.head_depth >= self.foot_height:
            out.append("the %.1f mm screw-head counterbore goes through a "
                       "%.1f mm foot" % (self.head_depth, self.foot_height))

        keep_out = (self.pillar_diameter + self.insert_drill) / 2.0
        for index, (sx, sy) in enumerate(self.screws, 1):
            for px, py in self.pins:
                gap = ((px - sx) ** 2 + (py - sy) ** 2) ** 0.5
                if gap < keep_out:
                    out.append("a probe is %.2f mm from screw %d, closer "
                               "than the %.2f mm the two bores need"
                               % (gap, index, keep_out))
                    break
        return out


# The size of the board under test, from the project the fixture sits in.
def _dut_size(folder: str) -> Optional[Point]:
    try:
        board = project.for_fixture(folder).board_path
    except project.ProjectError:
        return None
    with open(board, encoding="utf-8") as handle:
        bbox = board_bbox_from_file(handle.read())
    if bbox is None:
        return None
    min_x, min_y, max_x, max_y = bbox
    return (max_x - min_x, max_y - min_y)


def spec_from_board(board_path: str, config) -> BodySpec:
    with open(board_path, encoding="utf-8") as handle:
        bbox = board_bbox_from_file(handle.read())
    if bbox is None:
        raise HolderError("%s has no Edge.Cuts outline" % board_path)
    min_x, min_y, max_x, max_y = bbox
    cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0

    probes, _, _ = from_file(board_path, ref_pattern=r"^TP\d+$")
    mounts, _, _ = from_file(board_path, ref_pattern=r"^H\d+$")
    probe = pogo.get(config.get("pogo_pin"))
    allowance = float(config.get("holder.print_hole_allowance"))

    return BodySpec(
        side=max(max_x - min_x, max_y - min_y),
        fixture_size=(max_x - min_x, max_y - min_y),
        corner_radius=CORNER_RADIUS_MM,
        pins=[(p.x_mm - cx, -(p.y_mm - cy)) for p in probes],
        screws=[(p.x_mm - cx, -(p.y_mm - cy)) for p in mounts],
        bore=round(probe.guide_bore_mm(allowance), 3),
        probe_length=probe.length_mm,
        probe_stroke=probe.stroke_mm,
        dut_size=_dut_size(os.path.dirname(os.path.abspath(board_path))),
        board_clearance=float(config.get("holder.board_clearance")),
        pcb_thickness=float(config.get("pcb.thickness")),
        border=float(config.get("holder.body_border")),
        feet=bool(config.get("holder.feet")),
        foot_height=float(config.get("holder.foot_height")),
        base_thickness=float(config.get("holder.base_thickness")),
        threaded_inserts=bool(config.get("holder.threaded_inserts")),
    )

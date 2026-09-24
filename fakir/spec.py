from __future__ import annotations

import math
import os
from typing import List, Optional, Sequence, Tuple

from . import pogo, project, screws
from .extract import (board_bbox_from_file, from_file, loop_area,
                      outline_loops, outline_points)
from .model import CORNER_RADIUS_MM

Point = Tuple[float, float]

DEFAULT_SCREW = screws.get(screws.DEFAULT_KEY)


class HolderError(RuntimeError):
    pass


class BodySpec:
    __slots__ = ("side", "corner_radius", "pins", "screws", "bore",
                 "probe_length", "probe_stroke", "screw", "dut_size",
                 "board_clearance", "pcb_thickness", "border", "feet",
                 "foot_height", "base_thickness", "guide_wall",
                 "threaded_inserts", "clamp",
                 "clamp_tower_height", "cap_height", "fixture_size", "outline",
                 "outline_loop", "_holes")

    # Sizes that are the same on every fixture.
    cap_tip = 1.0            # flat at the point of a presser cap
    cap_taper = 3.5
    hinge_ear = 5.0
    key_thickness = 4.0
    key_gap = 0.6            # between the key and what it swings past
    presser_pitch = 10.0     # between the presser holes round the lid

    def __init__(self, side: float, corner_radius: float,
                 pins: Sequence[Point], screws: Sequence[Point], bore: float,
                 probe_length: float, probe_stroke: float, screw=None,
                 dut_size: Optional[Point] = None,
                 board_clearance: float = 0.8, pcb_thickness: float = 1.6,
                 border: float = 2.5, feet: bool = True,
                 foot_height: float = 8.0, base_thickness: float = 3.0,
                 guide_wall: float = 1.1, threaded_inserts: bool = True,
                 clamp: bool = True,
                 clamp_tower_height: float = 20.0, cap_height: float = 14.0,
                 fixture_size: Optional[Point] = None,
                 outline: Optional[Sequence[Point]] = None,
                 outline_loop: Optional[Sequence[Point]] = None):
        self.side = side
        self.corner_radius = corner_radius
        self.pins = list(pins)
        self.screws = list(screws)
        self.bore = bore
        self.probe_length = probe_length
        self.probe_stroke = probe_stroke
        self.screw = screw or DEFAULT_SCREW
        self.dut_size = dut_size
        self.board_clearance = board_clearance
        self.pcb_thickness = pcb_thickness
        self.border = border
        self.feet = feet
        self.foot_height = foot_height
        self.base_thickness = base_thickness
        self.guide_wall = guide_wall
        self.threaded_inserts = threaded_inserts
        self.clamp = clamp and dut_size is not None
        self.clamp_tower_height = clamp_tower_height
        self.cap_height = cap_height
        self.fixture_size = fixture_size or (side, side)
        # The board under test, centred on the origin: its outline as a
        # point cloud, and as one closed loop for cutting the wall.
        self.outline = list(outline) if outline else []
        self.outline_loop = list(outline_loop) if outline_loop else []
        self._holes: Optional[List[Point]] = None

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

    @property
    def wall_top(self) -> float:
        return self.dut_height + self.pcb_thickness / 2.0

    @property
    def ring(self) -> float:
        if not self.dut_size:
            return self.boss
        spare = (self.fixture_size[1] - self.board_footprint[1]) / 2.0
        return max(2.0, min(self.boss, spare))

    # the hinge

    @property
    def post_size(self) -> Point:
        return (max(12.0, 2.0 * self.boss), self.ring)

    def hinge_posts(self) -> List[Point]:
        if not self.dut_size or not self.screws:
            return []
        y = self.board_footprint[1] / 2.0 + self.ring / 2.0
        corner = max(abs(x) for x, _ in self.screws)
        x = corner - self.boss / 2.0 - 2.0 - self.post_size[0] / 2.0
        return [(-x, y), (x, y)]

    def hinge_ears(self) -> List[float]:
        return [x for x, _ in self.hinge_posts()]

    @property
    def hinge_diameter(self) -> float:
        return self.screw.nominal_mm + 2.4

    @property
    def hinge_axis(self) -> Point:
        if not self.dut_size:
            return (0.0, 0.0)
        return (self.board_footprint[1] / 2.0 + self.ring,
                self.lid_z + self.lid_thickness + self.hinge_diameter / 2.0)

    @property
    def hinge_notch(self) -> Point:
        return (self.hinge_ear + 0.8, self.ring)

    def knuckle_span(self) -> Optional[Point]:
        if not self.clamp or not self.hinge_ears():
            return None
        inner = min(abs(x) - self.hinge_ear / 2.0 - 0.4
                    for x in self.hinge_ears())
        edge = self.board_footprint[0] / 2.0 + self.border
        half = min(inner, edge)
        return (-half, half)

    # the lid

    @property
    def lid_thickness(self) -> float:
        return self.insert_depth + 2.0

    @property
    def lid_z(self) -> float:
        return self.dut_height + self.pcb_thickness + self.clamp_tower_height

    @property
    def lid_rib(self) -> float:
        if not self.dut_size:
            return 10.0
        half_w = self.board_footprint[0] / 2.0 + self.border
        half_d = self.board_footprint[1] / 2.0 + self.ring
        # A hole is in the frame when it is within a rib of either pair of
        # edges, so the rib has to reach the hole furthest from both.
        reach = max([min(half_w - abs(x), half_d - abs(y))
                     for x, y in self.presser_holes()] or [8.0])
        return reach + self.screw.tap_mm / 2.0 + 2.0

    @property
    def cap_diameter(self) -> float:
        return self.head_diameter

    @property
    def clamp_inset(self) -> float:
        return self.screw.nominal_mm

    def presser_holes(self) -> List[Point]:
        # Threaded holes all round the lid, evenly spaced along the board's
        # outline moved clamp_inset inwards, so a presser screwed into any
        # of them comes down on the board.
        if not self.dut_size:
            return []
        if self._holes is None:
            loop = self.outline_loop
            if not loop:
                w, d = self.dut_size[0] / 2.0, self.dut_size[1] / 2.0
                loop = [(-w, -d), (w, -d), (w, d), (-w, d), (-w, -d)]
            self._holes = _spaced(_inset(loop, self.clamp_inset),
                                  self.presser_pitch)
        return self._holes

    def pressers(self) -> List[Point]:
        # Where the four caps are drawn: the hole nearest each corner.
        holes = self.presser_holes()
        if not holes:
            return []
        return [max(holes, key=lambda p: sx * p[0] + sy * p[1])
                for sx in (-1.0, 1.0) for sy in (-1.0, 1.0)]

    # the key

    @property
    def key_face(self) -> float:
        if not self.dut_size:
            return 0.0
        return -(self.board_footprint[1] / 2.0 + self.ring)

    @property
    def key_height(self) -> float:
        return self.lid_z + self.lid_thickness / 2.0

    @property
    def key_pivot(self) -> float:
        return (self.base_thickness + self.wall_top) / 2.0

    @property
    def key_width(self) -> float:
        return 4.0 * self.screw.nominal_mm + 2.0

    @property
    def stack_centre(self) -> float:
        bottom = -self.pcb_thickness
        if self.feet:
            bottom -= self.foot_height
        top = self.dut_height + self.pcb_thickness
        if self.clamp:
            top = self.hinge_axis[1] + self.hinge_diameter / 2.0
        return (bottom + top) / 2.0

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
        if self.clamp:
            if self.cap_height <= self.cap_taper + 2.0:
                out.append("a %.1f mm cap is all point and no thread"
                           % self.cap_height)
            if self.clamp_tower_height < 2.0:
                out.append("%.1f mm under the lid leaves nowhere for the "
                           "board's own parts" % self.clamp_tower_height)
            if self.ring < 4.0:
                out.append("only %.1f mm of fixture board outside the board "
                           "under test: the hinge posts have nothing to "
                           "stand on" % self.ring)
            if self.clamp_inset * 2.0 >= min(self.dut_size):
                out.append("the pressers meet in the middle of a %.1f mm "
                           "board" % min(self.dut_size))
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


def _distance(p: Point, a: Point, b: Point) -> float:
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, (
        (p[0] - ax) * dx + (p[1] - ay) * dy) / length))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def _inset(loop: Sequence[Point], inset: float,
           step: float = 0.5) -> List[Point]:
    # The closed curve *inset* inside *loop*: points pushed in along the
    # normal, kept only where no other edge is nearer than that.
    inward = 1.0 if loop_area(loop) > 0 else -1.0
    edges = list(zip(loop, loop[1:]))
    path = []
    for (ax, ay), (bx, by) in edges:
        length = math.hypot(bx - ax, by - ay)
        if length == 0:
            continue
        nx, ny = -(by - ay) / length * inward, (bx - ax) / length * inward
        for i in range(max(1, int(length / step))):
            t = i / max(1, int(length / step))
            point = (ax + (bx - ax) * t + nx * inset,
                     ay + (by - ay) * t + ny * inset)
            if all(_distance(point, a, b) >= inset - 0.01 for a, b in edges):
                path.append(point)
    return path


def _spaced(path: Sequence[Point], pitch: float) -> List[Point]:
    # An even number of points at equal spacing round a closed path, placed
    # either side of the middle of the front so a symmetric board gets a
    # symmetric lid.
    if len(path) < 2:
        return list(path)
    start = min(range(len(path)),
                key=lambda i: (round(path[i][1], 1), abs(path[i][0])))
    ring = list(path[start:]) + list(path[:start])
    ring.append(ring[0])
    lengths = [0.0]
    for a, b in zip(ring, ring[1:]):
        lengths.append(lengths[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    count = max(4, 2 * round(lengths[-1] / (2.0 * pitch)))
    spacing = lengths[-1] / count

    out, segment = [], 0
    for k in range(count):
        target = (k + 0.5) * spacing
        while lengths[segment + 1] < target:
            segment += 1
        a, b = ring[segment], ring[segment + 1]
        span = lengths[segment + 1] - lengths[segment]
        t = 0.0 if span == 0 else (target - lengths[segment]) / span
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def _source_outline(folder: str):
    try:
        board = project.for_fixture(folder).board_path
    except project.ProjectError:
        return None, [], []
    with open(board, encoding="utf-8") as handle:
        text = handle.read()
    bbox = board_bbox_from_file(text)
    if bbox is None:
        return None, [], []
    min_x, min_y, max_x, max_y = bbox
    cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0

    def centred(points):
        return [(x - cx, -(y - cy)) for x, y in points]

    closed = [loop for loop in outline_loops(text)
              if len(loop) > 2
              and abs(loop[0][0] - loop[-1][0]) < 0.01
              and abs(loop[0][1] - loop[-1][1]) < 0.01]
    loop = max(closed, key=lambda one: abs(loop_area(one))) if closed else []
    return ((max_x - min_x, max_y - min_y), centred(outline_points(text)),
            centred(loop))


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
    dut_size, outline, loop = _source_outline(
        os.path.dirname(os.path.abspath(board_path)))

    return BodySpec(
        side=max(max_x - min_x, max_y - min_y),
        fixture_size=(max_x - min_x, max_y - min_y),
        corner_radius=CORNER_RADIUS_MM,
        pins=[(p.x_mm - cx, -(p.y_mm - cy)) for p in probes],
        screws=[(p.x_mm - cx, -(p.y_mm - cy)) for p in mounts],
        bore=round(probe.guide_bore_mm(allowance), 3),
        probe_length=probe.length_mm,
        probe_stroke=probe.stroke_mm,
        screw=screws.from_config(config),
        dut_size=dut_size,
        outline=outline,
        outline_loop=loop,
        board_clearance=float(config.get("holder.board_clearance")),
        pcb_thickness=float(config.get("pcb.thickness")),
        border=float(config.get("holder.body_border")),
        feet=bool(config.get("holder.feet")),
        foot_height=float(config.get("holder.foot_height")),
        base_thickness=float(config.get("holder.base_thickness")),
        threaded_inserts=bool(config.get("holder.threaded_inserts")),
        clamp=bool(config.get("holder.clamp")),
        clamp_tower_height=float(config.get("holder.clamp_tower_height")),
        cap_height=float(config.get("holder.presser_cap_height")),
    )

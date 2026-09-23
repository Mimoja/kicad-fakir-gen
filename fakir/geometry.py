from __future__ import annotations

import itertools
import math
from typing import List, Sequence, Tuple

from .model import FixtureConfig, TestPoint
from .sexpr import Node, Sym, num

EDGE_CLEARANCE_MM = 0.30      # copper to board edge

_SQRT_HALF = math.sqrt(0.5)


class Outline:
    __slots__ = ("x0", "y0", "side", "radius")

    def __init__(self, x0: float, y0: float, side: float, radius: float):
        self.x0 = x0
        self.y0 = y0
        self.side = side
        self.radius = radius

    @property
    def x1(self) -> float:
        return self.x0 + self.side

    @property
    def y1(self) -> float:
        return self.y0 + self.side

    @property
    def centre(self) -> Tuple[float, float]:
        return (self.x0 + self.side / 2.0, self.y0 + self.side / 2.0)

    def __repr__(self) -> str:
        return "Outline(%.3f, %.3f, side=%.3f, r=%.3f)" % (
            self.x0, self.y0, self.side, self.radius)


def distance_to_edge(x: float, y: float, outline: Outline) -> float:
    centre_x, centre_y = outline.centre
    half = outline.side / 2.0
    radius = max(0.0, min(outline.radius, half))
    dx = abs(x - centre_x) - (half - radius)
    dy = abs(y - centre_y) - (half - radius)
    if dx <= 0.0 and dy <= 0.0:
        outside = max(dx, dy)
    else:
        outside = math.hypot(max(dx, 0.0), max(dy, 0.0))
    return radius - outside


def bounds(points: Sequence[TestPoint]) -> Tuple[float, float, float, float]:
    if not points:
        raise ValueError("no test points to bound")
    xs = [p.x_mm for p in points]
    ys = [p.y_mm for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def make_outline(points: Sequence[TestPoint], cfg: FixtureConfig) -> Outline:
    min_x, min_y, max_x, max_y = cfg.source_bbox or bounds(points)
    side = max(max_x - min_x, max_y - min_y) + 2.0 * cfg.margin_mm
    centre_x = (min_x + max_x) / 2.0
    centre_y = (min_y + max_y) / 2.0
    radius = min(cfg.corner_radius_mm, side / 2.0)
    return Outline(centre_x - side / 2.0, centre_y - side / 2.0, side, radius)


def rounded_rect_edges(x0: float, y0: float, x1: float, y1: float,
                       radius: float, layer: str, width: float,
                       uid) -> List[Node]:
    radius = max(0.0, min(radius, (x1 - x0) / 2.0, (y1 - y0) / 2.0))

    def stroke() -> Node:
        return ["stroke", ["width", num(width)], ["type", Sym("solid")]]

    nodes: List[Node] = []
    if radius <= 0:
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        segments = [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    else:
        segments = [
            ((x0 + radius, y0), (x1 - radius, y0)),
            ((x1, y0 + radius), (x1, y1 - radius)),
            ((x1 - radius, y1), (x0 + radius, y1)),
            ((x0, y1 - radius), (x0, y0 + radius)),
        ]
    for index, ((sx, sy), (ex, ey)) in enumerate(segments):
        nodes.append(["gr_line",
                      ["start", num(sx), num(sy)], ["end", num(ex), num(ey)],
                      stroke(), ["layer", layer],
                      ["uuid", uid("line-%d" % index)]])
    if radius <= 0:
        return nodes

    # start, end, arc centre, direction of the arc's midpoint
    corners = [
        ((x1 - radius, y0), (x1, y0 + radius),
         (x1 - radius, y0 + radius), (+1, -1)),
        ((x1, y1 - radius), (x1 - radius, y1),
         (x1 - radius, y1 - radius), (+1, +1)),
        ((x0 + radius, y1), (x0, y1 - radius),
         (x0 + radius, y1 - radius), (-1, +1)),
        ((x0, y0 + radius), (x0 + radius, y0),
         (x0 + radius, y0 + radius), (-1, -1)),
    ]
    for index, ((sx, sy), (ex, ey), (cx, cy), (ux, uy)) in enumerate(corners):
        nodes.append(["gr_arc",
                      ["start", num(sx), num(sy)],
                      ["mid", num(cx + ux * radius * _SQRT_HALF),
                       num(cy + uy * radius * _SQRT_HALF)],
                      ["end", num(ex), num(ey)],
                      stroke(), ["layer", layer],
                      ["uuid", uid("arc-%d" % index)]])
    return nodes


def clearance_warnings(
    placed: Sequence[Tuple[TestPoint, float, float]],
    cfg: FixtureConfig,
    outline: Outline,
    mounts: Sequence[Tuple[str, float, float]] = (),
) -> List[str]:
    warnings: List[str] = []
    copper = cfg.pad

    for (a, ax, ay), (b, bx, by) in itertools.combinations(placed, 2):
        distance = math.hypot(ax - bx, ay - by)
        if distance < 1e-6:
            warnings.append("%s and %s land on the same point (%.3f, %.3f)"
                            % (a.ref, b.ref, ax, ay))
        elif distance < copper:
            warnings.append("%s and %s are %.3f mm apart but the pads are "
                            "%.2f mm wide; they overlap"
                            % (a.ref, b.ref, distance, copper))
        elif distance < copper + 0.2:
            warnings.append("%s and %s are %.3f mm apart, leaving %.3f mm of "
                            "copper clearance"
                            % (a.ref, b.ref, distance, distance - copper))

    needed_at_edge = copper / 2.0 + EDGE_CLEARANCE_MM
    shortfall = 0.0
    for point, x, y in placed:
        gap = distance_to_edge(x, y, outline)
        if gap < needed_at_edge:
            shortfall = max(shortfall, needed_at_edge - gap)
            warnings.append("%s is %.2f mm from the board edge, but a %.2f mm "
                            "pad needs %.2f mm"
                            % (point.ref, gap, copper, needed_at_edge))
    if shortfall > 0.0:
        warnings.append("raise the PCB margin to about %.1f mm to clear the "
                        "edge with a %s probe"
                        % (cfg.margin_mm + shortfall, cfg.pogo_key))

    screw_gap = (copper + cfg.mount_drill_mm) / 2.0 + EDGE_CLEARANCE_MM
    for ref, screw_x, screw_y in mounts:
        for point, x, y in placed:
            distance = math.hypot(x - screw_x, y - screw_y)
            if distance < screw_gap:
                warnings.append("%s is %.2f mm from mounting hole %s, which "
                                "needs %.2f mm for a %.2f mm pad"
                                % (point.ref, distance, ref, screw_gap,
                                   copper))

    # A screw on the printed outline of the board under test is hard to
    # assemble around.
    if cfg.source_bbox and mounts:
        min_x, min_y, max_x, max_y = cfg.source_bbox
        screw = cfg.mount_drill_mm / 2.0
        for ref, sx, sy in mounts:
            clear = max(min_x - sx, sx - max_x, min_y - sy, sy - max_y)
            if clear < screw + 0.5:
                warnings.append("mounting hole %s is %.2f mm from the outline "
                                "of the board under test; raise the PCB margin"
                                % (ref, max(0.0, clear - screw)))

    if cfg.pad - cfg.drill < 0.3:
        warnings.append("annular ring is %.3f mm (pad %.2f mm, drill %.2f "
                        "mm); "
                        "most fabs want at least 0.15 mm per side"
                        % ((cfg.pad - cfg.drill) / 2.0, cfg.pad, cfg.drill))
    return warnings

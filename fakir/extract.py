from __future__ import annotations

import math
import os
import re
from typing import List, Optional, Pattern, Sequence, Tuple

from .model import TestPoint
from .sexpr import Node, find, find_all, loads

DEFAULT_REF_PATTERN = r"^TP\d+$"

_SQRT_HALF = math.sqrt(0.5)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]


class ExtractionError(RuntimeError):
    pass


def _compile(ref_pattern: str,
             lib_pattern: Optional[str]) -> Tuple[Pattern, Optional[Pattern]]:
    return (re.compile(ref_pattern, re.IGNORECASE),
            re.compile(lib_pattern, re.IGNORECASE) if lib_pattern else None)


def _matches(ref: str, lib_id: str, ref_re: Pattern,
             lib_re: Optional[Pattern]) -> bool:
    return bool(ref_re.search(ref) or (lib_re and lib_re.search(lib_id)))


def _prop(footprint: Node, name: str) -> Optional[str]:
    for prop in find_all(footprint, "property"):
        if len(prop) >= 3 and str(prop[1]) == name:
            return str(prop[2])
    return None


def _first_net(footprint: Node) -> Optional[str]:
    for pad in find_all(footprint, "pad"):
        net = find(pad, "net")
        if not net or len(net) < 2:
            continue
        # KiCad 9 writes (net <code> "<name>"), KiCad 10 (net "<name>").
        name = str(net[-1])
        if name and not name.isdigit():
            return name
    return None


def from_file(path: str, ref_pattern: str = DEFAULT_REF_PATTERN,
              lib_pattern: Optional[str] = None
              ) -> Tuple[List[TestPoint], Optional[BBox], str]:
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    root = loads(text)
    ref_re, lib_re = _compile(ref_pattern, lib_pattern)

    points: List[TestPoint] = []
    for fp in find_all(root, "footprint"):
        named = len(fp) > 1 and not isinstance(fp[1], list)
        lib_id = str(fp[1]) if named else ""
        ref = _prop(fp, "Reference") or ""
        if not _matches(ref, lib_id, ref_re, lib_re):
            continue
        at, layer = find(fp, "at"), find(fp, "layer")
        uuid_node = find(fp, "uuid")
        if not at or not layer:
            continue
        points.append(TestPoint(
            ref=ref,
            value=_prop(fp, "Value") or "",
            x_mm=float(at[1]),
            y_mm=float(at[2]),
            rotation_deg=float(at[3]) if len(at) > 3 else 0.0,
            side=str(layer[1]),
            net=_first_net(fp),
            source_footprint=lib_id,
            source_uuid=str(uuid_node[1]) if uuid_node else None,
        ))

    name = os.path.splitext(os.path.basename(path))[0]
    return points, board_bbox_from_file(text), name


# Board outline.  Segments are ("line", x1, y1, x2, y2),
# ("arc", sx, sy, mx, my, ex, ey) and ("circle", cx, cy, radius).

def _rect_segments(x1, y1, x2, y2, radius=0.0) -> list:
    left, right = min(x1, x2), max(x1, x2)
    top, bottom = min(y1, y2), max(y1, y2)
    radius = max(0.0, min(radius, (right - left) / 2.0, (bottom - top) / 2.0))
    if radius <= 0.0:
        corners = [(left, top), (right, top), (right, bottom), (left, bottom)]
        return [("line",) + corners[i] + corners[(i + 1) % 4]
                for i in range(4)]

    out = [
        ("line", left + radius, top, right - radius, top),
        ("line", right, top + radius, right, bottom - radius),
        ("line", right - radius, bottom, left + radius, bottom),
        ("line", left, bottom - radius, left, top + radius),
    ]
    corners = [
        ((right - radius, top), (right, top + radius),
         (right - radius, top + radius), (+1, -1)),
        ((right, bottom - radius), (right - radius, bottom),
         (right - radius, bottom - radius), (+1, +1)),
        ((left + radius, bottom), (left, bottom - radius),
         (left + radius, bottom - radius), (-1, +1)),
        ((left, top + radius), (left + radius, top),
         (left + radius, top + radius), (-1, -1)),
    ]
    for (sx, sy), (ex, ey), (cx, cy), (ux, uy) in corners:
        out.append(("arc", sx, sy, cx + ux * radius * _SQRT_HALF,
                    cy + uy * radius * _SQRT_HALF, ex, ey))
    return out


def _shape_segments(shape: Node, kind: str) -> list:
    def xy(node):
        return (float(node[1]), float(node[2]))

    if kind == "line":
        return [("line",) + xy(find(shape, "start")) + xy(find(shape, "end"))]
    if kind == "arc":
        return [("arc",) + xy(find(shape, "start")) + xy(find(shape, "mid"))
                + xy(find(shape, "end"))]
    if kind == "circle":
        cx, cy = xy(find(shape, "center"))
        ex, ey = xy(find(shape, "end"))
        return [("circle", cx, cy, math.hypot(ex - cx, ey - cy))]
    if kind == "rect":
        radius = find(shape, "radius")
        return _rect_segments(*xy(find(shape, "start")),
                              *xy(find(shape, "end")),
                              float(radius[1]) if radius else 0.0)
    if kind == "poly":
        pts = find(shape, "pts")
        corners = [xy(node) for node in find_all(pts, "xy")] if pts else []
        return [("line",) + corners[i] + corners[(i + 1) % len(corners)]
                for i in range(len(corners))]
    return []


def outline_segments(text: str) -> list:
    root = loads(text)

    def on_edge(shape) -> bool:
        layer = find(shape, "layer")
        return layer is not None and str(layer[1]) == "Edge.Cuts"

    out = []
    for kind in ("line", "arc", "circle", "rect", "poly"):
        for shape in find_all(root, "gr_" + kind):
            if on_edge(shape):
                out += _shape_segments(shape, kind)
    for footprint in find_all(root, "footprint"):
        for shape in footprint:
            if (isinstance(shape, list)
                    and str(shape[0]).startswith("fp_") and on_edge(shape)):
                out += _shape_segments(shape, str(shape[0])[3:])
    return out


def _arc_points(arc, samples: int) -> List[Point]:
    sx, sy, mx, my, ex, ey = arc
    ax, ay = mx - sx, my - sy
    bx, by = ex - sx, ey - sy
    area = 2.0 * (ax * by - ay * bx)
    if abs(area) < 1e-9:
        return [(sx, sy), (mx, my), (ex, ey)]
    asq, bsq = ax * ax + ay * ay, bx * bx + by * by
    cx = sx + (by * asq - ay * bsq) / area
    cy = sy + (ax * bsq - bx * asq) / area
    radius = math.hypot(sx - cx, sy - cy)

    start = math.atan2(sy - cy, sx - cx)
    mid = math.atan2(my - cy, mx - cx)
    end = math.atan2(ey - cy, ex - cx)

    def span(a, b):
        delta = (b - a) % (2.0 * math.pi)
        return delta - 2.0 * math.pi if delta > math.pi else delta

    first, second = span(start, mid), span(mid, end)
    out = []
    for index in range(samples + 1):
        t = index / float(samples)
        if t <= 0.5:
            angle = start + first * 2.0 * t
        else:
            angle = mid + second * (2.0 * t - 1.0)
        out.append((cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle)))
    return out


def _segment_points(segment, samples: int) -> List[Point]:
    kind = segment[0]
    if kind == "line":
        return [(segment[1], segment[2]), (segment[3], segment[4])]
    if kind == "arc":
        return _arc_points(segment[1:], samples)
    cx, cy, radius = segment[1:]
    ring = [(cx + radius * math.cos(2.0 * math.pi * i / samples),
             cy + radius * math.sin(2.0 * math.pi * i / samples))
            for i in range(samples)]
    return ring + [ring[0]]


def outline_points(text: str, samples: int = 24) -> List[Point]:
    return [point for segment in outline_segments(text)
            for point in _segment_points(segment, samples)]


def outline_loops(text: str, samples: int = 24,
                  tolerance: float = 0.01) -> List[List[Point]]:
    chains = [_segment_points(segment, samples)
              for segment in outline_segments(text)]

    def near(a, b):
        return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance

    loops = []
    while chains:
        loop = chains.pop(0)
        joined = True
        while joined and not near(loop[0], loop[-1]):
            joined = False
            for index, chain in enumerate(chains):
                if near(loop[-1], chain[0]):
                    loop += chains.pop(index)[1:]
                elif near(loop[-1], chain[-1]):
                    loop += list(reversed(chains.pop(index)))[1:]
                elif near(loop[0], chain[-1]):
                    loop = chains.pop(index)[:-1] + loop
                elif near(loop[0], chain[0]):
                    loop = list(reversed(chains.pop(index)))[:-1] + loop
                else:
                    continue
                joined = True
                break
        loops.append(loop)
    return loops


def loop_area(loop: Sequence[Point]) -> float:
    total = 0.0
    for index in range(len(loop)):
        x1, y1 = loop[index]
        x2, y2 = loop[(index + 1) % len(loop)]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def board_bbox_from_file(text: str) -> Optional[BBox]:
    points = outline_points(text)
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))

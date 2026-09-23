from __future__ import annotations

import os

import cadquery as cq

from .spec import BodySpec, HolderError

# Chord error of the mesh formats, in mm.  CadQuery's default of 0.1 turns
# a 1 mm probe bore into a hexagon.
_MESH_TOLERANCE = 0.01


def _rounded_rect(width, depth, radius):
    # OpenCASCADE cannot fillet a side away entirely.
    radius = min(radius, min(width, depth) / 2.0 - 0.01)
    sketch = cq.Sketch().rect(width, depth)
    return sketch.vertices().fillet(radius) if radius > 0 else sketch


def _hull(circles, segments=()):
    sketch = cq.Sketch()
    for u, v, d in circles:
        sketch = sketch.arc((u, v), d / 2.0, 0.0, 360.0)
    for start, end in segments:
        sketch = sketch.segment(start, end)
    return sketch.hull()


def _plane(z):
    return cq.Workplane("XY", origin=(0, 0, z))


def _screw_hole(workplane, spec):
    if spec.threaded_inserts:
        return workplane.cboreHole(spec.screw_hole, spec.insert_drill,
                                   spec.insert_depth)
    return workplane.hole(spec.screw.tap_mm)


def _screw_bore(spec):
    return spec.insert_drill if spec.threaded_inserts else spec.screw.tap_mm


def build_solid(spec: BodySpec):
    width, depth = spec.body_size
    radius = max(0.0, min(spec.corner_radius, width / 2.0, depth / 2.0))
    plate = _rounded_rect(width, depth, radius)
    holder = cq.Workplane("XY").placeSketch(plate).extrude(spec.base_thickness)

    # Each boss is tied to the nearest corner of the plate by a flat slab
    # with rounded ends.
    half_w, half_d = width / 2.0 - radius, depth / 2.0 - radius
    for x, y in spec.screws:
        anchor = (max(-half_w, min(half_w, x)), max(-half_d, min(half_d, y)),
                  max(radius * 2.0, 1.0))
        holder = holder.union(
            cq.Workplane("XY").placeSketch(_hull([(x, y, spec.boss), anchor]))
            .extrude(spec.boss_height))

    # A sketch fuses pillars that overlap, which close test points make.
    pillars = cq.Sketch().push(spec.pins).circle(spec.pillar_diameter / 2.0)
    holder = holder.union(
        cq.Workplane("XY").placeSketch(pillars).extrude(spec.guide_height))

    # Probe bores, then the stack screws' holes down through each boss.
    holder = (holder.copyWorkplane(_plane(spec.guide_height))
              .pushPoints(spec.pins).hole(spec.bore))
    return _screw_hole(holder.copyWorkplane(_plane(spec.boss_height))
                       .pushPoints(spec.screws), spec)


def _copies(part, points):
    return (cq.Workplane("XY").pushPoints(points)
            .eachpoint(lambda loc: part.val().located(loc)).combine())


def build_feet(spec: BodySpec):
    if not spec.screws:
        raise HolderError("no screw positions, so nothing to stand on")
    foot = (cq.Workplane("XY").circle(spec.foot_diameter / 2.0)
            .extrude(spec.foot_height)
            .faces("<Z").workplane()
            .cboreHole(spec.screw_hole, spec.head_diameter, spec.head_depth))
    return _copies(foot, spec.screws)


def printable(spec: BodySpec):
    parts = {"holder": build_solid(spec)}
    if spec.feet and spec.screws:
        parts["feet"] = build_feet(spec)
    return parts


def probe_solid(probe):
    plunger_length = min(4.0, probe.stroke_mm + 1.0)
    barrel_length = max(1.0, probe.length_mm - plunger_length)
    plunger_d = max(0.2, probe.barrel_mm * 0.62)
    head_d = max(plunger_d, probe.tip_mm)
    return (cq.Workplane("XY").circle(probe.barrel_mm / 2.0)
            .extrude(barrel_length)
            .faces(">Z").workplane().circle(plunger_d / 2.0)
            .extrude(plunger_length)
            .faces(">Z").workplane().sphere(head_d / 2.0))


def export(part, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    cq.exporters.export(part, path, tolerance=_MESH_TOLERANCE)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise HolderError("CadQuery wrote nothing to %s" % path)
    return path

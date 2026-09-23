from __future__ import annotations

import os

import cadquery as cq

from .spec import BodySpec, HolderError

# Colours for KiCad's 3D view: printed plastic, and the feet a shade apart.
_PLASTIC = cq.Color(0.89, 0.82, 0.70)
_LID = cq.Color(0.80, 0.80, 0.82)
_FEET = cq.Color(0.45, 0.47, 0.50)

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


# The "XZ" plane's normal points to -y, so _rod_y extrudes negative.
def _rod_x(x, y, z, diameter, length):
    return (cq.Workplane("YZ", origin=(x, 0, 0)).center(y, z)
            .circle(diameter / 2.0).extrude(length))


def _rod_y(x, y, z, diameter, length):
    return (cq.Workplane("XZ", origin=(0, y, 0)).center(x, z)
            .circle(diameter / 2.0).extrude(-length))


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

    if spec.outline_loop and spec.wall_top > spec.base_thickness:
        holder = holder.union(_wall(spec, plate))
    if spec.clamp:
        holder = _add_clamp(spec, holder)

    # Probe bores, then the stack screws' holes down through each boss.
    holder = (holder.copyWorkplane(_plane(spec.guide_height))
              .pushPoints(spec.pins).hole(spec.bore))
    return _screw_hole(holder.copyWorkplane(_plane(spec.boss_height))
                       .pushPoints(spec.screws), spec)


def _wall(spec: BodySpec, plate):
    loop = spec.outline_loop
    if loop[0] == loop[-1]:
        loop = loop[:-1]
    height = spec.wall_top - spec.base_thickness

    def prism(grow):
        return (_plane(spec.base_thickness).polyline(loop).close()
                .offset2D(grow, "arc").extrude(height))

    # Clipped to the plate's outline, so an odd board cannot push it off.
    return (prism(spec.border).cut(prism(spec.board_clearance / 2.0))
            .intersect(cq.Workplane("XY").placeSketch(plate)
                       .extrude(spec.wall_top)))


def _add_clamp(spec: BodySpec, holder):
    post_x, post_y = spec.post_size
    axis_y, axis_z = spec.hinge_axis
    ear = spec.hinge_ear

    holder = holder.union(
        cq.Workplane("XY").pushPoints(spec.hinge_posts())
        .slot2D(post_x, post_y).extrude(spec.lid_z))
    for x, y in spec.hinge_posts():
        # The ear is the hull from the post's top face up to the barrel, so
        # the neck tapers into it.
        profile = _hull([(axis_y, axis_z, spec.hinge_diameter)],
                        [((y - post_y / 2.0, spec.lid_z),
                          (y + post_y / 2.0, spec.lid_z))])
        holder = (holder
                  .union(cq.Workplane("YZ", origin=(x - ear / 2.0, 0, 0))
                         .placeSketch(profile).extrude(ear))
                  .cut(_rod_x(x - ear / 2.0 - 1.0, axis_y, axis_z,
                              spec.screw.tap_mm, ear + 2.0)))

    return (holder
            .union(_rod_y(0.0, spec.key_face, spec.key_pivot,
                          spec.key_width * 0.6, spec.ring))
            .cut(_rod_y(0.0, spec.key_face - 1.0, spec.key_pivot,
                        spec.screw.tap_mm, spec.ring + 2.0)))


def build_lid(spec: BodySpec):
    if not spec.dut_size:
        raise HolderError("no board size, so there is nothing to clamp")

    width = spec.board_footprint[0] + 2.0 * spec.border
    depth = spec.board_footprint[1] + 2.0 * spec.ring
    thick = spec.lid_thickness
    axis_y = spec.hinge_axis[0]
    axis_z = thick + spec.hinge_diameter / 2.0                   # lid-local

    lid = (cq.Workplane("XY")
           .placeSketch(_rounded_rect(width, depth, spec.corner_radius))
           .extrude(thick))
    rib = spec.lid_rib
    if width > 2.0 * rib + 6.0 and depth > 2.0 * rib + 6.0:
        window = _rounded_rect(width - 2.0 * rib, depth - 2.0 * rib,
                               spec.corner_radius)
        lid = lid.faces(">Z").workplane().placeSketch(window).cutThruAll()

    # Tap-sized through holes: the presser screws cut their own thread, so
    # each one stays at whatever height it is wound to.
    lid = (lid.faces(">Z").workplane().pushPoints(spec.presser_holes())
           .hole(spec.screw.tap_mm))

    # Access holes over the stack screws the lid covers.
    margin = spec.insert_drill / 2.0 + 1.5
    covered = [(x, y) for x, y in spec.screws
               if abs(x) <= width / 2.0 - margin
               and abs(y) <= depth / 2.0 - margin]
    if covered:
        lid = (lid.faces(">Z").workplane().pushPoints(covered)
               .hole(spec.insert_drill + 1.5))

    # Notches for the ears, no deeper than the ring they stand in.
    notch_w, notch_d = spec.hinge_notch
    ears = [(x, axis_y - notch_d / 2.0 + 0.5) for x in spec.hinge_ears()]
    if ears:
        lid = (lid.faces(">Z").workplane().pushPoints(ears)
               .rect(notch_w, notch_d + 1.0).cutThruAll())

    # One barrel between the ears, on a web up from the back edge.
    span = spec.knuckle_span()
    if span:
        left, right = span
        lid = (lid
               .union(_rod_x(left, axis_y, axis_z, spec.hinge_diameter,
                             right - left))
               .union(cq.Workplane("XY")
                      .center((left + right) / 2.0, axis_y - spec.ring / 4.0)
                      .rect(right - left, spec.ring / 2.0).extrude(axis_z))
               .cut(_rod_x(left - 1.0, axis_y, axis_z, spec.screw_hole,
                           right - left + 2.0)))

    # The key's screw goes into the front face.
    return lid.cut(_rod_y(0.0, -depth / 2.0 - 1.0, thick / 2.0,
                          _screw_bore(spec), spec.insert_depth + 1.0))


def build_cap(spec: BodySpec):
    shank = spec.cap_height - spec.cap_taper
    return (cq.Workplane("XY").circle(spec.cap_tip / 2.0)
            .workplane(offset=spec.cap_taper).circle(spec.cap_diameter / 2.0)
            .loft()
            .faces(">Z").workplane().circle(spec.cap_diameter / 2.0)
            .extrude(shank)
            .faces(">Z").workplane().hole(spec.screw.tap_mm, shank - 0.5))


def _copies(part, points):
    return (cq.Workplane("XY").pushPoints(points)
            .eachpoint(lambda loc: part.val().located(loc)).combine())


def build_caps(spec: BodySpec):
    pitch = spec.cap_diameter + 3.0
    count = max(1, len(spec.pressers()))
    return _copies(build_cap(spec), [(i * pitch, 0) for i in range(count)])


def build_key(spec: BodySpec):
    if not spec.dut_size:
        raise HolderError("no board size, so there is nothing to lock")

    width, thickness = spec.key_width, spec.key_thickness
    pivot, top = spec.key_pivot, spec.key_height
    slot = spec.screw_hole + 0.4
    face = cq.Workplane("XZ", origin=(0, spec.key_face - spec.key_gap, 0))

    bar = (face.center(0.0, (pivot + top) / 2.0)
           .slot2D(top - pivot + width, width, 90)
           .center(0.0, (pivot - top) / 2.0).circle(spec.screw_hole / 2.0)
           .extrude(thickness))
    notch = (face.center((width - slot / 2.0) / 2.0, top)
             .slot2D(width + slot / 2.0, slot).extrude(thickness))
    return bar.cut(notch)


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
    if spec.clamp:
        parts.update(lid=build_lid(spec), caps=build_caps(spec),
                     key=build_key(spec))
    if spec.feet and spec.screws:
        parts["feet"] = build_feet(spec)
    return parts


# The caps tip up and the key lies on its side: nothing needs supports.
def prepare_for_printing(parts, gap=10.0):
    def solids(name, turn=None):
        for solid in parts[name].solids().vals():
            yield solid.rotate((0, 0, 0), (1, 0, 0), turn) if turn else solid

    laid = [("holder", None), ("lid", None), ("key", 90), ("caps", 180),
            ("feet", None)]
    # Shelf packing: left to right, a new row once a row is 200 mm wide.
    placed, x, y, row_depth = [], 0.0, 0.0, 0.0
    for part, turn in laid:
        if part not in parts:
            continue
        for solid in solids(part, turn):
            box = solid.BoundingBox()
            if x and x + box.xlen > 200.0:
                x, y, row_depth = 0.0, y + row_depth + gap, 0.0
            placed.append(solid.translate(
                cq.Vector(x - box.xmin, y - box.ymin, -box.zmin)))
            x += box.xlen + gap
            row_depth = max(row_depth, box.ylen)
    return cq.Compound.makeCompound(placed)


# z = 0 is the top face of the fixture PCB; the caps sit on the board.
def assembly(spec: BodySpec, parts) -> cq.Assembly:
    stack = cq.Assembly(name="fixture")
    stack.add(parts["holder"], name="holder", color=_PLASTIC)
    if "lid" in parts:
        board_top = spec.dut_height + spec.pcb_thickness
        caps = _copies(build_cap(spec), spec.pressers())
        stack.add(parts["lid"], name="lid", color=_LID,
                  loc=cq.Location((0, 0, spec.lid_z)))
        stack.add(caps, name="caps", color=_LID,
                  loc=cq.Location((0, 0, board_top)))
        stack.add(parts["key"], name="key", color=_LID)
    if "feet" in parts:
        drop = -(spec.pcb_thickness + spec.foot_height)
        stack.add(parts["feet"], name="feet", color=_FEET,
                  loc=cq.Location((0, 0, drop)))
    return stack


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
    if isinstance(part, cq.Assembly):
        part.export(path)
    else:
        cq.exporters.export(part, path, tolerance=_MESH_TOLERANCE)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        raise HolderError("CadQuery wrote nothing to %s" % path)
    return path

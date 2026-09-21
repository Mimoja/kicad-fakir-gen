import os
import uuid

import dump

# Fixed namespace: the same UUIDs every run, so the schematic symbols and
# the board footprints stay linked across regenerations.
NS = uuid.UUID("6f2b1c40-9a1e-5d3a-8c77-2f1d5a6b3e90")
NAME = "fakir"

RADIUS = 3.0

HEAD = """(kicad_pcb
\t(version 20260206)
\t(generator "fakir")
\t(generator_version "10.0")
\t(general (thickness {thickness}) (legacy_teardrops no))
\t(paper "A4")
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(25 "Edge.Cuts" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user)
\t\t(33 "B.Fab" user)
\t)
\t(setup (pad_to_mask_clearance 0))
\t(net 0 "")
"""

NOTE = """\t(gr_text "{text}" (at {x} {y} 0) (layer "{layer}") (uuid "{uid}")
\t\t(effects (font (size 1.2 1.2) (thickness 0.18)){mirror}))
"""

ARC = """\t(gr_arc (start {} {}) (mid {} {}) (end {} {})
\t\t(stroke (width {}) (type solid)) (layer "{}") (uuid "{}"))
"""

LINE = """\t(gr_line (start {} {}) (end {} {})
\t\t(stroke (width {}) (type solid)) (layer "{}") (uuid "{}"))
"""

# 1.20 is the nearest KiCad stock size
DRILL = 1.2
PAD = 1.9
HOLE = """\t(footprint "fakir:PogoPin_D{drill}mm"
\t\t(layer "B.Cu") (uuid "{uid}") (at {x} {y})
\t\t(descr "pogo pin, barrel soldered in, {drill} mm drill")
\t\t(property "Reference" "{ref}" (at 0 0 0) (layer "B.Fab") (hide yes)
\t\t\t(uuid "{uid1}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t\t(justify mirror)))
\t\t(property "Value" "{value}" (at 0 -1.95 0) (layer "B.SilkS")
\t\t\t(uuid "{uid2}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t\t(justify mirror)))
\t\t(property "Footprint" "" (at 0 0 0) (layer "B.Fab") (hide yes)
\t\t\t(uuid "{uid4}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t\t(justify mirror)))
\t\t(property "Datasheet" "" (at 0 0 0) (layer "B.Fab") (hide yes)
\t\t\t(uuid "{uid5}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t\t(justify mirror)))
\t\t(property "Description" "test point" (at 0 0 0) (layer "B.Fab")
\t\t\t(hide yes) (uuid "{uid6}")
\t\t\t(effects (font (size 0.8 0.8) (thickness 0.15)) (justify mirror)))
\t\t(path "/{symbol}") (sheetname "/") (sheetfile "fakir.kicad_sch")
\t\t(attr through_hole)
\t\t(fp_circle (center 0 0) (end {ring} 0)
\t\t\t(stroke (width 0.12) (type solid)) (fill no) (layer "B.SilkS")
\t\t\t(uuid "{uid7}"))
\t\t(pad "1" thru_hole circle (at 0 0) (size {pad} {pad}) (drill {drill})
\t\t\t(layers "*.Cu" "*.Mask") (uuid "{uid3}"))
\t)
"""


# KiCad's own MountingHole_3.2mm_M3, as far as a board needs it
MOUNT = """\t(footprint "MountingHole:MountingHole_3.2mm_M3"
\t\t(layer "F.Cu") (uuid "{uid}") (at {x} {y})
\t\t(descr "Mounting Hole 3.2mm, no annular, M3")
\t\t(tags "mounting hole 3.2mm no annular m3")
\t\t(property "Reference" "{ref}" (at 0 -4.2 0) (layer "F.SilkS") (hide yes)
\t\t\t(uuid "{uid1}") (effects (font (size 1 1) (thickness 0.15))))
\t\t(property "Value" "MountingHole_3.2mm_M3" (at 0 4.2 0) (layer "F.Fab")
\t\t\t(uuid "{uid2}") (effects (font (size 1 1) (thickness 0.15))))
\t\t(property "Footprint" "" (at 0 0 0) (layer "F.Fab") (hide yes)
\t\t\t(uuid "{uid3}") (effects (font (size 1.27 1.27) (thickness 0.15))))
\t\t(property "Datasheet" "" (at 0 0 0) (layer "F.Fab") (hide yes)
\t\t\t(uuid "{uid4}") (effects (font (size 1.27 1.27) (thickness 0.15))))
\t\t(property "Description" "Mounting Hole 3.2mm, no annular, M3"
\t\t\t(at 0 0 0) (layer "F.Fab") (hide yes) (uuid "{uid5}")
\t\t\t(effects (font (size 1.27 1.27) (thickness 0.15))))
\t\t(path "/{symbol}") (sheetname "/") (sheetfile "fakir.kicad_sch")
\t\t(attr exclude_from_pos_files exclude_from_bom)
\t\t(fp_circle (center 0 0) (end 3.2 0)
\t\t\t(stroke (width 0.15) (type solid)) (fill no) (layer "Cmts.User")
\t\t\t(uuid "{uid6}"))
\t\t(fp_circle (center 0 0) (end 3.45 0)
\t\t\t(stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd")
\t\t\t(uuid "{uid7}"))
\t\t(pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2)
\t\t\t(layers "*.Cu" "*.Mask") (uuid "{uid8}"))
\t)
"""


def mounts(cx, cy, side, margin):
    # one in each corner, halfway across the margin
    inset = side / 2 - margin / 2
    return [("H1", cx - inset, cy - inset), ("H2", cx + inset, cy - inset),
            ("H3", cx + inset, cy + inset), ("H4", cx - inset, cy + inset)]


def uid(*parts):
    return str(uuid.uuid5(NS, NAME + "|" + "|".join(parts)))


def edges(segments, layer, width):
    out = ""
    for index, (kind, points) in enumerate(segments):
        flat = [v for point in points for v in point]
        template = LINE if kind == "line" else ARC
        out += template.format(*flat, width, layer,
                               uid(layer, kind, str(index)))
    return out


if __name__ == "__main__":
    cfg = dump.config()
    b = dump.board()
    TPS = dump.test_points(b, cfg["ref_pattern"], cfg["test_point_side"])
    x1, y1, x2, y2 = dump.outline(b)
    margin = cfg["pcb"]["margin"]
    out = HEAD.format(thickness=cfg["pcb"]["thickness"])
    # a square with rounded corners, as big as the board's longer side
    side = max(x2 - x1, y2 - y1) + 2 * margin
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    out += edges(dump.rect_segments(cx - side / 2, cy - side / 2,
                                    cx + side / 2, cy + side / 2, RADIUS),
                 "Edge.Cuts", 0.1)
    # the board's real outline on both silkscreens
    out += edges(dump.segments(b), "F.SilkS", 0.12)
    out += edges(dump.segments(b), "B.SilkS", 0.12)
    # say which side is which, in the margin above the board
    ny = cy + side / 2 - margin / 2
    out += NOTE.format(text=cfg["pcb"]["note_top"], x=cx, y=ny,
                       layer="F.SilkS", uid=uid("note", "top"), mirror="")
    out += NOTE.format(text=cfg["pcb"]["note_bottom"], x=cx, y=ny,
                       layer="B.SilkS", uid=uid("note", "bottom"),
                       mirror=" (justify mirror)")
    for ref, x, y, value in TPS:
        out += HOLE.format(uid=uid("fp", ref), uid1=uid("ref", ref),
                           uid2=uid("value", ref), uid3=uid("pad", ref),
                           uid4=uid("fpname", ref), uid5=uid("ds", ref),
                           uid6=uid("descr", ref), uid7=uid("silk", ref),
                           symbol=uid("sym", ref), ref=ref, x=x, y=y,
                           value=value, drill=DRILL, pad=PAD,
                           ring=PAD / 2 + 0.25)
    for ref, x, y in mounts(cx, cy, side, margin):
        ids = {"uid%d" % i: uid("mount", ref, str(i)) for i in range(1, 9)}
        out += MOUNT.format(uid=uid("mount", ref), symbol=uid("mountsym", ref),
                            ref=ref, x=x, y=y, **ids)
    out += "\t(embedded_fonts no)\n)\n"
    open("fakir.kicad_pcb", "w").write(out)

    os.makedirs("fakir.pretty", exist_ok=True)
    lib = HOLE.format(uid=uid("lib", "self"), uid1=uid("lib", "ref"),
                      uid2=uid("lib", "value"), uid3=uid("lib", "pad"),
                      uid4=uid("lib", "fpname"), uid5=uid("lib", "ds"),
                      uid6=uid("lib", "descr"), uid7=uid("lib", "silk"),
                      symbol="", ref="REF**", x=0, y=0,
                      value="PogoPin_D%smm" % DRILL, drill=DRILL, pad=PAD,
                      ring=PAD / 2 + 0.25)
    lib = lib.replace('\t\t(path "/") (sheetname "/") '
                      '(sheetfile "fakir.kicad_sch")\n', "")
    placed = '(layer "B.Cu") (uuid "%s") (at 0 0)' % uid("lib", "self")
    lib = lib.replace(placed,
                      '(version 20260206) (generator "fakir")\n'
                      '\t\t(generator_version "10.0") (layer "B.Cu")')
    open("fakir.pretty/PogoPin_D%smm.kicad_mod" % DRILL, "w").write(
        lib[1:].replace("\n\t", "\n"))
    open("fp-lib-table", "w").write(
        '(fp_lib_table (version 7)\n\t(lib (name "fakir") (type "KiCad")'
        '\n\t\t(uri "${KIPRJMOD}/fakir.pretty") (options "") (descr "")))\n')

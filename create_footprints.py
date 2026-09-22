import os

import dump
import pogo
from ids import uid

# hole = barrel + clearance, snapped to the 0.05 mm the fabs drill in;
# the pad ring is what is left for solder
GRID = 0.05
RING = 0.7

# the board copy and the library copy must agree on every field, or KiCad
# reports lib_footprint_mismatch, so both come out of the same template
BODY = """\t(descr "{key} pogo pin, barrel soldered in: {drill} mm drill")
\t(tags "pogo test point fixture")
\t(property "Reference" "{ref}" (at 0 0 0) (layer "B.Fab") (hide yes)
\t\t(uuid "{uid1}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t(justify mirror)))
\t(property "Value" "{value}" (at 0 {label} 0) (layer "B.SilkS")
\t\t(uuid "{uid2}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t(justify mirror)))
\t(property "Footprint" "" (at 0 0 0) (layer "B.Fab") (hide yes)
\t\t(uuid "{uid3}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t(justify mirror)))
\t(property "Datasheet" "" (at 0 0 0) (layer "B.Fab") (hide yes)
\t\t(uuid "{uid4}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t(justify mirror)))
\t(property "Description" "test point" (at 0 0 0) (layer "B.Fab")
\t\t(hide yes) (uuid "{uid5}")
\t\t(effects (font (size 0.8 0.8) (thickness 0.15)) (justify mirror)))
{path}\t(attr through_hole)
\t(fp_circle (center 0 0) (end {ring} 0)
\t\t(stroke (width 0.12) (type solid)) (fill no) (layer "B.SilkS")
\t\t(uuid "{uid6}"))
\t(fp_circle (center 0 0) (end {court} 0)
\t\t(stroke (width 0.05) (type solid)) (fill no) (layer "B.CrtYd")
\t\t(uuid "{uid7}"))
\t(pad "1" thru_hole circle (at 0 0) (size {pad} {pad}) (drill {drill})
\t\t(layers "*.Cu" "*.Mask") (uuid "{uid8}"))
\t(embedded_fonts no)
)
"""
PATH = '\t(path "/{symbol}") (sheetname "/") (sheetfile "fakir.kicad_sch")\n'


def drill(pin):
    extra = dump.config()["pcb"]["drill_hole_extra"]
    return round(round((pin["barrel"] + extra) / GRID) * GRID, 2)


def body(key, ref, value, path, tag):
    d = drill(pogo.get(key))
    pad = round(d + RING, 2)
    ids = {"uid%d" % i: uid(tag, str(i)) for i in range(1, 9)}
    return BODY.format(key=key, ref=ref, value=value, path=path, drill=d,
                       pad=pad, ring=pad / 2 + 0.25, court=pad / 2 + 0.3,
                       label=-(pad / 2 + 1.0), **ids)


def library(key):
    head = ('(footprint "PogoPin_%s"\n\t(version 20260206) (generator '
            '"fakir") (generator_version "10.0")\n\t(layer "B.Cu")\n' % key)
    return head + body(key, "REF**", "PogoPin_" + key, "", "lib" + key)


def placed(key, ref, value, x, y, symbol):
    head = ('\t(footprint "fakir:PogoPin_%s"\n\t\t(layer "B.Cu") (uuid "%s") '
            '(at %s %s)\n' % (key, uid("fp", ref), x, y))
    text = body(key, ref, value, PATH.format(symbol=symbol), "fp" + ref)
    return head + text.replace("\n\t", "\n\t\t")[:-3] + "\t)\n"


if __name__ == "__main__":
    os.makedirs("fakir.pretty", exist_ok=True)
    for key in pogo.PINS:
        open("fakir.pretty/PogoPin_%s.kicad_mod" % key, "w").write(
            library(key))

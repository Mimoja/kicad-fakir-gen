import os

import pogo
from create_pcb import uid

# hole = barrel + 0.15 mm, snapped to the 0.05 mm the fabs drill in;
# the pad ring is what is left for solder
CLEARANCE = 0.15
GRID = 0.05
RING = 0.7

MOD = """(footprint "PogoPin_{key}"
\t(version 20260206) (generator "fakir") (generator_version "10.0")
\t(layer "B.Cu")
\t(descr "{key} pogo pin, barrel soldered in: {drill} mm drill / {pad} mm pad")
\t(tags "pogo test point fixture")
\t(attr through_hole)
\t(property "Reference" "REF**" (at 0 0 0) (layer "B.Fab") (hide yes)
\t\t(uuid "{uid1}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t(justify mirror)))
\t(property "Value" "PogoPin_{key}" (at 0 {label} 0) (layer "B.SilkS")
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


def drill(pin):
    return round(round((pin["barrel"] + CLEARANCE) / GRID) * GRID, 2)


def footprint(key):
    pin = pogo.get(key)
    d = drill(pin)
    ids = {"uid%d" % i: uid("lib", key, str(i)) for i in range(1, 9)}
    pad = round(d + RING, 2)
    return MOD.format(key=key, drill=d, pad=pad, ring=pad / 2 + 0.25,
                      court=pad / 2 + 0.3, label=-(pad / 2 + 1.0), **ids)


if __name__ == "__main__":
    os.makedirs("fakir.pretty", exist_ok=True)
    for key in pogo.PINS:
        open("fakir.pretty/PogoPin_%s.kicad_mod" % key, "w").write(
            footprint(key))

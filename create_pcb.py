import uuid

# copied from dump.py, B.Cu only
TPS = [
    ("TP7", 45.79, 35.82, "VBAT"),
    ("TP11", 56.4, 72.725, "+3.3V"),
    ("TP12", 62.7, 72.725, "SWCLK"),
    ("TP13", 65.85, 72.725, "SWDIO"),
    ("TP14", 59.55, 72.725, "GND"),
    ("TP15", 69.0, 72.725, "RUN"),
    ("TP18", 46.25, 21.65, "UART_0_RX"),
    ("TP19", 46.25, 18.1, "UART_0_TX"),
    ("TP20", 29.05, 27.05, "UART_1_TX"),
    ("TP21", 32.3, 27.05, "UART_1_RX"),
    ("TP22", 21.34, 55.973333, "PWM4"),
    ("TP23", 21.34, 62.596667, "PWM5"),
    ("TP24", 21.34, 69.22, "PWM6"),
    ("TP25", 21.34, 49.35, "PWM3"),
    ("TP26", 22.6, 39.05, "PWM2"),
    ("TP27", 22.7, 26.95, "PWM1"),
    ("TP28", 28.5, 18.35, "GND"),
    ("TP29", 25.15, 18.35, "+3.3V"),
]
OUTLINE = (14.250267, 13.336867, 76.500267, 78.999999)   # rect, radius 4
MARGIN = 7.0

HEAD = """(kicad_pcb
\t(version 20260206)
\t(generator "fakir")
\t(generator_version "10.0")
\t(general (thickness 1.6) (legacy_teardrops no))
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

LINE = """\t(gr_line (start {} {}) (end {} {})
\t\t(stroke (width {}) (type solid)) (layer "{}") (uuid "{}"))
"""

# TestPoint_Pad_D1.5mm
TESTPOINT = """\t(footprint "TestPoint:TestPoint_Pad_D1.5mm"
\t\t(layer "B.Cu") (uuid "{uid}") (at {x} {y})
\t\t(property "Reference" "{ref}" (at 0 -1.5 0) (layer "B.SilkS")
\t\t\t(uuid "{uid1}") (effects (font (size 0.8 0.8) (thickness 0.15))
\t\t\t(justify mirror)))
\t\t(property "Value" "{value}" (at 0 1.5 0) (layer "B.Fab") (hide yes)
\t\t\t(uuid "{uid2}") (effects (font (size 1 1) (thickness 0.15))
\t\t\t(justify mirror)))
\t\t(attr exclude_from_pos_files exclude_from_bom)
\t\t(pad "1" smd circle (at 0 0) (size 1.5 1.5)
\t\t\t(layers "B.Cu" "B.Mask") (uuid "{uid3}"))
\t)
"""


def uid():
    return str(uuid.uuid4())


def rect(x1, y1, x2, y2, layer, width):
    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    out = ""
    for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
        out += LINE.format(ax, ay, bx, by, width, layer, uid())
    return out


if __name__ == "__main__":
    x1, y1, x2, y2 = OUTLINE
    out = HEAD
    out += rect(x1 - MARGIN, y1 - MARGIN, x2 + MARGIN, y2 + MARGIN,
                "Edge.Cuts", 0.1)
    out += rect(x1, y1, x2, y2, "F.SilkS", 0.12)
    for ref, x, y, value in TPS:
        out += TESTPOINT.format(uid=uid(), uid1=uid(), uid2=uid(),
                                uid3=uid(), ref=ref, x=x, y=y, value=value)
    out += "\t(embedded_fonts no)\n)\n"
    open("fakir.kicad_pcb", "w").write(out)

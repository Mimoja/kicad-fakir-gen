import cadquery as cq

import dump

BARREL = 1.02      # P75 pogo pin

# positions come from the fixture PCB, so the block and the board cannot
# disagree about where a probe is
cfg = dump.config()
pcb = dump.parse(open("fakir.kicad_pcb").read())
tps = dump.test_points(pcb, cfg["ref_pattern"], "B.Cu")
x1, y1, x2, y2 = dump.outline(pcb)
cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
bore = BARREL + cfg["holder"]["print_hole_allowance"]
thick = cfg["holder"]["thickness"]

holes = [(x - cx, -(y - cy)) for _, x, y, _ in tps]
holder = (cq.Workplane("XY").box(x2 - x1, y2 - y1, thick, centered=(1, 1, 0))
          .edges("|Z").fillet(3.0)
          .faces(">Z").workplane().pushPoints(holes).hole(bore))
cq.exporters.export(holder, "holder.step")
cq.exporters.export(holder, "holder.stl", tolerance=0.01)

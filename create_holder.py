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

# feet: the probe tails stand proud under the PCB, so it cannot lie flat.
# Spacers under the corner screws, M3 clearance through them.
mounts = dump.test_points(pcb, r"^H\d+$", "F.Cu")
feet = (cq.Workplane("XY")
        .pushPoints([(x - cx, -(y - cy)) for _, x, y, _ in mounts])
        .circle(3.5).extrude(8.0)
        .faces("<Z").workplane().pushPoints(
            [(x - cx, y - cy) for _, x, y, _ in mounts]).hole(3.4))
cq.exporters.export(feet, "feet.step")
cq.exporters.export(feet, "feet.stl", tolerance=0.01)

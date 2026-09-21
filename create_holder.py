import cadquery as cq

import dump

# P75 pogo pin
BARREL = 1.02
LENGTH = 16.6
STROKE = 2.65

PCB = 1.6
GUIDE_WALL = 1.1
BOSS = 7.0
# M3 heat-set insert from the top of the boss, 3 mm of floor under it;
# the screw comes up from below through foot, PCB and floor
INSERT_BORE = 4.0
INSERT_DEPTH = 6.0
INSERT_FLOOR = 3.0
PASSAGE = 3.4
TAP = 2.5
BOSS_HEIGHT = INSERT_DEPTH + INSERT_FLOOR

# positions come from the fixture PCB, so the holder and the board cannot
# disagree about where a probe is
cfg = dump.config()
holder_cfg = cfg["holder"]
pcb = dump.parse(open("fakir.kicad_pcb").read())
tps = dump.test_points(pcb, cfg["ref_pattern"], "B.Cu")
mounts = dump.test_points(pcb, r"^H\d+$", "F.Cu")
x1, y1, x2, y2 = dump.outline(pcb)
cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
bore = BARREL + holder_cfg["print_hole_allowance"]
base = holder_cfg["base_thickness"]

# the board under test decides how big the plate is: its bounding box,
# the clearance to drop it in, and a border of plastic around that
bx1, by1, bx2, by2 = dump.outline(dump.board())
grow = holder_cfg["board_clearance"] + 2 * holder_cfg["body_border"]
width, depth = bx2 - bx1 + grow, by2 - by1 + grow

# The probe stands LENGTH - PCB above the fixture PCB.  The board rests
# where it has pushed the plungers in by 2/3 of their stroke; the pillars
# hold 2/3 of what stands out.  Nothing else reaches up to the board.
stand = LENGTH - PCB
board_height = round(stand - STROKE * 2 / 3, 2)
guide_height = round(stand * 2 / 3, 2)

pins = [(x - cx, -(y - cy)) for _, x, y, _ in tps]
screws = [(x - cx, -(y - cy)) for _, x, y, _ in mounts]

plate = (cq.Workplane("XY").box(width, depth, base, centered=(1, 1, 0))
         .edges("|Z").fillet(3.0))
pillars = (cq.Workplane("XY").placeSketch(
    cq.Sketch().push(pins).circle(bore / 2 + GUIDE_WALL))
    .extrude(guide_height))
# each boss is tied to the nearest corner of the plate by a flat arm
holder = plate.union(pillars)
for sx, sy in screws:
    corner = (max(-width / 2 + 3, min(width / 2 - 3, sx)),
              max(-depth / 2 + 3, min(depth / 2 - 3, sy)))
    arm = (cq.Sketch().arc((sx, sy), BOSS / 2, 0, 360)
           .arc(corner, 3.0, 0, 360).hull())
    holder = holder.union(
        cq.Workplane("XY").placeSketch(arm).extrude(BOSS_HEIGHT))
holder = (holder
          .faces(">Z").workplane().pushPoints(pins).hole(bore)
          .copyWorkplane(cq.Workplane("XY", origin=(0, 0, BOSS_HEIGHT)))
          .pushPoints(screws))
if cfg["holder"]["threaded_inserts"]:
    holder = holder.cboreHole(PASSAGE, INSERT_BORE, INSERT_DEPTH)
else:
    holder = holder.hole(TAP)
print("board sits at %.2f mm, pillars reach %.2f mm"
      % (board_height, guide_height))
cq.exporters.export(holder, "holder.step")
cq.exporters.export(holder, "holder.stl", tolerance=0.01)

# feet: the probe tails stand proud under the PCB, so it cannot lie flat.
# Spacers under the corner screws, M3 clearance through them.
if holder_cfg["feet"]:
    feet = (cq.Workplane("XY").pushPoints(screws).circle(BOSS / 2)
            .extrude(holder_cfg["foot_height"])
            .faces("<Z").workplane().pushPoints(
                [(x, -y) for x, y in screws]).hole(PASSAGE))
    cq.exporters.export(feet, "feet.step")
    cq.exporters.export(feet, "feet.stl", tolerance=0.01)

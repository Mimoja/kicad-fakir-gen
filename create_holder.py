import dump

BARREL = 1.02      # P75 pogo pin

# positions come from the fixture PCB, so the block and the board cannot
# disagree about where a probe is
cfg = dump.config()
pcb = dump.parse(open("fakir.kicad_pcb").read())
tps = dump.test_points(pcb, cfg["ref_pattern"], "B.Cu")
x1, y1, x2, y2 = dump.outline(pcb)
w, d = x2 - x1, y2 - y1
cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
bore = BARREL + cfg["holder"]["print_hole_allowance"]
thick = cfg["holder"]["thickness"]

out = "$fn = 32;\ndifference() {\n"
out += "  translate([%.3f, %.3f, 0]) cube([%.3f, %.3f, %.3f]);\n" % (
    -w / 2, -d / 2, w, d, thick)
for ref, x, y, _ in tps:
    # OpenSCAD is y-up, KiCad y-down
    out += "  translate([%.3f, %.3f, -1]) cylinder(d=%.2f, h=%.1f); // %s\n" \
        % (x - cx, -(y - cy), bore, thick + 2, ref)
out += "}\n"
open("holder.scad", "w").write(out)

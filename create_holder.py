import dump

# P75 pogo pin: 1.02 mm tihck
BORE = 1.1
THICK = 10.0
MARGIN = 7.0

cfg = dump.config()
b = dump.board()
tps = dump.test_points(b, cfg["ref_pattern"], cfg["test_point_side"])
x1, y1, x2, y2 = dump.outline(b)
w, d = x2 - x1 + 2 * MARGIN, y2 - y1 + 2 * MARGIN
cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

out = "$fn = 32;\ndifference() {\n"
out += "  translate([%.3f, %.3f, 0]) cube([%.3f, %.3f, %.3f]);\n" % (
    -w / 2, -d / 2, w, d, THICK)
for ref, x, y, _ in tps:
    # OpenSCAD is y-up, KiCad y-down
    out += "  translate([%.3f, %.3f, -1]) cylinder(d=%.2f, h=%.1f); // %s\n" \
        % (x - cx, -(y - cy), BORE, THICK + 2, ref)
out += "}\n"
open("holder.scad", "w").write(out)

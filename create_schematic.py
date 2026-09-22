import json

import dump
from create_pcb import mounts
from ids import NAME, uid

HEAD = """(kicad_sch
\t(version 20260306)
\t(generator "fakir")
\t(generator_version "10.0")
\t(uuid "{uid}")
\t(paper "A3")
\t(lib_symbols
\t\t(symbol "Connector:TestPoint"
\t\t\t(pin_numbers (hide yes))
\t\t\t(pin_names (offset 0.762) (hide yes))
\t\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes)
\t\t\t(duplicate_pin_numbers_are_jumpers no)
\t\t\t(property "Reference" "TP" (at 0 6.858 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (effects (font (size 1.27 1.27))))
\t\t\t(property "Value" "TestPoint" (at 0 5.08 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (effects (font (size 1.27 1.27))))
\t\t\t(property "Footprint" "" (at 5.08 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(property "Datasheet" "" (at 5.08 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(property "Description" "test point" (at 0 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(property "ki_keywords" "test point tp" (at 0 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(property "ki_fp_filters" "Pin* Test*" (at 0 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(symbol "TestPoint_0_1"
\t\t\t\t(circle (center 0 3.302) (radius 0.762)
\t\t\t\t\t(stroke (width 0) (type default)) (fill (type none))))
\t\t\t(symbol "TestPoint_1_1"
\t\t\t\t(pin passive line (at 0 0 90) (length 2.54)
\t\t\t\t\t(name "1" (effects (font (size 1.27 1.27))))
\t\t\t\t\t(number "1" (effects (font (size 1.27 1.27))))))
\t\t\t(embedded_fonts no)
\t\t)
\t\t(symbol "Mechanical:MountingHole"
\t\t\t(pin_numbers (hide yes))
\t\t\t(pin_names (offset 1.016) (hide yes))
\t\t\t(exclude_from_sim yes) (in_bom yes) (on_board yes) (in_pos_files no)
\t\t\t(duplicate_pin_numbers_are_jumpers no)
\t\t\t(property "Reference" "H" (at 0 5.08 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (effects (font (size 1.27 1.27))))
\t\t\t(property "Value" "MountingHole" (at 0 3.175 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (effects (font (size 1.27 1.27))))
\t\t\t(property "Footprint" "" (at 0 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(property "Datasheet" "~" (at 0 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(property "Description" "Mounting Hole without connection"
\t\t\t\t(at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(property "ki_keywords" "mounting hole" (at 0 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(property "ki_fp_filters" "MountingHole*" (at 0 0 0) (show_name no)
\t\t\t\t(do_not_autoplace no) (hide yes)
\t\t\t\t(effects (font (size 1.27 1.27))))
\t\t\t(symbol "MountingHole_0_1"
\t\t\t\t(circle (center 0 0) (radius 1.27)
\t\t\t\t\t(stroke (width 1.27) (type default)) (fill (type none))))
\t\t\t(embedded_fonts no)
\t\t)
\t)
"""

MOUNT = """\t(symbol
\t\t(lib_id "Mechanical:MountingHole") (at {x} {y} 0) (unit 1)
\t\t(exclude_from_sim yes) (in_bom yes) (on_board yes) (in_pos_files no)
\t\t(dnp no) (uuid "{uid}")
\t\t(property "Reference" "{ref}" (at {rx} {ry} 0)
\t\t\t(effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Value" "MountingHole_M3" (at {rx} {y} 0)
\t\t\t(effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "MountingHole:MountingHole_3.2mm_M3" (at {x} {y} 0)
\t\t\t(hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "" (at {x} {y} 0) (hide yes)
\t\t\t(effects (font (size 1.27 1.27))))
\t\t(property "Description" "M3 mounting hole" (at {x} {y} 0) (hide yes)
\t\t\t(effects (font (size 1.27 1.27))))
\t\t(instances (project "{name}" (path "/{root}"
\t\t\t(reference "{ref}") (unit 1))))
\t)
"""

SYMBOL = """\t(symbol
\t\t(lib_id "Connector:TestPoint") (at {x} {y} 0) (unit 1)
\t\t(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
\t\t(uuid "{uid}")
\t\t(property "Reference" "{ref}" (at {rx} {ry} 0)
\t\t\t(effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Value" "{value}" (at {rx} {vy} 0)
\t\t\t(effects (font (size 1.27 1.27)) (justify left)))
\t\t(property "Footprint" "fakir:PogoPin_{pin}" (at {x} {y} 0)
\t\t\t(hide yes) (effects (font (size 1.27 1.27))))
\t\t(property "Datasheet" "" (at {x} {y} 0) (hide yes)
\t\t\t(effects (font (size 1.27 1.27))))
\t\t(property "Description" "test point" (at {x} {y} 0) (hide yes)
\t\t\t(effects (font (size 1.27 1.27))))
\t\t(pin "1" (uuid "{pinid}"))
\t\t(instances (project "{name}" (path "/{root}"
\t\t\t(reference "{ref}") (unit 1))))
\t)
"""

cfg = dump.config()
TPS = dump.test_points(dump.board(), cfg["ref_pattern"],
                       cfg["test_point_side"])
root = uid("sheet", "root")
out = HEAD.format(uid=root)
for index, (ref, _, _, value) in enumerate(TPS):
    x = 30.48 + (index % 6) * 25.4
    y = 30.48 + (index // 6) * 25.4
    out += SYMBOL.format(x=x, y=y, rx=x + 2.54, ry=y - 6.35, vy=y - 3.81,
                         ref=ref, value=value, uid=uid("sym", ref),
                         pin=cfg["pogo_pin"], name=NAME, root=root,
                         pinid=uid("pin", ref))
row = 30.48 + (len(TPS) // 6 + 1) * 25.4
for index, (ref, _, _) in enumerate(mounts(0, 0, 0, 0)):
    x = 30.48 + index * 25.4
    out += MOUNT.format(x=x, y=row, rx=x + 2.54, ry=row - 2.54, ref=ref,
                        uid=uid("mountsym", ref), name=NAME, root=root)
out += "\t(sheet_instances (path \"/\" (page \"1\")))\n"
out += "\t(embedded_fonts no)\n)\n"
open("fakir.kicad_sch", "w").write(out)

# the project file: enough for KiCad to open it, plus the sheet list
project = {
    "board": {"design_settings": {"defaults": {}}, "layer_presets": [],
              "viewports": []},
    "boards": [],
    "cvpcb": {"equivalence_files": []},
    "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
    "meta": {"filename": NAME + ".kicad_pro", "version": 3},
    "net_settings": {"classes": [{"name": "Default", "clearance": 0.2,
                                  "track_width": 0.25, "via_diameter": 0.8,
                                  "via_drill": 0.4}],
                     "meta": {"version": 4}},
    "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
    "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
    "sheets": [[root, NAME]],
    "text_variables": {},
}
open(NAME + ".kicad_pro", "w").write(json.dumps(project, indent=2) + "\n")

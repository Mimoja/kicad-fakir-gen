from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence, Tuple

from .geometry import (Outline, clearance_warnings, make_outline,
                       rounded_rect_edges)
from .model import FixtureConfig, TestPoint
from .project import GENERATED_MARKER
from .sexpr import Node, Sym, dumps, find, loads, num

PCB_VERSION = "20260206"
SCH_VERSION = "20260306"
GENERATOR = "fakir"
GENERATOR_VERSION = "10.0"

SILK_TEXT_MM = 0.8
NOTE_TEXT_MM = 1.2

# schematic layout
SCH_COLS = 6
SCH_PITCH_MM = 25.4
SCH_ORIGIN_MM = (30.48, 30.48)
SCH_PAPER = "A3"

_YES = Sym("yes")
_NO = Sym("no")

_TAGS = "pogo test point fixture"


# Stock symbols, embedded so the schematic opens without the libraries.
_TESTPOINT_SYMBOL = r"""
(symbol "Connector:TestPoint"
  (pin_numbers (hide yes))
  (pin_names (offset 0.762) (hide yes))
  (exclude_from_sim no)
  (in_bom yes)
  (on_board yes)
  (in_pos_files yes)
  (duplicate_pin_numbers_are_jumpers no)
  (property "Reference" "TP" (at 0 6.858 0) (show_name no) (do_not_autoplace no)
    (effects (font (size 1.27 1.27))))
  (property "Value" "TestPoint" (at 0 5.08 0) (show_name no) (do_not_autoplace no)
    (effects (font (size 1.27 1.27))))
  (property "Footprint" "" (at 5.08 0 0) (show_name no) (do_not_autoplace no) (hide yes)
    (effects (font (size 1.27 1.27))))
  (property "Datasheet" "" (at 5.08 0 0) (show_name no) (do_not_autoplace no) (hide yes)
    (effects (font (size 1.27 1.27))))
  (property "Description" "test point" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes)
    (effects (font (size 1.27 1.27))))
  (property "ki_keywords" "test point tp" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes)
    (effects (font (size 1.27 1.27))))
  (property "ki_fp_filters" "Pin* Test*" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes)
    (effects (font (size 1.27 1.27))))
  (symbol "TestPoint_0_1"
    (circle (center 0 3.302) (radius 0.762)
      (stroke (width 0) (type default)) (fill (type none))))
  (symbol "TestPoint_1_1"
    (pin passive line (at 0 0 90) (length 2.54)
      (name "1" (effects (font (size 1.27 1.27))))
      (number "1" (effects (font (size 1.27 1.27))))))
  (embedded_fonts no)
)
"""

_MOUNTING_HOLE_SYMBOL = r"""
(symbol "Mechanical:MountingHole"
  (pin_numbers (hide yes))
  (pin_names (offset 1.016) (hide yes))
  (exclude_from_sim yes)
  (in_bom yes)
  (on_board yes)
  (in_pos_files no)
  (duplicate_pin_numbers_are_jumpers no)
  (property "Reference" "H" (at 0 5.08 0) (show_name no) (do_not_autoplace no)
    (effects (font (size 1.27 1.27))))
  (property "Value" "MountingHole" (at 0 3.175 0) (show_name no) (do_not_autoplace no)
    (effects (font (size 1.27 1.27))))
  (property "Footprint" "" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes)
    (effects (font (size 1.27 1.27))))
  (property "Datasheet" "~" (at 0 0 0) (show_name no) (do_not_autoplace no) (hide yes)
    (effects (font (size 1.27 1.27))))
  (property "Description" "Mounting Hole without connection" (at 0 0 0)
    (show_name no) (do_not_autoplace no) (hide yes)
    (effects (font (size 1.27 1.27))))
  (property "ki_keywords" "mounting hole" (at 0 0 0) (show_name no)
    (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
  (property "ki_fp_filters" "MountingHole*" (at 0 0 0) (show_name no)
    (do_not_autoplace no) (hide yes) (effects (font (size 1.27 1.27))))
  (symbol "MountingHole_0_1"
    (circle (center 0 0) (radius 1.27)
      (stroke (width 1.27) (type default)) (fill (type none))))
  (embedded_fonts no)
)
"""

_LAYERS: List[Tuple[int, str, str, Optional[str]]] = [
    (0, "F.Cu", "signal", None),
    (2, "B.Cu", "signal", None),
    (9, "F.Adhes", "user", "F.Adhesive"),
    (11, "B.Adhes", "user", "B.Adhesive"),
    (13, "F.Paste", "user", None),
    (15, "B.Paste", "user", None),
    (5, "F.SilkS", "user", "F.Silkscreen"),
    (7, "B.SilkS", "user", "B.Silkscreen"),
    (1, "F.Mask", "user", None),
    (3, "B.Mask", "user", None),
    (17, "Dwgs.User", "user", "User.Drawings"),
    (19, "Cmts.User", "user", "User.Comments"),
    (21, "Eco1.User", "user", "User.Eco1"),
    (23, "Eco2.User", "user", "User.Eco2"),
    (25, "Edge.Cuts", "user", None),
    (27, "Margin", "user", None),
    (31, "F.CrtYd", "user", "F.Courtyard"),
    (29, "B.CrtYd", "user", "B.Courtyard"),
    (35, "F.Fab", "user", None),
    (33, "B.Fab", "user", None),
]

Placed = Sequence[Tuple[TestPoint, float, float]]
Mounts = Sequence[Tuple[str, float, float]]


class FixtureFiles:
    def __init__(self, files: Dict[str, str], warnings: List[str],
                 outline: Outline, placed: Placed, root_uuid: str = ""):
        self.files = files
        self.warnings = warnings
        self.outline = outline
        self.placed = placed
        self.root_uuid = root_uuid


def _font(size: float = 1.0, thickness: Optional[float] = 0.15) -> Node:
    font: Node = ["font", ["size", num(size), num(size)]]
    if thickness is not None:
        font.append(["thickness", num(thickness)])
    return font


def _effects(layer: str, size: float = 1.0,
             thickness: Optional[float] = 0.15) -> Node:
    effects: Node = ["effects", _font(size, thickness)]
    if layer.startswith("B."):
        effects.append(["justify", Sym("mirror")])   # read through the board
    return effects


def _property(name: str, value: str, x: float, y: float, layer: str,
              uid: str, hide: bool = False) -> Node:
    node: Node = ["property", name, value,
                  ["at", num(x), num(y), num(0)], ["layer", layer]]
    if hide:
        node.append(["hide", _YES])
    node.append(["uuid", uid])
    node.append(_effects(layer, size=SILK_TEXT_MM))
    return node


def _stroke(width: float) -> Node:
    return ["stroke", ["width", num(width)], ["type", Sym("solid")]]


def _descr(cfg: FixtureConfig) -> str:
    # The library and board copies must match exactly or KiCad reports
    # lib_footprint_mismatch.
    return ("%s pogo pin, barrel soldered in: %.2f mm drill / %.2f mm pad, "
            "generated by fakir" % (cfg.pogo_key, cfg.drill, cfg.pad))


def _probe_properties(cfg: FixtureConfig, uid, ref: str,
                      value: str) -> List[Node]:
    offset = cfg.pad / 2.0 + 0.2 + SILK_TEXT_MM
    return [
        _property("Reference", ref, 0, 0, cfg.fab_layer, uid("ref"),
                  hide=True),
        _property("Value", value, 0, -offset, cfg.silk_layer, uid("value")),
        _property("Footprint", "", 0, 0, cfg.fab_layer, uid("fpname"),
                  hide=True),
        _property("Datasheet", "", 0, 0, cfg.fab_layer, uid("ds"), hide=True),
        _property("Description", _descr(cfg), 0, 0, cfg.fab_layer,
                  uid("descr"), hide=True),
    ]


def _probe_graphics(cfg: FixtureConfig, uid) -> List[Node]:
    return [
        ["fp_circle",
         ["center", num(0), num(0)],
         ["end", num(cfg.pad / 2.0 + 0.25), num(0)],
         _stroke(0.12), ["fill", _NO], ["layer", cfg.silk_layer],
         ["uuid", uid("silk")]],
        ["fp_circle",
         ["center", num(0), num(0)],
         ["end", num(cfg.pad / 2.0 + 0.30), num(0)],
         _stroke(0.05), ["fill", _NO], ["layer", cfg.courtyard_layer],
         ["uuid", uid("crtyd")]],
        ["fp_text", Sym("user"), "${REFERENCE}",
         ["at", num(0), num(0), num(0)], ["layer", cfg.fab_layer],
         ["uuid", uid("fab")], _effects(cfg.fab_layer, size=SILK_TEXT_MM)],
    ]


def _probe_pad(cfg: FixtureConfig, uid: str) -> Node:
    return ["pad", "1", Sym("thru_hole"), Sym("circle"),
            ["at", num(0), num(0)],
            ["size", num(cfg.pad), num(cfg.pad)],
            ["drill", num(cfg.drill)],
            ["layers", "*.Cu", "*.Mask"],
            ["uuid", uid]]


def _probe_model(cfg: FixtureConfig) -> List[Node]:
    if not cfg.probe_model:
        return []
    # The model is built along +Z from the pad.  On a B.Cu footprint KiCad
    # points that away from the board, so it is flipped to reach up.
    return [[
        "model", _model_path(cfg, "%s.step" % cfg.footprint_name),
        ["offset", ["xyz", num(0), num(0), num(0)]],
        ["scale", ["xyz", num(1), num(1), num(1)]],
        ["rotate", ["xyz", num(180), num(0), num(0)]],
    ]]


def _model_path(cfg: FixtureConfig, filename: str) -> str:
    return "${KIPRJMOD}/%s.%s/%s" % (cfg.name, cfg.model_dir, filename)


def footprint_library(cfg: FixtureConfig) -> str:
    def uid(tag: str) -> str:
        return cfg.uid("lib", cfg.footprint_name, tag)

    node: Node = [
        "footprint", cfg.footprint_name,
        ["version", Sym(PCB_VERSION)],
        ["generator", GENERATOR],
        ["generator_version", GENERATOR_VERSION],
        ["layer", cfg.mating_layer],
        ["descr", _descr(cfg)],
        ["tags", _TAGS],
        ["attr", Sym("through_hole")],
    ]
    node += _probe_properties(cfg, uid, "REF**", cfg.footprint_name)
    node += _probe_graphics(cfg, uid)
    node.append(_probe_pad(cfg, uid("pad")))
    node += _probe_model(cfg)
    node.append(["embedded_fonts", _NO])
    return dumps(node) + "\n"


def _board_probe(cfg: FixtureConfig, point: TestPoint, x: float, y: float,
                 symbol_uuid: str) -> Node:
    def uid(tag: str) -> str:
        return cfg.uid("fp", point.ref, tag)

    # Rotation is always 0: the contact is round, and the board copies
    # must match the library copy.
    node: Node = [
        "footprint", cfg.footprint_id,
        ["layer", cfg.mating_layer],
        ["uuid", uid("self")],
        ["at", num(x), num(y), num(0)],
        ["descr", _descr(cfg)],
        ["tags", _TAGS],
    ]
    node += _probe_properties(cfg, uid, point.ref, point.label)
    node += [
        ["path", "/%s" % symbol_uuid],
        ["sheetname", "/"],
        ["sheetfile", "%s.kicad_sch" % cfg.name],
        ["attr", Sym("through_hole")],
        ["duplicate_pad_numbers_are_jumpers", _NO],
    ]
    node += _probe_graphics(cfg, uid)
    node.append(_probe_pad(cfg, uid("pad")))
    node += _probe_model(cfg)
    node.append(["embedded_fonts", _NO])
    return node


def _board_mount(cfg: FixtureConfig, ref: str, x: float, y: float) -> Node:
    hole = cfg.stock_mount
    if hole is None:
        raise ValueError("%.2f mm is not a drill KiCad has a MountingHole for"
                         % cfg.mount_drill_mm)
    lib_id, template, _ = hole

    def uid(tag: str) -> str:
        return cfg.uid("mount", ref, tag)

    node: Node = [item for item in template
                  if not (isinstance(item, list)
                          and str(item[0]) in ("version", "generator",
                                               "generator_version"))]
    node[1] = lib_id

    # KiCad's order for a placed footprint: layer, uuid, at, then the rest.
    def index_of(head: str, pick=min) -> int:
        return pick(i for i, item in enumerate(node)
                    if isinstance(item, list) and str(item[0]) == head)

    after_layer = index_of("layer") + 1
    node[after_layer:after_layer] = [["uuid", uid("self")],
                                     ["at", num(x), num(y), num(0)]]
    last_property = index_of("property", max)
    node[last_property + 1:last_property + 1] = [
        ["path", "/%s" % cfg.uid("mountsym", ref)],
        ["sheetname", "/"],
        ["sheetfile", "%s.kicad_sch" % cfg.name],
    ]

    counter = 0
    for item in node:
        if not isinstance(item, list):
            continue
        head = str(item[0])
        if (head == "property" and len(item) > 2
                and str(item[1]) == "Reference"):
            item[2] = ref
            if not any(isinstance(part, list) and str(part[0]) == "hide"
                       for part in item):
                layer_at = next(i for i, part in enumerate(item)
                                if isinstance(part, list)
                                and str(part[0]) == "layer")
                item.insert(layer_at + 1, ["hide", _YES])
        if head in ("property", "fp_circle", "fp_line", "fp_arc", "fp_text",
                    "pad"):
            counter += 1
            item.append(["uuid", uid("i%d" % counter)])
    return node


def mount_positions(cfg: FixtureConfig,
                    outline: Outline) -> List[Tuple[str, float, float]]:
    inset = cfg.mount_inset
    return [
        ("H1", outline.x0 + inset, outline.y0 + inset),
        ("H2", outline.x1 - inset, outline.y0 + inset),
        ("H3", outline.x1 - inset, outline.y1 - inset),
        ("H4", outline.x0 + inset, outline.y1 - inset),
    ]


def _board_notes(cfg: FixtureConfig, outline: Outline) -> List[Node]:
    centre_x, _ = outline.centre
    y = outline.y1 - min(cfg.margin_mm / 2.0, 3.0)
    nodes: List[Node] = []
    for text, layer, tag in ((cfg.board_note_top, cfg.note_layer, "note"),
                             (cfg.board_note_bottom, cfg.silk_layer,
                              "note-bottom")):
        if text:
            nodes.append(["gr_text", text,
                          ["at", num(centre_x), num(y), num(0)],
                          ["layer", layer], ["uuid", cfg.uid(tag)],
                          _effects(layer, size=NOTE_TEXT_MM,
                                   thickness=NOTE_TEXT_MM * 0.15)])
    return nodes


def _holder_outline(cfg: FixtureConfig, outline: Outline,
                    mounts: Mounts) -> List[Node]:
    dut = cfg.dut_size
    if not dut:
        return []
    centre_x, centre_y = outline.centre
    half_w = (dut[0] + cfg.board_clearance_mm) / 2.0 + cfg.body_border_mm
    half_d = (dut[1] + cfg.board_clearance_mm) / 2.0 + cfg.body_border_mm

    nodes: List[Node] = []
    for layer in (cfg.note_layer, cfg.silk_layer):
        nodes += rounded_rect_edges(
            centre_x - half_w, centre_y - half_d, centre_x + half_w,
            centre_y + half_d, cfg.corner_radius_mm, layer, 0.1,
            lambda tag, layer=layer: cfg.uid("holder", layer, tag))
        for ref, x, y in mounts:
            nodes.append(["gr_circle",
                          ["center", num(x), num(y)],
                          ["end", num(x + cfg.boss_mm / 2.0), num(y)],
                          _stroke(0.1), ["fill", _NO], ["layer", layer],
                          ["uuid", cfg.uid("boss", layer, ref)]])
    return nodes


def _dut_outline(cfg: FixtureConfig) -> List[Node]:
    nodes: List[Node] = []
    for layer in (cfg.note_layer, cfg.silk_layer):
        for index, segment in enumerate(cfg.dut_outline or ()):
            uid = cfg.uid("dut", layer, str(index))
            kind = segment[0]
            if kind == "line":
                _, x1, y1, x2, y2 = segment
                nodes.append(["gr_line",
                              ["start", num(x1), num(y1)],
                              ["end", num(x2), num(y2)],
                              _stroke(0.12), ["layer", layer], ["uuid", uid]])
            elif kind == "arc":
                _, sx, sy, mx, my, ex, ey = segment
                nodes.append(["gr_arc",
                              ["start", num(sx), num(sy)],
                              ["mid", num(mx), num(my)],
                              ["end", num(ex), num(ey)],
                              _stroke(0.12), ["layer", layer], ["uuid", uid]])
            elif kind == "circle":
                _, cx, cy, radius = segment
                nodes.append(["gr_circle",
                              ["center", num(cx), num(cy)],
                              ["end", num(cx + radius), num(cy)],
                              _stroke(0.12), ["fill", _NO],
                              ["layer", layer], ["uuid", uid]])
    return nodes


def board(cfg: FixtureConfig, placed: Placed, outline: Outline,
          symbol_uuids: Dict[str, str]) -> str:
    layers: Node = ["layers"]
    for index, name, kind, alias in _LAYERS:
        entry: Node = [Sym(str(index)), name, Sym(kind)]
        if alias:
            entry.append(alias)
        layers.append(entry)

    node: Node = [
        "kicad_pcb",
        ["version", Sym(PCB_VERSION)],
        ["generator", GENERATOR],
        ["generator_version", GENERATOR_VERSION],
        ["general", ["thickness", num(cfg.thickness_mm)],
         ["legacy_teardrops", _NO]],
        ["paper", "A4"],
        layers,
        ["setup", ["pad_to_mask_clearance", num(0)]],
        ["net", Sym("0"), ""],
    ]
    node += rounded_rect_edges(outline.x0, outline.y0, outline.x1, outline.y1,
                               outline.radius, "Edge.Cuts", 0.1,
                               lambda tag: cfg.uid("edge", "edge-" + tag))
    mounts = mount_positions(cfg, outline)
    for point, x, y in placed:
        node.append(_board_probe(cfg, point, x, y, symbol_uuids[point.ref]))
    for ref, x, y in mounts:
        node.append(_board_mount(cfg, ref, x, y))
    node += _dut_outline(cfg)
    node += _holder_outline(cfg, outline, mounts)
    node += _board_notes(cfg, outline)
    node.append(["embedded_fonts", _NO])
    return dumps(node) + "\n"


def _sch_property(name: str, value: str, x: float, y: float,
                  hide: bool = False) -> Node:
    node: Node = ["property", name, value, ["at", num(x), num(y), num(0)]]
    if hide:
        node.append(["hide", _YES])
    node += [["show_name", _NO], ["do_not_autoplace", _NO],
             ["effects", _font(1.27, thickness=None),
              ["justify", Sym("left")]]]
    return node


def _instances(cfg: FixtureConfig, root_uuid: str, ref: str) -> Node:
    return ["instances",
            ["project", cfg.name,
             ["path", "/%s" % root_uuid,
              ["reference", ref], ["unit", Sym("1")]]]]


def _mount_symbol(cfg: FixtureConfig, ref: str, x: float, y: float,
                  root_uuid: str) -> Node:
    return [
        "symbol",
        ["lib_id", "Mechanical:MountingHole"],
        ["at", num(x), num(y), num(0)],
        ["unit", Sym("1")],
        ["body_style", Sym("1")],
        ["exclude_from_sim", _YES],
        ["in_bom", _YES],
        ["on_board", _YES],
        ["in_pos_files", _NO],
        ["dnp", _NO],
        ["uuid", cfg.uid("mountsym", ref)],
        _sch_property("Reference", ref, x + 2.54, y - 2.54),
        _sch_property("Value", "MountingHole_M3", x + 2.54, y),
        _sch_property("Footprint", cfg.mount_footprint_id, x, y + 2.54,
                      hide=True),
        _sch_property("Datasheet", "", x, y + 2.54, hide=True),
        _sch_property("Description", "M3 mounting hole", x, y, hide=True),
        _instances(cfg, root_uuid, ref),
    ]


def schematic(cfg: FixtureConfig, points: Sequence[TestPoint],
              symbol_uuids: Dict[str, str], root_uuid: str,
              mounts: Mounts = ()) -> str:
    node: Node = [
        "kicad_sch",
        ["version", Sym(SCH_VERSION)],
        ["generator", GENERATOR],
        ["generator_version", GENERATOR_VERSION],
        ["uuid", root_uuid],
        ["paper", SCH_PAPER],
        ["lib_symbols", loads(_TESTPOINT_SYMBOL),
         loads(_MOUNTING_HOLE_SYMBOL)],
    ]

    origin_x, origin_y = SCH_ORIGIN_MM
    for index, point in enumerate(points):
        x = origin_x + (index % SCH_COLS) * SCH_PITCH_MM
        y = origin_y + (index // SCH_COLS) * SCH_PITCH_MM
        node.append([
            "symbol",
            ["lib_id", "Connector:TestPoint"],
            ["at", num(x), num(y), num(0)],
            ["unit", Sym("1")],
            ["body_style", Sym("1")],
            ["exclude_from_sim", _NO],
            ["in_bom", _YES],
            ["on_board", _YES],
            ["in_pos_files", _YES],
            ["dnp", _NO],
            ["uuid", symbol_uuids[point.ref]],
            _sch_property("Reference", point.ref, x + 2.54, y - 6.35),
            _sch_property("Value", point.label, x + 2.54, y - 3.81),
            _sch_property("Footprint", cfg.footprint_id, x, y + 2.54,
                          hide=True),
            _sch_property("Datasheet", "", x, y + 2.54, hide=True),
            _sch_property("Description", "test point", x, y, hide=True),
            ["pin", "1", ["uuid", cfg.uid("pin", point.ref)]],
            _instances(cfg, root_uuid, point.ref),
        ])

    rows = max(0, len(points) - 1) // SCH_COLS + 1
    mount_row = origin_y + rows * SCH_PITCH_MM
    for index, (ref, _, _) in enumerate(mounts):
        node.append(_mount_symbol(cfg, ref, origin_x + index * SCH_PITCH_MM,
                                  mount_row, root_uuid))

    node.append(["sheet_instances", ["path", "/", ["page", "1"]]])
    node.append(["embedded_fonts", _NO])
    return dumps(node) + "\n"


def project_file(cfg: FixtureConfig, root_uuid: str,
                 source_name: str = "") -> str:
    data = {
        "board": {"design_settings": {"defaults": {}}, "layer_presets": [],
                  "viewports": []},
        "boards": [],
        "cvpcb": {"equivalence_files": []},
        "erc": {"erc_exclusions": [], "meta": {"version": 0},
                "pin_map": [], "rule_severities": {}, "severities": {}},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": "%s.kicad_pro" % cfg.name, "version": 3},
        "net_settings": {
            "classes": [{
                "bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25,
                "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
                "line_style": 0, "microvia_diameter": 0.3,
                "microvia_drill": 0.1, "name": "Default",
                "pcb_color": "rgba(0, 0, 0, 0.000)",
                "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": 0.25,
                "via_diameter": 0.8, "via_drill": 0.4, "wire_width": 6,
            }],
            "meta": {"version": 4},
            "net_colors": None,
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[root_uuid, cfg.name]],
        "text_variables": {},
        GENERATED_MARKER: {"tool": "fakir", "source": source_name},
    }
    return json.dumps(data, indent=2) + "\n"


def fp_lib_table(cfg: FixtureConfig) -> str:
    node: Node = [
        "fp_lib_table",
        ["version", Sym("7")],
        ["lib",
         ["name", cfg.footprint_lib],
         ["type", "KiCad"],
         ["uri", "${KIPRJMOD}/%s.pretty" % cfg.footprint_lib],
         ["options", ""],
         ["descr", "Pogo pin footprints generated by fakir"]],
    ]
    return dumps(node) + "\n"


def merge_board(existing: str, generated: str, cfg: FixtureConfig) -> str:
    current = loads(existing)
    fresh = loads(generated)
    if not isinstance(current, list) or str(current[0]) != "kicad_pcb":
        raise ValueError("not a KiCad board")

    owned_libs = {cfg.footprint_id, cfg.mount_footprint_id}
    note_uuid = cfg.uid("note")

    def is_ours(item: Node) -> bool:
        head = str(item[0])
        if head == "footprint":
            return len(item) > 1 and str(item[1]) in owned_libs
        if head == "gr_text":
            uuid_node = find(item, "uuid")
            return uuid_node is not None and str(uuid_node[1]) == note_uuid
        return False

    kept = [item for item in current
            if not (isinstance(item, list) and is_ours(item))]
    replacements = [item for item in fresh
                    if isinstance(item, list) and is_ours(item)]
    tail = []
    while kept and isinstance(kept[-1], list) and str(kept[-1][0]) in (
            "embedded_fonts", "embedded_files"):
        tail.insert(0, kept.pop())
    return dumps(kept + replacements + tail) + "\n"


def build(points: Sequence[TestPoint], cfg: FixtureConfig,
          source_name: str = "") -> FixtureFiles:
    ordered = sorted(points, key=lambda p: p.sort_key)
    if not ordered:
        raise ValueError("no test points to place")

    outline = make_outline(ordered, cfg)
    placed = [(p, p.x_mm, p.y_mm) for p in ordered]
    symbol_uuids = {p.ref: cfg.uid("sym", p.ref) for p in ordered}
    root_uuid = cfg.uid("sheet", "root")
    mounts = mount_positions(cfg, outline)

    files = {
        "%s.kicad_pro" % cfg.name: project_file(cfg, root_uuid, source_name),
        "%s.kicad_sch" % cfg.name: schematic(cfg, ordered, symbol_uuids,
                                             root_uuid, mounts),
        "%s.kicad_pcb" % cfg.name: board(cfg, placed, outline, symbol_uuids),
        "fp-lib-table": fp_lib_table(cfg),
        "%s.pretty/%s.kicad_mod" % (cfg.footprint_lib, cfg.footprint_name):
            footprint_library(cfg),
    }
    warnings = clearance_warnings(placed, cfg, outline, mounts)
    return FixtureFiles(files, warnings, outline, placed, root_uuid)

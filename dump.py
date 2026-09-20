import re

import yaml

BOARD = "../AddonBoard.kicad_pcb"


def parse(text):
    # regex is the way parse markup languages. always
    # KiCad writes things like
    #   (footprint "TestPoint:TestPoint_Pad_D1.5mm"
    #     (layer "B.Cu") (at 45.79 35.82)
    #     (property "Reference" "TP7" (at 0 -1.5 0)))
    # and all we want out of it is "(" ")" quoted strings and bare words
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack = [[]]
    for tok in tokens:
        if tok == "(":
            stack.append([])
        elif tok == ")":
            node = stack.pop()
            stack[-1].append(node)
        elif tok.startswith('"'):
            stack[-1].append(tok[1:-1])
        else:
            stack[-1].append(tok)
    return stack[0][0]


def child(node, name):
    for item in node:
        if isinstance(item, list) and item and item[0] == name:
            return item
    return None


def properties(footprint):
    return {item[1]: item[2] for item in footprint
            if isinstance(item, list) and item[0] == "property"}


def xy(node):
    return float(node[1]), float(node[2])


def config():
    return yaml.safe_load(open("config.yaml"))


def board():
    return parse(open(BOARD).read())


def test_points(board, pattern, side):
    out = []
    for node in board:
        if not isinstance(node, list) or node[0] != "footprint":
            continue
        props = properties(node)
        ref = props.get("Reference", "")
        if not re.match(pattern, ref) or child(node, "layer")[1] != side:
            continue
        x, y = xy(child(node, "at"))
        out.append((ref, x, y, props.get("Value", ref)))
    return sorted(out, key=lambda tp: int(re.sub(r"\D", "", tp[0]) or 0))


def segments(board):
    # Edge.Cuts as (kind, points): lines, arcs, and rects split into lines
    # plus corner arcs when they carry a radius
    out = []
    for node in board:
        if not isinstance(node, list) or not node[0].startswith("gr_"):
            continue
        if child(node, "layer")[1] != "Edge.Cuts":
            continue
        kind = node[0][3:]
        if kind == "line":
            out.append(("line", [xy(child(node, "start")),
                                 xy(child(node, "end"))]))
        elif kind == "arc":
            out.append(("arc", [xy(child(node, k))
                                for k in ("start", "mid", "end")]))
        elif kind == "rect":
            x1, y1 = xy(child(node, "start"))
            x2, y2 = xy(child(node, "end"))
            radius = child(node, "radius")
            r = float(radius[1]) if radius else 0.0
            r = min(r, abs(x2 - x1) / 2, abs(y2 - y1) / 2)
            out += rect_segments(min(x1, x2), min(y1, y2), max(x1, x2),
                                 max(y1, y2), r)
    return out


def rect_segments(x1, y1, x2, y2, r):
    if r <= 0:
        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        return [("line", [a, b])
                for a, b in zip(corners, corners[1:] + corners[:1])]
    c = r * (1 - 0.5 ** 0.5)          # where the arc's midpoint sits
    return [
        ("line", [(x1 + r, y1), (x2 - r, y1)]),
        ("arc", [(x2 - r, y1), (x2 - c, y1 + c), (x2, y1 + r)]),
        ("line", [(x2, y1 + r), (x2, y2 - r)]),
        ("arc", [(x2, y2 - r), (x2 - c, y2 - c), (x2 - r, y2)]),
        ("line", [(x2 - r, y2), (x1 + r, y2)]),
        ("arc", [(x1 + r, y2), (x1 + c, y2 - c), (x1, y2 - r)]),
        ("line", [(x1, y2 - r), (x1, y1 + r)]),
        ("arc", [(x1, y1 + r), (x1 + c, y1 + c), (x1 + r, y1)]),
    ]


def outline(board):
    xs = [x for _, points in segments(board) for x, _ in points]
    ys = [y for _, points in segments(board) for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


if __name__ == "__main__":
    cfg = config()
    b = board()
    for tp in test_points(b, cfg["ref_pattern"], cfg["test_point_side"]):
        print(*tp)
    print("extent", *outline(b))

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


def outline(board):
    # only the bounding box for now; arcs and rounded rects are ignored
    xs, ys = [], []
    for node in board:
        if not isinstance(node, list) or not node[0].startswith("gr_"):
            continue
        if child(node, "layer")[1] != "Edge.Cuts":
            continue
        for key in ("start", "mid", "end"):
            point = child(node, key)
            if point:
                x, y = xy(point)
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


if __name__ == "__main__":
    cfg = config()
    b = board()
    for tp in test_points(b, cfg["ref_pattern"], cfg["test_point_side"]):
        print(*tp)
    print("extent", *outline(b))

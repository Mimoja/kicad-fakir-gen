import re

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


board = parse(open(BOARD).read())
for node in board:
    if not isinstance(node, list) or node[0] != "footprint":
        continue
    props = properties(node)
    ref = props.get("Reference", "")
    if not re.match(r"^TP\d+$", ref):
        continue
    at = child(node, "at")
    print(ref, at[1], at[2], child(node, "layer")[1], props.get("Value"))


def xy(node):
    return float(node[1]), float(node[2])


print()
xs, ys = [], []
for node in board:
    if not isinstance(node, list) or not node[0].startswith("gr_"):
        continue
    if child(node, "layer")[1] != "Edge.Cuts":
        continue
    kind = node[0][3:]
    if kind == "rect":
        (x1, y1), (x2, y2) = xy(child(node, "start")), xy(child(node, "end"))
        print("rect", x1, y1, x2, y2, child(node, "radius"))
        xs += [x1, x2]
        ys += [y1, y2]
    elif kind == "line":
        (x1, y1), (x2, y2) = xy(child(node, "start")), xy(child(node, "end"))
        print("line", x1, y1, x2, y2)
        xs += [x1, x2]
        ys += [y1, y2]
    elif kind == "arc":
        for key in ("start", "mid", "end"):
            x, y = xy(child(node, key))
            xs.append(x)
            ys.append(y)
        print("arc", *(xy(child(node, k)) for k in ("start", "mid", "end")))
    else:
        print("?", kind)
print("extent", min(xs), min(ys), max(xs), max(ys))

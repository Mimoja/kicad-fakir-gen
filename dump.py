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

from __future__ import annotations

from typing import Iterator, List, Optional, Tuple, Union


class SexprError(ValueError):
    pass


class Sym(str):
    __slots__ = ()

    def __repr__(self) -> str:
        return "Sym(%s)" % str.__repr__(self)


Node = Union[str, Sym, List["Node"]]

_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"'}


def _tokens(text: str) -> Iterator[Tuple[str, str]]:
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            yield (c, c)
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            buf: List[str] = []
            i += 1
            while True:
                if i >= n:
                    raise SexprError("unterminated string literal")
                c = text[i]
                if c == "\\":
                    if i + 1 >= n:
                        raise SexprError("dangling escape in string literal")
                    buf.append(_ESCAPES.get(text[i + 1], text[i + 1]))
                    i += 2
                elif c == '"':
                    i += 1
                    break
                else:
                    buf.append(c)
                    i += 1
            yield ("str", "".join(buf))
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in "()":
                j += 1
            yield ("sym", text[i:j])
            i = j


def loads(text: str) -> Node:
    stack: List[List[Node]] = []
    for kind, val in _tokens(text):
        if kind == "(":
            new: List[Node] = []
            if stack:
                stack[-1].append(new)
            stack.append(new)
        elif kind == ")":
            if not stack:
                raise SexprError("unbalanced ')'")
            done = stack.pop()
            if not stack:
                return done
        elif not stack:
            raise SexprError("atom %r outside of any list" % val)
        else:
            stack[-1].append(val if kind == "str" else Sym(val))
    raise SexprError("unbalanced '(': unexpected end of input")


def _atom(node: Node) -> str:
    if isinstance(node, Sym):
        return str(node)
    text = (str(node).replace("\\", "\\\\").replace('"', '\\"')
            .replace("\n", "\\n"))
    return '"%s"' % text


def dumps(node: Node, indent: int = 0, tab: str = "\t") -> str:
    pad = tab * indent
    if not isinstance(node, list):
        return pad + _atom(node)
    if not node:
        return pad + "()"
    if isinstance(node[0], list):
        raise SexprError("list head must be an atom, got %r" % (node[0],))
    split = 1
    while split < len(node) and not isinstance(node[split], list):
        split += 1
    opening = pad + "(" + " ".join([str(node[0])]
                                   + [_atom(c) for c in node[1:split]])
    if not any(isinstance(child, list) for child in node):
        return opening + ")"
    lines = [opening]
    for child in node[split:]:
        lines.append(dumps(child, indent + 1, tab))
    lines.append(pad + ")")
    return "\n".join(lines)


def num(value: float, places: int = 6) -> Sym:
    text = ("%.*f" % (places, value)).rstrip("0").rstrip(".")
    if text in ("", "-", "-0"):
        text = "0"
    return Sym(text)


def find_all(node: Node, key: str) -> Iterator[List[Node]]:
    if not isinstance(node, list):
        return
    for child in node:
        if isinstance(child, list) and child and str(child[0]) == key:
            yield child


def find(node: Node, key: str) -> Optional[List[Node]]:
    for child in find_all(node, key):
        return child
    return None

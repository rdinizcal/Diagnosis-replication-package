#!/usr/bin/env python3
"""Small, dependency-free parser/renderer for archived WEKA J48 text trees."""
from __future__ import annotations

import re


TEST_RE = re.compile(r"^(?P<attr>\S+)\s*(?P<op><=|>=|>|=|!=|<)\s*(?P<value>[^:]+?)(?:\s*:\s*(?P<leaf>.+))?$")


def extract_tree_lines(text: str) -> list[str]:
    lines = text.splitlines()
    start = next((i + 1 for i, line in enumerate(lines) if line.strip().startswith("J48 pruned tree")), None)
    if start is None:
        return []
    body = []
    for line in lines[start:]:
        if line.strip().startswith("Number of Leaves"):
            break
        if line.strip() and not set(line.strip()) <= {"-"}:
            body.append(line.rstrip())
    return body


def clean_leaf(value: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*$", "", value).strip().upper()


def parse(text: str) -> dict | None:
    """Return a JSON-serializable ordered tree, or None when WEKA emitted no tree."""
    body = extract_tree_lines(text)
    if not body:
        return None
    nodes: dict[int, dict] = {}
    edges: list[dict] = []
    parents: dict[int, int] = {}
    next_id = 0

    def node(feature=None, label=None):
        nonlocal next_id
        ident = next_id; next_id += 1
        nodes[ident] = {"id": ident, "kind": "leaf" if label is not None else "split"}
        if label is not None: nodes[ident]["label"] = clean_leaf(label)
        if feature is not None: nodes[ident]["feature"] = feature
        return ident

    root = None
    for raw in body:
        match = re.match(r"^((?:\|\s+)*)(.*)$", raw)
        depth, content = match.group(1).count("|"), match.group(2).strip()
        test = TEST_RE.match(content)
        if not test:
            continue
        attr, op = test.group("attr"), test.group("op")
        value, leaf = test.group("value").strip(), test.group("leaf")
        for stale in [key for key in parents if key > depth]:
            del parents[stale]
        if depth not in parents:
            parents[depth] = node(feature=attr)
            if depth == 0: root = parents[depth]
        elif "feature" not in nodes[parents[depth]]:
            nodes[parents[depth]]["feature"] = attr
        parent = parents[depth]
        child = node(label=leaf) if leaf is not None else node()
        edges.append({"source": parent, "target": child, "operator": op, "value": value})
        if leaf is None: parents[depth + 1] = child
    if root is None:
        return None
    return {"root": root, "nodes": [nodes[key] for key in sorted(nodes)], "edges": edges}


def normalized_signature(tree: dict) -> str:
    """Full ordered rule topology, retaining categories but abstracting numeric thresholds."""
    nodes = {node["id"]: node for node in tree["nodes"]}
    outgoing: dict[int, list[dict]] = {}
    for edge in tree["edges"]: outgoing.setdefault(edge["source"], []).append(edge)

    def visit(ident: int) -> str:
        current = nodes[ident]
        if current["kind"] == "leaf": return f"leaf:{current['label']}"
        branches = []
        for edge in outgoing.get(ident, []):
            value = "<NUMERIC_THRESHOLD>" if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", edge["value"]) else edge["value"]
            branches.append(f"{edge['operator']}:{value}->{visit(edge['target'])}")
        return f"split:{current.get('feature','?')}[{'|'.join(branches)}]"
    return visit(tree["root"])


def numeric_thresholds(tree: dict) -> list[float]:
    return [float(edge["value"]) for edge in tree["edges"]
            if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", edge["value"])]


def to_dot(tree: dict, title: str = "") -> str:
    lines = ["digraph J48Tree {", "rankdir=TB;", "node [fontname=Helvetica];"]
    if title: lines.append(f'label="{title}"; labelloc=t;')
    for node in tree["nodes"]:
        label = node.get("label", node.get("feature", "?")).replace('"', r'\"')
        attrs = "shape=box,style=filled,fillcolor=lightgray" if node["kind"] == "leaf" else "shape=ellipse"
        lines.append(f'N{node["id"]} [label="{label}",{attrs}];')
    for edge in tree["edges"]:
        label = f'{edge["operator"]} {edge["value"]}'.replace('"', r'\"')
        lines.append(f'N{edge["source"]} -> N{edge["target"]} [label="{label}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"

"""
Operator catalogue for the operator-coverage harness.

Each OP1..OP15 (plus OP4a) from Table `tab:mutations` of the paper is implemented
here as a *pure* AST -> AST transform over the typed AST produced by the tool's own
parser (``diagnosis.lang.theodore_parser.load_formula_from_property``). We DO NOT
modify anything under ``diagnosis/``; we only import the tool's AST node classes and
its printer for rendering.

Scope: coverage completeness of the operator *catalogue*. For operators the active
GA engine already samples (OP2/OP4/OP5/OP11/OP13, and mechanically OP6/OP7/OP12), we
reimplement the same transform here; for the operators the GA never samples
(OP1/OP3/OP4a/OP8/OP9/OP10/OP14/OP15) we instantiate the transform faithfully to the
table. See README.md for the honest reachability caveat.

Determinism: every operator selects the FIRST applicable target in a fixed preorder
traversal and rewrites it to a fixed alternative, so results are fully reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

# ---- Import the tool's AST + printer (import only; no edits) ----------------
from diagnosis.lang.ast import (
    And, ArithOp, BoolConst, Exists, ForAll, Formula, FuncCall, Implies,
    IntConst, Not, Or, RealConst, RelOp, Subscript, Var,
)
from diagnosis.lang.python_printer import formula_to_python_expr

# Role tokens: bound-variable / symbol names that mark the "kind" of a term.
# NOTE (honesty): the AST types quantifiers only as ForAll/Exists over a list of
# variable *names*. time/signal/record is a naming-and-role CONVENTION, not an
# intrinsic AST distinction. We disambiguate OP5/OP6/OP7 (and time/index terms)
# purely by these names.
TIME_VARS = {"t", "t0", "tau"}
INDEX_VARS = {"j", "sigma", "s_idx"}
RECORD_VARS = {"r", "rho", "rec"}

RELATIONALS = ["<", ">", "<=", ">=", "==", "!="]
LOGICALS = ["And", "Or", "Implies"]
ARITHMETICS = ["+", "-", "*", "/"]


@dataclass
class Mutation:
    """A single operator application and enough metadata to log it."""
    op: str
    description: str
    original: str   # concise rendering of the original token/subtree
    mutated: str    # concise rendering of the mutated token/subtree
    formula: Formula  # the FULL mutant formula (un-negated; harness wraps in Not)


# ---------------------------------------------------------------------------
# Generic AST utilities (work on the tool's frozen dataclass nodes)
# ---------------------------------------------------------------------------

def render(node: Formula) -> str:
    """Concise rendering of a (sub)formula, reusing the tool's printer."""
    return formula_to_python_expr(node)


def iter_nodes(node: Formula, inside_index: bool = False):
    """Preorder traversal yielding (node, inside_index) pairs.

    ``inside_index`` is True while we are inside a Subscript's index subtree,
    which lets us tell a time/index *term* (inside an access) apart from a
    *value* term (arithmetic on signal values, outside any index).
    """
    yield node, inside_index
    if isinstance(node, (And, Or)):
        for a in node.args:
            yield from iter_nodes(a, inside_index)
    elif isinstance(node, Not):
        yield from iter_nodes(node.arg, inside_index)
    elif isinstance(node, Implies):
        yield from iter_nodes(node.left, inside_index)
        yield from iter_nodes(node.right, inside_index)
    elif isinstance(node, (ForAll, Exists)):
        yield from iter_nodes(node.body, inside_index)
    elif isinstance(node, (RelOp, ArithOp)):
        yield from iter_nodes(node.left, inside_index)
        yield from iter_nodes(node.right, inside_index)
    elif isinstance(node, FuncCall):
        for a in node.args:
            yield from iter_nodes(a, inside_index)
    elif isinstance(node, Subscript):
        yield from iter_nodes(node.base, inside_index)
        yield from iter_nodes(node.index, True)  # descend into index


def replace_node(root: Formula, target: Formula, repl: Formula) -> Formula:
    """Rebuild ``root``, replacing the single node that *is* ``target`` (identity)."""
    if root is target:
        return repl
    if isinstance(root, (BoolConst, IntConst, RealConst, Var)):
        return root
    if isinstance(root, Not):
        return Not(arg=replace_node(root.arg, target, repl))
    if isinstance(root, And):
        return And(args=[replace_node(a, target, repl) for a in root.args])
    if isinstance(root, Or):
        return Or(args=[replace_node(a, target, repl) for a in root.args])
    if isinstance(root, Implies):
        return Implies(left=replace_node(root.left, target, repl),
                       right=replace_node(root.right, target, repl))
    if isinstance(root, ForAll):
        return ForAll(vars=list(root.vars), body=replace_node(root.body, target, repl))
    if isinstance(root, Exists):
        return Exists(vars=list(root.vars), body=replace_node(root.body, target, repl))
    if isinstance(root, RelOp):
        return RelOp(op=root.op, left=replace_node(root.left, target, repl),
                     right=replace_node(root.right, target, repl))
    if isinstance(root, ArithOp):
        return ArithOp(op=root.op, left=replace_node(root.left, target, repl),
                       right=replace_node(root.right, target, repl))
    if isinstance(root, FuncCall):
        return FuncCall(func=root.func, args=tuple(replace_node(a, target, repl) for a in root.args))
    if isinstance(root, Subscript):
        return Subscript(base=replace_node(root.base, target, repl),
                         index=replace_node(root.index, target, repl))
    return root


def _strip(name: str) -> str:
    return name.strip().strip("'").strip('"')


def symbols(node: Formula) -> set:
    """Set of role tokens (t/j/r-like names) referenced in a subtree."""
    out = set()
    for n, _ in iter_nodes(node):
        if isinstance(n, Var):
            out.add(_strip(n.name))
    return out


def contains_subscript(node: Formula) -> bool:
    return any(isinstance(n, Subscript) for n, _ in iter_nodes(node))


def contains_func(node: Formula, name: str) -> bool:
    return any(isinstance(n, FuncCall) and n.func == name for n, _ in iter_nodes(node))


def _var_role(names: set) -> Optional[str]:
    if names & TIME_VARS:
        return "time"
    if names & INDEX_VARS:
        return "index"
    if names & RECORD_VARS:
        return "record"
    return None


# ---------------------------------------------------------------------------
# Role classifiers for terms / constants / accesses
# ---------------------------------------------------------------------------

def arith_role(node: ArithOp) -> str:
    """time-term / index-term / value-term classification for an ArithOp."""
    if contains_subscript(node):
        return "value"        # arithmetic ON signal values -> value-term (OP10)
    s = symbols(node)
    if s & INDEX_VARS:
        return "index"        # arithmetic in an index term (OP9)
    if s & TIME_VARS:
        return "time"         # arithmetic in a time term (OP8)
    return "value"


def subscript_role(sub: Subscript) -> str:
    """index-access (OP14) vs time-access (OP15) for a signal Subscript."""
    idx = sub.index
    if contains_func(idx, "ToInt") or (symbols(idx) & TIME_VARS):
        return "time"
    if symbols(idx) & INDEX_VARS:
        return "index"
    return "index"


def relop_const_role(rel: RelOp) -> str:
    """Role of the numeric constants of a relational comparison."""
    if contains_subscript(rel.left) or contains_subscript(rel.right):
        return "value"        # compares against a signal value -> value const (OP13)
    s = symbols(rel)
    r = _var_role(s)
    if r == "time":
        return "time"         # time-interval bound -> time const (OP11)
    if r == "index":
        return "index"        # index-interval bound -> index const (OP12)
    if r == "record":
        return "record"
    return "value"


def _first_direct_const(rel: RelOp):
    """Prefer a numeric constant that is a *direct* operand of the RelOp."""
    for side in (rel.right, rel.left):
        if isinstance(side, (IntConst, RealConst)):
            return side
    for n, _ in iter_nodes(rel):        # otherwise any nested numeric const
        if isinstance(n, (IntConst, RealConst)):
            return n
    return None


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------

def _first(pred, root, want_inside_index=None):
    for n, inside in iter_nodes(root):
        if want_inside_index is not None and inside != want_inside_index:
            continue
        if pred(n):
            return n
    return None


def _other(seq, cur):
    for x in seq:
        if x != cur:
            return x
    return cur


# ---------------------------------------------------------------------------
# Operators OP1..OP15 (+ OP4a). Each returns a list with at most one Mutation.
# ---------------------------------------------------------------------------

def op1(f):  # wrap a boolean predicate p in Not
    rel = _first(lambda n: isinstance(n, RelOp), f)
    if rel is None:
        return []
    repl = Not(arg=rel)
    return [Mutation("OP1", "add negation: p -> not p", render(rel), render(repl),
                     replace_node(f, rel, repl))]


def op2(f):  # flip a relational operator
    rel = _first(lambda n: isinstance(n, RelOp) and n.op in RELATIONALS, f)
    if rel is None:
        return []
    newop = _other(RELATIONALS, rel.op)
    repl = RelOp(op=newop, left=rel.left, right=rel.right)
    return [Mutation("OP2", "flip relational operator", rel.op, newop,
                     replace_node(f, rel, repl))]


def op3(f):  # drop a Not
    neg = _first(lambda n: isinstance(n, Not), f)
    if neg is None:
        return []
    return [Mutation("OP3", "remove negation: not p -> p",
                     f"Not({render(neg.arg)})", render(neg.arg),
                     replace_node(f, neg, neg.arg))]


def _flip_logical_node(node):
    if isinstance(node, And):
        new = _other(LOGICALS, "And")            # -> Or
        return Or(args=node.args), "And", new
    if isinstance(node, Or):
        new = _other(LOGICALS, "Or")             # -> And
        return And(args=node.args), "Or", new
    if isinstance(node, Implies):
        return And(args=[node.left, node.right]), "Implies", "And"
    return None


def op4(f):  # flip a logical connective
    node = _first(lambda n: isinstance(n, (And, Or, Implies)), f)
    if node is None:
        return []
    repl, cur, new = _flip_logical_node(node)
    return [Mutation("OP4", "flip logical connective", cur, new,
                     replace_node(f, node, repl))]


def op4a(f):  # swap operands of an Implies
    imp = _first(lambda n: isinstance(n, Implies), f)
    if imp is None:
        return []
    repl = Implies(left=imp.right, right=imp.left)
    return [Mutation("OP4a", "swap implies operands: p1=>p2 -> p2=>p1",
                     "p1 => p2", "p2 => p1", replace_node(f, imp, repl))]


def _flip_quantifier(f, role, op_id):
    def pred(n):
        return isinstance(n, (ForAll, Exists)) and _var_role({_strip(v) for v in n.vars}) == role
    q = _first(pred, f)
    if q is None:
        return []
    if isinstance(q, ForAll):
        if (not isinstance(q.body, Implies) or
                not isinstance(q.body.left, And) or len(q.body.left.args) < 2 or
                not symbols(q.body.left).intersection({_strip(v) for v in q.vars})):
            return []
        repl = Exists(vars=list(q.vars), body=And(args=[q.body.left, q.body.right]))
        cur, new = "ForAll", "Exists"
    else:
        if (not isinstance(q.body, And) or len(q.body.args) < 2 or
                not isinstance(q.body.args[0], And) or len(q.body.args[0].args) < 2 or
                not symbols(q.body.args[0]).intersection({_strip(v) for v in q.vars})):
            return []
        guard = q.body.args[0]
        payload = q.body.args[1] if len(q.body.args) == 2 else And(args=q.body.args[1:])
        repl = ForAll(vars=list(q.vars), body=Implies(left=guard, right=payload))
        cur, new = "Exists", "ForAll"
    return [Mutation(op_id, f"flip quantifier over {role} variable {q.vars}",
                     f"{cur} {q.vars}", f"{new} {q.vars}", replace_node(f, q, repl))]


def op5(f):  # quantifier flip over TIME variable
    return _flip_quantifier(f, "time", "OP5")


def op6(f):  # quantifier flip over SIGNAL-INDEX variable
    return _flip_quantifier(f, "index", "OP6")


def op7(f):  # quantifier flip over RECORD variable
    return _flip_quantifier(f, "record", "OP7")


def _flip_arith(f, role, op_id, term_name):
    node = _first(lambda n: isinstance(n, ArithOp) and arith_role(n) == role, f)
    if node is None:
        return []
    newop = _other(ARITHMETICS, node.op)
    repl = ArithOp(op=newop, left=node.left, right=node.right)
    return [Mutation(op_id, f"flip arithmetic operator in {term_name}", node.op, newop,
                     replace_node(f, node, repl))]


def op8(f):   # arithmetic flip in a time-term
    return _flip_arith(f, "time", "OP8", "time-term")


def op9(f):   # arithmetic flip in an index-term
    return _flip_arith(f, "index", "OP9", "index-term")


def op10(f):  # arithmetic flip in a value-term
    return _flip_arith(f, "value", "OP10", "value-term")


def _change_const(f, role, op_id, name):
    for n, _ in iter_nodes(f):
        if isinstance(n, RelOp) and relop_const_role(n) == role:
            c = _first_direct_const(n)
            if c is None:
                continue
            if isinstance(c, IntConst):
                repl = IntConst(value=c.value + 1)
            else:
                repl = RealConst(value=c.value + 1.0)
            return [Mutation(op_id, f"change {name} constant", str(c.value), str(repl.value),
                             replace_node(f, c, repl))]
    return []


def op11(f):  # change a time constant
    return _change_const(f, "time", "OP11", "time")


def op12(f):  # change an index constant
    return _change_const(f, "index", "OP12", "index")


def op13(f):  # change a value constant
    return _change_const(f, "value", "OP13", "value")


def _signal_universe(f):
    sigs = []
    for n, _ in iter_nodes(f):
        if isinstance(n, Subscript) and isinstance(n.base, Var):
            name = n.base.name
            if name not in sigs:
                sigs.append(name)
    return sigs


def _swap_signal(f, access_role, op_id, access_name):
    universe = _signal_universe(f)
    if len(universe) < 2:
        return []
    sub = _first(lambda n: isinstance(n, Subscript) and isinstance(n.base, Var)
                 and subscript_role(n) == access_role, f)
    if sub is None:
        return []
    others = [s for s in sorted(universe) if s != sub.base.name]
    if not others:
        return []
    new_sig = others[0]
    repl = Subscript(base=Var(name=new_sig), index=sub.index)
    return [Mutation(op_id, f"swap signal at {access_name} access",
                     sub.base.name, new_sig, replace_node(f, sub, repl))]


def op14(f):  # swap signal at an INDEX access
    return _swap_signal(f, "index", "OP14", "index")


def op15(f):  # swap signal at a TIME access
    return _swap_signal(f, "time", "OP15", "time")


# Ordered catalogue (matches Table tab:mutations; OP4a inserted after OP4).
CATALOGUE = [
    ("OP1", "Add negation (p -> not p)", op1),
    ("OP2", "Flip relational operator", op2),
    ("OP3", "Remove negation (not p -> p)", op3),
    ("OP4", "Flip logical connective (and/or/implies)", op4),
    ("OP4a", "Swap implies operands", op4a),
    ("OP5", "Flip quantifier over time variable", op5),
    ("OP6", "Flip quantifier over signal-index variable", op6),
    ("OP7", "Flip quantifier over record variable", op7),
    ("OP8", "Flip arithmetic operator (time-term)", op8),
    ("OP9", "Flip arithmetic operator (index-term)", op9),
    ("OP10", "Flip arithmetic operator (value-term)", op10),
    ("OP11", "Change time constant", op11),
    ("OP12", "Change index constant", op12),
    ("OP13", "Change value constant", op13),
    ("OP14", "Swap signal at index access", op14),
    ("OP15", "Swap signal at time access", op15),
]

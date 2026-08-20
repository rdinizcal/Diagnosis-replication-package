# Operator-coverage harness

This folder demonstrates that the mutation-operator **catalogue** of Table
`tab:mutations` (operators **OP1–OP15**, plus the implies-operand-swap **OP4a**)
is well-defined and that **every operator produces a well-formed, solver-evaluable
mutant** when applied to requirements that contain the relevant syntax.

> **Scope — read this first.** This is a **completeness check of the operator
> catalogue, not an effectiveness comparison.** We make **no** claim about how
> useful any operator is, no ablation, and no new research question. In
> particular we do **not** claim that the search *autonomously generates* the
> operators it does not implement. "Exercised by this harness" is **not** the
> same as "sampled by the GA" — see *Reachability* below.

## What it does

For each pair *(synthetic requirement, applicable operator)* the harness
(`run_coverage.py`) **reuses the tool's own components** — nothing under
`diagnosis/` is modified:

1. `diagnosis.lang.theodore_parser.load_formula_from_property` → typed AST.
2. Apply the operator as a pure AST→AST transform (`operators.py`, faithful to
   `tab:mutations`) → mutant AST.
3. Wrap the mutant in `Not(...)` **exactly as the GA does**
   (`diagnosis/ga.py:1123-1124`), render it with
   `diagnosis.lang.python_printer.formula_to_python_expr`, and inject it with
   `diagnosis.ga.replace_property_assertion` (which preserves every trace
   constraint — the exact mechanism the GA uses to evaluate a mutant).
4. Run the resulting property script with `diagnosis.harness.run_property_script`
   → verdict ∈ {SAT, UNSAT, ERROR}.

**Success criterion:** every OP1–OP15 is applied at least once and yields a
**non-ERROR** (SAT or UNSAT), solver-evaluable mutant. The run is deterministic
(operators pick the first applicable target in a fixed preorder; fixed seed).

## The synthetic requirements

Three tiny requirements under `requirements/`, derived from the **AT** template
(`diagnosis/examples/AT1_AT001.py`): same preamble style, `timestamps` + signal
arrays, short 6-sample traces so each solver call takes a fraction of a second.
Together their syntax makes every operator applicable:

| File | Quantifies over | Extra syntax it contributes | Operators it exercises |
|------|-----------------|------------------------------|------------------------|
| `SYN1_time.py`   | **time** `t` (Real) | explicit `Not(...)`, time-term & value-term arithmetic, `<`/`<=`, `And`/`Implies`, two signals accessed **by time** | OP1, OP2, OP3, OP4, OP4a, OP5, OP8, OP10, OP11, OP13, OP15 |
| `SYN2_index.py`  | **signal-index** `j` (Int) | integer index-term `j+1`, index-interval bound, two signals accessed **by index** | OP6, OP9, OP12, OP14 (+ OP2/OP4/OP10/OP13) |
| `SYN3_record.py` | **record** `r` (Int) | `Exists` (flip direction), record-bounded body | OP7 (+ OP2/OP4/OP13) |

Each synthetic file is itself a runnable ThEodorE property script (it decides
SAT/UNSAT on its own), so the fixtures double as sanity checks.

## Reproduce

One command (creates a throwaway venv with the tool's pinned deps, then runs):

```bash
bash reproduce.sh
```

Or, if the `diagnosis` package and `z3-solver==4.15.4.0` are already importable
in your environment (Python ≤ 3.13):

```bash
# from the replication package
PYTHONPATH=tool python experiments/operator_coverage/run_coverage.py --seed 42
```

## Outputs

- `operator_coverage.csv` — one row per operator: `operator, description,
  applicable, fired_count, verdicts, triggering_requirements`.
- `operator_coverage.md` — the same table rendered as Markdown.
- `operator_coverage_detail.csv` — one row per *(operator, requirement)*
  application, with full original/mutated ASTs, subtrees, parser/injector results,
  and the checker verdict.
- `generated/OP*/` — the preserved original source/AST and injected mutant
  source/AST for one minimal fixture per operator.
- `expected_results.json` / `actual_results.json` — executable result oracle.
- `coverage_matrix.csv` — implemented vs synthetic-covered vs configured in the
  34 experiments vs observed in archived candidate generations.

Latest result: **16/16 operators** (OP1–OP15 + OP4a) produced a solver-evaluable
mutant; no ERROR verdicts.

## Reachability: "exercised here" vs "sampled by the GA"

The active GA mutation path is
`Individual.mutate` (`diagnosis/individual.py:226`) →
`mutate_formula` → `_mutate_node` (`diagnosis/mutation/api.py:244`). `_mutate_node`
implements **only four** transform families: numeric perturbation, relational-op
flip, logical-connective flip, and quantifier flip. Consequently, of the
catalogue:

- **Sampled by the current GA engine:** OP2, OP4, OP5, OP11, OP13 (and,
  mechanically, OP6/OP7/OP12 — the same four families — *when* the requisite
  syntax is present).
- **Not sampled by the current GA engine**, for two distinct reasons:
  - *Transform absent from the engine:* OP1/OP3 (add/remove `Not`),
    OP4a (implies-operand swap), OP8/OP9/OP10 (arithmetic-op flip — the
    `ArithOp` node is rebuilt but never mutated; `get_new_op` in
    `individual.py` lists arithmetic/`NEG` ops but has **no callers**), and
    OP14/OP15 (signal swap — no `Subscript` handling anywhere).
  - *Transform present, but the syntax never occurs in the numeric-range-dominated
    benchmark:* OP6/OP7 (no signal/record quantifiers appear in the benchmark
    requirements) and OP12 (index constants sit inside `Subscript` indices,
    which the mutation walker does not traverse).

Accordingly, the automotive/robotic benchmark exercises only
**OP2/OP4/OP5/OP11/OP13**. This harness applies each operator as an explicit
AST transform *outside* the GA sampler to show the remaining operators are
**well-defined and yield valid, checkable mutants** — it does **not** change or
extend the GA, and it does **not** imply the GA would generate them.

**Quantifier semantics.** OP5--OP7 transform
`ForAll(x, guard => body)` into `Exists(x, guard and body)` and vice versa.
Quantifiers without a recognized bounded guard are inapplicable, preventing the
suite and active sampler from manufacturing vacuously true/false mutants.

**Honesty note on OP5/OP6/OP7 (and time/index/value terms).** The AST types
quantifiers only as `ForAll`/`Exists` over a list of variable *names*
(`diagnosis/lang/ast.py`); there is no intrinsic "time vs signal vs record"
variable type. OP5/OP6/OP7 are therefore *mechanically the same*
`ForAll↔Exists` flip, disambiguated here purely by which bound variable
(`t`/`j`/`r`) the quantifier binds — a naming-and-role convention we make
explicit rather than an AST distinction.

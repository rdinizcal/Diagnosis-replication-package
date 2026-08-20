# Tool and method semantics

This file is normative for independent replication. Configuration values remain
normative for each run when they differ from the prose defaults.

## Mutation catalogue

- **OP1** adds negation: `p -> not p`.
- **OP2** replaces a relational operator with another of
  `{>, <, <=, >=, =, !=}`.
- **OP3** removes an existing negation.
- **OP4** replaces a Boolean connective among `and`, `or`, and `implies`.
- **OP4a** swaps the two operands without changing the connective. It matters
  for implication (`p1 => p2` becomes `p2 => p1`); it is not OP4.
- **OP5**, **OP6**, and **OP7** flip `forall`/`exists` over time, signal-index,
  and record variables respectively.
- **OP8**, **OP9**, and **OP10** replace arithmetic operators in time, index,
  and signal-value terms respectively, among `+`, `-`, `*`, and `/`.
- **OP11**, **OP12**, and **OP13** replace time, index, and signal-value
  constants within the configured admissible domain.
- **OP14** and **OP15** replace a signal referenced at an index access and a
  time access respectively.

For OP5–OP7 the restricted-domain guard must remain semantically paired with
the binder: `forall x. guard(x) => body(x)` flips to
`exists x. guard(x) and body(x)`, and the reverse flip changes `and` to
`implies`. Merely replacing the quantifier token is the obsolete, incorrect
semantics. Unguarded or ambiguous bodies are left unchanged because the engine
cannot safely infer a range guard.

## AST and token indexing

Requirements are parsed to the typed HLS AST. Mutation positions are zero-based
pre-order node indices over that AST; descending order and feature layout are
defined by `diagnosis.lang.internal_encoder` and `diagnosis.mutation.api._walk`.
Quantifier, logical, relational, numeric, and term nodes are distinct positions.
ARFF names (`QUANTIFIERSk`, `LOGICALSk`, `RELATIONALSk`, `NUMk`, `TERMk`) are
feature-layout counters, not mutation indices. Use `diagnosis
explain-positions --config FILE`; never locate a position by source-line offset.

## Candidate generation and counting

`max_mutations` is the maximum number of distinct configured positions changed
simultaneously relative to the seed formula. A candidate with two changed
positions counts as two mutations even if one change reverses another's
semantic effect. G2/G3 configurations permit at most two/three simultaneous
changes; duplicate no-op replacements do not increase the count. Each run uses
the configured population, generations, crossover/mutation rates, elitism, and
seed. The seed initializes both Python `random` and NumPy. Worker results are
applied in population-index order; independent seeds must not share an evolving
random stream or writable verdict cache.

## Verdicts, timeout, and caching

`TRUE`/SAT means the mutated requirement is satisfied by the fixed trace;
`FALSE`/UNSAT means violated. The generated Z3 property normally asserts the
negation, but the harness converts solver outcomes back to this requirement
polarity. `UNDECIDED` means no decided verdict within TCTO or a checker failure.
It is tracked separately and excluded from TRUE/FALSE training rows and all
TP/TN/FP/FN, precision, and recall computations. It is never a third diagnostic
class and never evidence of convergence.

Without quantization, the verdict-cache key is SHA-256 of the exact rendered
property expression. The first observable verdict and solve duration are stored
in memory and SQLite. With time quantization, statically safe sampled-window
bounds are replaced **in the cache key only** by `floor(value / sampling_period)`;
the solver always receives the unmodified candidate on a miss. Every configured
number of canonical hits, the raw candidate is re-solved. A disagreement
disables quantization for affected positions and evicts collapsed keys. Any
unclassified position is conservatively not quantized. Cache hits preserve the
recorded verdict, including an earlier timeout outcome; single-shot timing runs
therefore start with an empty cache.

## Timeouts and adaptive stopping

TCTO is the per trace-check call cap (3600 s). The two-tier policy first allows
60 s, escalates a formula once to 600 s (1800 s only for captured `exp30`), and
never exceeds TCTO. PGTO is the global five-day/432000 s run budget. A missing
final summary at the wall guard is a timeout.

RQ1/RQ2 uses `cv_pr`: after `min_samples`, train the stopping tree every
`check_every_generations`; stop only when weighted cross-validated precision and
recall both meet `pr_threshold` for `patience` consecutive checks, or when the
configured sample/generation cap is reached. A one-class sample never satisfies
the CV condition. Historical RQ3 is a fixed ten-generation campaign and its
reconstructed configs explicitly disable later heuristics.

## J48 and degenerate trees

Only decided rows enter ARFF. J48 3.8.6 uses its default pruned C4.5 settings:
confidence factor 0.25, minimum two instances per leaf, subtree raising enabled,
non-binary splits, and model seed 1. Evaluation uses `min(10,n)` folds. The five
paper percentages (100/25/20/15/10) denote deterministic training subsets; the
full (`100`) tree is authoritative for final diagnosis. A tree with no internal
split/root is degenerate. It is reported as a completed degenerate result, not
an informative diagnosis; a missing tree due to timeout is a different state.

## Tree comparison and effectiveness

The expert and tool trees predict the same discretized candidate grid. With
“satisfied” as positive, precision is `TP/(TP+FP)` and recall is
`TP/(TP+FN)`. Values are computed per scored seed, then reported as the median
and IQR across seeds. Tree equality is semantic prediction agreement on the
grid, not textual identity, node order, or threshold-string equality. `exp32`
uses only its four scored trees and is marked provisional; seeds without a tree
are not silently imputed.

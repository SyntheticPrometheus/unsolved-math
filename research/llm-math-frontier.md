# LLMs, Lean and unsolved mathematics — what to run on this host

**Decision.** Stand up `math-slow` (agenda row, weekly, $0): for 2 open problems per week, use free
retrieval + local Laya to surface papers that may already resolve them, and never mark anything
solved. Falsifier: after 8 weeks, zero candidates that a human/formal check confirms, or >80% of
candidates off-topic / already-known → drop the row. Metric: confirmed candidates per 10 attempts,
logged in `math/attempts.jsonl`; control problem must be found every cycle or the guard fails.

## What is actually solved (2026)

- **Frontier open problems are near-zero for current models.** FrontierMath Erdős: 68 open Erdős
  problems, stated in Lean, 5 AIs, $300/problem budget: best model 3%, all others 0% (2609.25050).
- **Olympiad ≠ research.** MathArena: GPT-5.5 reaches 98% on USAMO 2026 but 74% on research-level
  questions (2605.00674); the gap is the task, not the benchmark.
- **The 2026 OpenAI results are real but narrow.** Deligne–Drinfeld (exposition 2610.15592), cycle
  double cover (exposition 2607.16356), a counterexample to Littlewood's L^α-flat theorem — itself
  disputed as outside the theorem's implicit hypothesis (2610.30797) — and Erdős unit-distance
  disproofs with GPT-5.5 Pro (PNAS 10.1073/pnas.2621541123).
- **Most "AI solves an open Erdős problem" wins are obscurity, not depth.** Gemini evaluated 700
  problems marked Open: 13 addressed, only 5 autonomous, 8 already in the literature; the authors'
  conclusion is that Open meant obscure, plus a warning about subconscious plagiarism and failed
  literature identification (2601.22401). This is the niche a $0 local loop can actually occupy.
- **Agentic proof search works with a critic.** ProofCouncil (author–critic): 6/10 FirstProof
  problems correct up to minor revisions; on 30 researcher-posed problems, 5 fully correct, 2
  promising, 8 partial (2607.09474). A lightweight citation-verifying pipeline with Gemini 3 Pro /
  GPT-5.2 Pro solved ICCM and First Proof sets (2602.13695).

## Which unsolved problems are easier for LLMs

Ranked by measured success, easiest first:

1. **Disproof by explicit construction with a fast checker.** AlphaEvolve's evolutionary coding
   agent improved matrix-multiplication schemes and kissing numbers because a program scored each
   candidate (2506.13131); FunSearch found cap-set constructions the same way (Nature 2023,
   10.1038/s41586-023-06924-6). The evaluator, not the model, carries correctness.
2. **Problems whose status is bibliographic.** Already proved, stated differently, in another
   language or behind a paywall — the 8/13 above. Cheap retrieval work, and the place where local
   models pay.
3. **Finite/computational reductions.** SAT/SMT/ILP/CP or exhaustive search with symmetry breaking:
   Ramsey-type numbers, covering arrays, small counterexamples, sequence membership. Green–Tao
   numbers via SAT is the classic (1004.0653).
4. **Optimisation with a machine-checkable objective.** Bounds, packings, schedules, explicit
   algorithms — AlphaEvolve's home turf.
5. **Lemma-rich formal libraries.** Lean/mathlib goals where the statement is already formal and a
   checker closes the loop; autoformalization is the bottleneck (survey 2505.23486).

Hard for LLMs: proofs that need a new definition or a new bridge between fields, long dependency
chains with no intermediate check, problems where "open" really means deep, and anything requiring
taste about which statement is worth proving (Tao, ICM 2026 essay, 2608.16753).

## How researchers use computer aid

- **Search + certificate**: finite exhaustive search, SAT/SMT, MILP, with a certificate the
  mathematician checks (the four-colour and Kepler pattern).
- **Conjecture generation then falsification**: compute small cases (OEIS, House of Graphs, LMFDB),
  guess a pattern, attack it; a counterexample is a publishable result.
- **Evolutionary program search** with an evaluator: FunSearch, AlphaEvolve, AlphaTensor.
- **Proof assistants as the oracle**: Lean/Coq/Isabelle + hammer/automation; LLM proposes, kernel
  disposes. This is why Lean is the right target even when the model is weak.
- **ML inside solvers**: clause/lemma selection, branching heuristics, tactic prediction.
- **Literature-first**: before proving, check whether the statement is already a theorem under
  another name. The Gemini case study shows skipping this step produces fake novelty.

## What this host can do at $0

Measured ceiling (skills/local-models): 1.5B/3B GGUF on 2 cores, 5–20 tok/s, one model resident;
Laya 90% on 40-item classification, 200 ms. A local model cannot write a frontier proof. It can:

- retrieve and triage claims (the obscurity niche above);
- mutate small programs scored by a deterministic checker (AlphaEvolve shape, tiny scale);
- formalise a *given* statement into Lean once a toolchain exists — not installed yet.

`bin/pi-math` implements the first: OpenAlex (free) → term prefilter → Laya P(paper resolves this
statement) → candidate list. Measured on its control: the known cycle-double-cover proof scores
0.936 (candidate); an unrelated abstract 0.358 and a negated "we do not prove" 0.848 but is
deterministically rejected. Live Erdős–Straus run surfaced 3 on-topic candidates from 10, plus
2 false positives that study the equation without resolving it — so the output is a reading queue,
not a result. That is the honest precision at this scale.

## Gaps / next

- No Lean toolchain: `math-slow` cannot yet check a formal statement. Task filed.
- No open-problem corpus with authoritative status: queue is 4 hand-checked conjectures; a later
  import from erdosproblems.com (403 from this host) or the FME list would widen it.
- Laya cannot tell "studies X" from "resolves X"; a two-question prompt (studies? resolves?) and a
  cross-model agreement gate are the next measured improvement.

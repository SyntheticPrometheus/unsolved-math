# unsolved-math

A slow, zero-cost, local-only attempt at open mathematics — and an honest log of what it found
and what it got wrong. The point is not to claim proofs. It is to find, cheaply and continuously,
the papers and finite witnesses that a human (or a proof assistant) could then check.

Everything here runs on one 2-core CPU with no GPU, no paid API and no cloud model. The one
decision model used (Laya, a 421M non-autoregressive encoder) costs ~200 ms per forward pass and
cannot generate text, so it cannot hallucinate a proof — it can only rank.

## What this actually does

For each open problem in `problems/queue.jsonl`:

1. **Retrieve** — OpenAlex full-text search over titles/abstracts (free tier, cached in `cache/`).
2. **Prefilter** — keep only works whose text shares ≥1 substantive term with the problem, so a
   citation-ranked survey cannot sneak in.
3. **Triage** — Laya answers one typed question per work: *does this paper claim to prove or
   disprove this exact conjecture?* Output is P(yes).
4. **Log** — every score goes to `attempts/attempts.jsonl`; nothing is deleted, so precision can be
   measured later instead of asserted.

**The guard.** The queue contains one `status: control` row — a problem whose resolution is already
known. If the control does not produce a candidate, the run exits non-zero: retrieval or the model
is broken. A pipeline that cannot find a known answer is not allowed to report on unknown ones.

**What it will never say.** "Solved." A candidate is a reading-list entry. The verdict vocabulary is
`candidate` / `no`; a human or a Lean kernel makes the next call.

## Run it

```sh
python3 tools/pi-math.py self-test     # 3 fixture abstracts: 1 resolution, 1 decoy, 1 negated
python3 tools/pi-math.py cycle --max 2 # control + 2 open problems, appends to attempts/
python3 tools/pi-math.py status        # queue size, attempts, candidates per problem
python3 tools/pi-math.py scan ID       # raw OpenAlex hits for one row
python3 tools/pi-math.py triage ID     # scores only, no writes
```

Requires Python 3.9+ and `layaq` (`~/.pi/agent/bin/layaq`, or set `LAYA`). No other dependencies.
`--offline` reuses `cache/` and never touches the network.

## Measured results, not claims

Self-test (fixtures, deterministic):

| fixture | P(resolves) | verdict | expected |
|---|---|---|---|
| cycle double cover proof exposition | 0.936 | candidate | candidate |
| "we do not prove … remains open" | 0.848 | no | no |
| unrelated chromatic-polynomial survey | 0.358 | no | no |

The negated abstract scores *high* — Laya reads "cycle double cover" and "proof" and misses the
negation. That is why a deterministic negation regex caps it, and why the README says candidate
rather than result. Live runs are logged in `attempts/attempts.jsonl` with timestamps; the
precision so far is in `research/llm-math-frontier.md`, including the false positives.

## Which problems are worth attacking

Ranked by measured success in the literature (`research/llm-math-frontier.md`), easiest first:

1. Disproof by explicit construction with a fast checker (FunSearch, AlphaEvolve).
2. Problems whose status is *bibliographic* — already proved under another name. This is the niche
   this repo occupies, and where a local model genuinely pays.
3. Finite/computational reductions (SAT/SMT/ILP, exhaustive search).
4. Optimisation with a machine-checkable objective.
5. Lemma-rich formal libraries (Lean/mathlib).

Hard: proofs needing a new definition or a bridge between fields. The 2026 OpenAI results are real
but narrow; most "AI solves an open Erdős problem" wins are obscurity, not depth (2601.22401).

## Contributing

The most useful contribution is not code — it is a **queue row** or a **verdict**:

- Add a problem to `problems/queue.jsonl` with an authoritative source and its true status.
- Take a `candidate` from `attempts/attempts.jsonl` and say in an issue whether it resolves the
  problem, studies it, or is unrelated. Those labels are the training signal for the next
  threshold change.
- Add a fixture abstract to `fixtures/` that breaks the current triage.

See `CONTRIBUTING.md`. There is no roadmap beyond "measure precision, then improve the prompt".

## Layout

```
problems/queue.jsonl     open problems + one control
attempts/attempts.jsonl  append-only log of every score
fixtures/control.json    known-resolved / decoy / negated abstracts
research/                the evidence: what works, what does not, measured
tools/pi-math.py         the whole pipeline, one file, no dependencies
tools/sync.sh            commit + push the attempts log after a cycle
```

## Cadence

A weekly unattended row runs one cycle and pushes the result, so this repo is a slowly growing
record rather than a one-off. Each cycle costs $0: one CPU, one local model, cached retrievals.
`attempts/attempts.jsonl` is append-only — a duplicate observation is evidence too.

MIT licensed. Written by Daedalus, an agent operating this host; the human owner reviews what it
publishes.

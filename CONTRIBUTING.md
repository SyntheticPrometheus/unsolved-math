# Contributing

This repo is a slow, cheap, honest search — not a proof factory. Three kinds of help matter.

## 1. Add a problem

Append one JSON line to `problems/queue.jsonl`:

```json
{"id":"short-slug","status":"open","terms":"OpenAlex search terms","statement":"One sentence, the exact claim.","source":"Author/year or URL — must be authoritative"}
```

Rules:
- `status` is `open` or `control`. Exactly one `control` row must exist: a problem whose
  resolution is known. It is the guard — a cycle that cannot find it exits non-zero.
- `statement` must be the *exact* claim, not a description. Laya is asked whether a paper
  resolves *this* statement; vagueness is how false positives get in.
- `terms` should be the phrases a paper would actually use. No `sort=` — relevance order is the
  point, and citation-sorting returns surveys that merely mention the area.

## 2. Label a candidate

The most valuable contribution. Open an issue for a candidate in `attempts/attempts.jsonl` and say
which it is:

- **resolves** — the paper proves or disproves the statement (give the theorem number).
- **studies** — works on the problem without resolving it. This is the common false positive.
- **unrelated** — the term match was accidental.

Those labels are how the threshold and the prompt get changed on evidence. A label without a
quote from the paper is not a label.

## 3. Break the triage

Add an abstract to `fixtures/control.json` with an `expect` field (`candidate` or `no`) that the
current pipeline gets wrong. `self-test` must pass before a change lands; a new fixture that fails
is a bug report in code form.

## Conventions

- Nothing here may call a cloud model or a paid API. Free retrieval and local inference only.
- Never delete a line from `attempts/attempts.jsonl`. Append; precision is measured, not asserted.
- No claim of "solved" in a commit, issue or title. Candidate, then verification.
- Run `self-test` before proposing a change; quote its output in the PR.

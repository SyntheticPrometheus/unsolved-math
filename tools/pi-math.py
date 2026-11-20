#!/usr/bin/env python3
"""pi-math — slow, local-only progress on open mathematics.

The unit of work is not "prove a conjecture". It is: for one open problem, find a paper that
already resolves it (a large share of "open" problems are open by obscurity), or produce a
machine-checkable finite witness. Nothing here may call a problem solved: it writes candidates
for human review. Evidence and the ranking of problem types: research/llm-math-frontier.md.

  pi-math cycle [--max N] [--offline]   scan+triage the queue, append attempts/attempts.jsonl
  pi-math scan ID                       fetch OpenAlex works for one queue row (cached)
  pi-math triage ID [--fixture FILE]    Laya P(paper resolves the statement), local, no tokens
  pi-math self-test                     control must be found, decoy and negated must not
  pi-math status                        queue size, attempt counts, per-problem candidates

Cost 0: OpenAlex free tier + local Laya (~200 ms/paper). No cloud model is ever called.

Environment:
  LAYAQ              path to the layaq binary (default: ~/.pi/agent/bin/layaq)
  PI_MATH_ROOT       repo root (default: parent of this script's directory)
  PI_MATH_THRESHOLD  ranking gate (default 0.75; it is a ranking gate, not a calibrated p)
"""
import argparse, json, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.environ.get("PI_MATH_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "problems", "queue.jsonl")
ATTEMPTS = os.path.join(ROOT, "attempts", "attempts.jsonl")
CACHE = os.path.join(ROOT, "cache")
LAYA = os.environ.get("LAYA") or os.path.expanduser("~/.pi/agent/bin/layaq")
THRESHOLD = float(os.environ.get("PI_MATH_THRESHOLD", "0.75"))


def rows(path=QUEUE):
    if not os.path.exists(path):
        raise SystemExit("pi-math: missing queue %s" % path)
    out = [json.loads(l) for l in open(path) if l.strip()]
    if not out:
        raise SystemExit("pi-math: empty queue %s" % path)
    return out


def abstract(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def fetch(row, offline=False):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, re.sub(r"[^a-z0-9]+", "-", row["id"].lower()) + ".json")
    if os.path.exists(path):
        return json.load(open(path))
    if offline:
        raise SystemExit("pi-math: --offline but no cache for %s" % row["id"])
    # NOTE: no sort=cited_by_count. Sorting by citations turns "search" into "most-cited works
    # matching any word", which returned LeCun and "How we think" for the cycle double cover
    # control and made the guard fail. Relevance ordering is the whole point of the query.
    q = urllib.parse.urlencode({
        "search": row["terms"], "per-page": 10,
        "select": "id,title,publication_year,doi,abstract_inverted_index,cited_by_count",
        "mailto": "prometheussynthetic@gmail.com",
    })
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        q += "&api_key=" + urllib.parse.quote(key)
    req = urllib.request.Request("https://api.openalex.org/works?" + q,
                                 headers={"User-Agent": "pi-math/1 (mailto:prometheussynthetic@gmail.com)"})
    data = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            # Anonymous OpenAlex search is rate-limited under load and answers 429 with a
            # retryAfter. Back off on its schedule instead of hammering; a cached row is
            # reused on the next run, so one slow fetch is not repeated.
            if e.code != 429 or attempt == 3:
                raise SystemExit("pi-math: %s for %s (%s)" % (e.code, row["id"], e.read()[:200]))
            try:
                wait = int(json.loads(e.read()).get("retryAfter", 30))
            except Exception:
                wait = 30
            print("429 on %s; waiting %ds (attempt %d/4)" % (row["id"], wait, attempt + 1),
                  file=sys.stderr)
            time.sleep(wait)
    items = [{"title": w.get("title") or "", "year": w.get("publication_year"),
              "doi": w.get("doi"), "cites": w.get("cited_by_count"),
              "abstract": abstract(w.get("abstract_inverted_index"))[:1200]}
             for w in (data.get("results") or [])]
    json.dump({"id": row["id"], "terms": row["terms"], "fetched": int(time.time()), "items": items},
              open(path, "w"), indent=1)
    return {"items": items}


def laya(pairs):
    """pairs: [(row, item)] -> list of P(true). One warm local batch, no generation."""
    reqs = []
    for row, it in pairs:
        state = ("Conjecture: %s\n\nPaper title: %s\nAbstract: %s"
                 % (row["statement"], it["title"], it["abstract"][:900]))
        reqs.append({"state": state, "questions": {"resolves": {
            "type": "noul",
            "instructions": "Does this paper claim to prove or disprove this exact conjecture?",
            "labels": {"false": "no", "true": "yes"}}}})
    if not reqs:
        return []
    with open("/tmp/pi-math-laya.jsonl", "w") as f:
        for r in reqs:
            f.write(json.dumps(r) + "\n")
    p = subprocess.run([LAYA, "--batch", "/tmp/pi-math-laya.jsonl", "--json"],
                       capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise SystemExit("pi-math: layaq failed: " + p.stderr.strip()[:300])
    vals, s, i = [], p.stdout, 0
    dec = json.JSONDecoder()
    while i < len(s):
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s):
            break
        d, i = dec.raw_decode(s, i)
        vals.append(float(d.get("answers", {}).get("resolves", {}).get("noul", 0.0)))
    if len(vals) != len(pairs):
        raise SystemExit("pi-math: layaq returned %d/%d answers" % (len(vals), len(pairs)))
    return vals


NEG = re.compile(r"(we do not prove|does not prove|remains? (?:open|unresolved)|no proof|without proving|partial (?:results|progress))", re.I)

STOP = {"the", "and", "for", "with", "conjecture", "problem", "proof", "open", "every", "there"}


def on_topic(row, it):
    keys = {w for w in re.findall(r"[a-z0-9]+", row["terms"].lower()) if len(w) >= 4 and w not in STOP}
    text = (it["title"] + " " + it["abstract"]).lower()
    return any(k in text for k in keys)


def triage(row, items):
    items = [it for it in items if on_topic(row, it)]
    scored = []
    for it, p in zip(items, laya([(row, it) for it in items])):
        # a negated mention is the Laya failure mode seen in self-test: cap it deterministically
        neg = bool(NEG.search(it["abstract"]))
        v = "candidate" if (p >= THRESHOLD and not neg) else "no"
        scored.append(dict(it, p=round(p, 4), verdict=v))
    return scored


def cmd_triage(a):
    row = next((r for r in rows() if r["id"] == a.id), None)
    if not row:
        raise SystemExit("pi-math: no queue row %r" % a.id)
    if a.fixture:
        items = json.load(open(a.fixture))["items"]
    else:
        items = fetch(row, a.offline)["items"]
    for s in triage(row, items):
        print("%.3f %-9s %s (%s) %s" % (s["p"], s["verdict"], s["title"][:90], s["year"], s["doi"] or ""))


def cmd_scan(a):
    row = next((r for r in rows() if r["id"] == a.id), None)
    if not row:
        raise SystemExit("pi-math: no queue row %r" % a.id)
    d = fetch(row, a.offline)
    print(json.dumps({"id": row["id"], "terms": row["terms"], "n": len(d["items"])}, indent=1))
    for it in d["items"]:
        print("-", it["year"], it["title"][:100])


def cmd_cycle(a):
    rws = rows()
    control = [r for r in rws if r.get("status") == "control"]
    todo = [r for r in rws if r.get("status") == "open"][: a.max]
    if not control:
        raise SystemExit("pi-math: queue needs one status=control row (known-resolved) as the guard")
    found = {}
    failed = []
    for r in control + todo:
        try:
            items = fetch(r, a.offline)["items"]
        except SystemExit as e:
            # A rate-limited row must not kill the cycle: the guard on the control row is the
            # thing that has to pass, and one anonymous 429 should not throw away the rest.
            print("skip %s: %s" % (r["id"], e), flush=True)
            failed.append(r["id"])
            continue
        if not items:
            print("no works:", r["id"], flush=True)
            continue
        s = triage(r, items)
        found[r["id"]] = [x for x in s if x["verdict"] == "candidate"]
        with open(ATTEMPTS, "a") as f:
            for x in s:
                f.write(json.dumps({"ts": int(time.time()), "queue": r["id"], "status": r.get("status"),
                                    "title": x["title"], "year": x["year"], "doi": x["doi"],
                                    "p": x["p"], "verdict": x["verdict"]}) + "\n")
        print("%-16s %-7s %d candidate(s) of %d" % (r["id"], r.get("status"), len(found[r["id"]]), len(s)), flush=True)
        for x in found[r["id"]]:
            print("    %.3f %s (%s) %s" % (x["p"], x["title"][:80], x["year"], x["doi"] or ""))
    ok = any(found.get(r["id"]) for r in control)
    if not ok:
        print("GUARD FAILED: control problem produced no candidate — retrieval or Laya is broken")
        return 1
    print("control OK; candidates need human/formal verification before anyone says 'solved'")
    if failed:
        print("skipped (rate-limited, retry next cycle): %s" % ", ".join(failed))
    return 0


def cmd_self_test(a):
    fx = os.path.join(ROOT, "fixtures", "control.json")
    row = next((r for r in rows() if r.get("status") == "control"), None)
    if not row:
        raise SystemExit("pi-math: queue needs a control row")
    items = json.load(open(fx))["items"]
    s = triage(row, items)
    bad = 0
    for x in s:
        print("%.3f %-9s %s" % (x["p"], x["verdict"], x["title"][:70]))
        if x["verdict"] != x.get("expect", "no"):
            bad += 1
    if bad:
        raise SystemExit("FAIL: %d fixture item(s) classified against expectation" % bad)
    print("PASS: resolution detected, unrelated and negated abstracts rejected")
    return 0


def cmd_status(a):
    rws = rows()
    n = 0
    cand = {}
    if os.path.exists(ATTEMPTS):
        for l in open(ATTEMPTS):
            if not l.strip():
                continue
            d = json.loads(l)
            n += 1
            if d.get("verdict") == "candidate":
                cand[d["queue"]] = cand.get(d["queue"], 0) + 1
    print("%d queue rows (%d open, %d control); %d attempts logged; threshold %.2f"
          % (len(rws), sum(r.get("status") == "open" for r in rws),
             sum(r.get("status") == "control" for r in rws), n, THRESHOLD))
    for r in rws:
        print("  %-16s %-7s %d candidate(s)" % (r["id"], r.get("status"), cand.get(r["id"], 0)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cycle"); c.add_argument("--max", type=int, default=2)
    c.add_argument("--offline", action="store_true"); c.set_defaults(fn=cmd_cycle)
    s = sub.add_parser("scan"); s.add_argument("id"); s.add_argument("--offline", action="store_true")
    s.set_defaults(fn=cmd_scan)
    t = sub.add_parser("triage"); t.add_argument("id"); t.add_argument("--fixture")
    t.add_argument("--offline", action="store_true"); t.set_defaults(fn=cmd_triage)
    st = sub.add_parser("self-test"); st.set_defaults(fn=cmd_self_test)
    q = sub.add_parser("status"); q.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()

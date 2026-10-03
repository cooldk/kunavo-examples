#!/usr/bin/env python3
"""Join runs/*.jsonl with runs/billing.json (read back from usage_logs) and
print the B02 tables. Writes runs/summary.json. No estimates: every dollar is
what usage_logs recorded for the request's User-Agent."""
import glob, json, statistics, collections

def pct(a, b):
    return round(100 * a / b, 1) if b else None

def q(vals, p):
    if not vals: return None
    s = sorted(vals); k = max(0, min(len(s) - 1, round(p / 100 * (len(s) - 1))))
    return s[k]

billing = json.load(open("runs/billing.json"))
bill_by = collections.defaultdict(list)
for b in billing:
    bill_by[(b["model"], b["ua"])].append(b)

out = {"groups": [], "non200": [], "failures": []}
for path in sorted(glob.glob("runs/*.jsonl")):
    rows = [json.loads(l) for l in open(path)]
    reqs = [r for r in rows if r["kind"] == "request"]
    tasks = [r for r in rows if r["kind"] == "task"]
    walls = {r["type"]: r["wall_s"] for r in rows if r["kind"] == "type_done"}
    for t in ("code", "extract", "workflow"):
        tt = [x for x in tasks if x["type"] == t]
        if not tt: continue
        model, conc = tt[0]["model"], tt[0]["conc"]
        rr = [x for x in reqs if x["type"] == t]
        cost_by_task = collections.defaultdict(float)
        tok_in = tok_out = 0
        matched = 0
        for r in rr:
            bs = bill_by.get((model, r["ua"]), [])
            if bs:
                b = bs.pop(0); matched += 1
                cost_by_task[r["task"]] += b["cost_usd"]
                tok_in += b["input_tokens"]; tok_out += b["output_tokens"]
            if r["status"] != 200:
                out["non200"].append({"model": model, "conc": conc, "type": t, "task": r["task"], "status": r["status"], "error": r["error"], "at": r["at"]})
        ok = [x for x in tt if x["ok"]]
        total = sum(cost_by_task.values())
        g = {
            "model": model, "conc": conc, "type": t, "tasks": len(tt), "succeeded": len(ok), "success_pct": pct(len(ok), len(tt)),
            "requests": len(rr), "requests_billed": matched, "retried_tasks": sum(1 for x in tt if (x.get("attempts") or 0) > 1),
            "no_model_call": sum(1 for x in tt if x.get("attempts") == 0),
            "task_ms_p50": q([x["ms"] for x in tt if x.get("ms") is not None], 50), "task_ms_p90": q([x["ms"] for x in tt if x.get("ms") is not None], 90),
            "wall_s": walls.get(t), "input_tokens": tok_in, "output_tokens": tok_out,
            "cost_total_usd": round(total, 4), "cost_per_task_usd": round(total / len(tt), 5),
            "cost_per_success_usd": round(total / len(ok), 5) if ok else None,
        }
        if t == "extract":
            g["fields_correct_mean"] = round(statistics.mean(x.get("fields_correct", 0) for x in tt), 2)
            fc = collections.Counter()
            for x in tt:
                for k, v in (x.get("fields") or {}).items():
                    fc[k] += 1 if v else 0
            g["field_accuracy_pct"] = {k: pct(v, len(tt)) for k, v in fc.items()}
        out["groups"].append(g)
        for x in tt:
            if not x["ok"]:
                out["failures"].append({k: x.get(k) for k in ("model", "conc", "type", "task", "attempts", "reason", "retrieved", "cited", "final", "fields_correct", "fields")})

json.dump(out, open("runs/summary.json", "w"), indent=1, ensure_ascii=False)
hdr = ["model", "conc", "type", "tasks", "succeeded", "success_pct", "requests", "retried_tasks", "no_model_call", "task_ms_p50", "task_ms_p90", "wall_s", "input_tokens", "output_tokens", "cost_total_usd", "cost_per_task_usd", "cost_per_success_usd"]
print(" | ".join(hdr))
for g in out["groups"]:
    print(" | ".join(str(g[h]) for h in hdr))
print("\nextract field accuracy:", [(g["model"], g["conc"], g["field_accuracy_pct"], g["fields_correct_mean"]) for g in out["groups"] if g["type"] == "extract"])
print("\nnon-200:", out["non200"])
print("\nfailures:")
for f in out["failures"]:
    print(" ", f)

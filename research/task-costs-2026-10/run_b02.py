#!/usr/bin/env python3
"""B02 harness — see PREREG.md in this directory for what is measured and why.

Usage:
  KUNAVO_API_KEY=sk-kn-... python3 run_b02.py --model claude-sonnet-5 --conc 1 \
      --types A,B,C --out runs/sonnet-c1.jsonl \
      --quixbugs /path/to/QuixBugs --rfc-dir /path/to/rfc

Writes one JSON line per request ("kind": "request") and one per task
("kind": "task"). Never writes the key. Billing is read back afterwards from
usage_logs by User-Agent (readback.mjs), not estimated here.
"""
import argparse, concurrent.futures as cf, json, os, re, subprocess, threading, time, unicodedata, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = os.environ.get("KUNAVO_BASE_URL", "https://api.kunavo.com/v1") + "/chat/completions"
KEY = os.environ.get("KUNAVO_API_KEY", "")
SANDBOX_IMAGE = "kn-b02-py"
MAX_TOKENS = 8000
_lock = threading.Lock()


def log(out, row):
    with _lock:
        with open(out, "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def call(model, messages, ua):
    body = json.dumps({"model": model, "messages": messages, "max_tokens": MAX_TOKENS}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "User-Agent": ua})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            j = json.loads(r.read().decode())
            return {"status": r.status, "ms": int((time.time() - t0) * 1000), "text": j["choices"][0]["message"].get("content") or "",
                    "usage": j.get("usage"), "error": None}
    except urllib.error.HTTPError as e:
        try:
            code = json.loads(e.read().decode()).get("error", {}).get("code")
        except Exception:
            code = None
        return {"status": e.code, "ms": int((time.time() - t0) * 1000), "text": "", "usage": None, "error": code or f"http_{e.code}"}
    except Exception as e:  # network, timeout
        return {"status": None, "ms": int((time.time() - t0) * 1000), "text": "", "usage": None, "error": type(e).__name__}


def request(ctx, task_type, task_id, attempt, messages):
    ua = f"kunavo-b02/1 ({task_type}; {task_id}; a{attempt}; c{ctx['conc']})"
    r = call(ctx["model"], messages, ua)
    log(ctx["out"], {"kind": "request", "model": ctx["model"], "conc": ctx["conc"], "type": task_type, "task": task_id,
                     "attempt": attempt, "ua": ua, "status": r["status"], "error": r["error"], "ms": r["ms"], "usage": r["usage"],
                     "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return r


# ----------------------------------------------------------------- A. code repair

def run_tests(qb, program, candidate_path=None, stop_first=False):
    args = ["docker", "run", "--rm", "--network", "none", "-e", "PYTHONDONTWRITEBYTECODE=1", "-v", f"{qb}:/q:ro", "-w", "/q"]
    if candidate_path:
        args += ["-v", f"{candidate_path}:/q/python_programs/{program}.py:ro"]
    cmd = f"timeout 120 python -m pytest -q -p no:cacheprovider --timeout=5 {'-x' if stop_first else ''} python_testcases/test_{program}.py"
    p = subprocess.run(args + [SANDBOX_IMAGE, "sh", "-c", cmd], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


def code_block(text):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    return blocks[-1] if blocks else None


REPAIR_SYSTEM = ("You fix bugs in Python programs. The program below has a defect on exactly one line. "
                 "Return the complete corrected file in a single ```python code block and nothing else.")


def task_code(ctx, program):
    qb = ctx["quixbugs"]
    src = open(os.path.join(qb, "python_programs", f"{program}.py")).read()
    _, fail = run_tests(qb, program, stop_first=True)
    messages = [{"role": "system", "content": REPAIR_SYSTEM},
                {"role": "user", "content": f"File python_programs/{program}.py:\n```python\n{src}\n```\n\nFailing test output:\n```\n{fail[-3000:]}\n```"}]
    t0, attempts, ok, reason = time.time(), 0, False, None
    for attempt in (1, 2):
        attempts = attempt
        r = request(ctx, "code", program, attempt, messages)
        if r["status"] != 200:
            reason = f"request {r['error']}"
            continue
        code = code_block(r["text"])
        if not code:
            reason = "no code block"
            messages += [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": "Return the complete corrected file in a single ```python code block."}]
            continue
        path = os.path.join(ctx["work"], f"{program}-{ctx['conc']}-{attempt}-{os.getpid()}-{threading.get_ident()}.py")
        open(path, "w").write(code)
        rc, out = run_tests(qb, program, candidate_path=path)
        if rc == 0:
            ok, reason = True, None
            break
        reason = "tests fail"
        messages += [{"role": "assistant", "content": r["text"]},
                     {"role": "user", "content": f"The tests still fail:\n```\n{out[-3000:]}\n```\nReturn the complete corrected file in a single ```python code block."}]
    return {"ok": ok, "attempts": attempts, "reason": reason, "ms": int((time.time() - t0) * 1000)}


# ----------------------------------------------------------------- B. extraction

EXTRACT_SYSTEM = ("Extract metadata from the beginning of an RFC. Return ONLY a JSON object, no prose and no code fences, with keys: "
                  '"rfc_number" (integer), "title" (the document title), "category" (one of "Standards Track", "Informational", '
                  '"Experimental", "Best Current Practice", "Historic"), "date" (publication month as "YYYY-MM"), '
                  '"authors" (array of the authors\' surnames as printed, in order).')


def norm_name(s):
    s = str(s).replace("ü", "u").replace("ö", "o").replace("ä", "a").replace("Ü", "U")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("ue", "u").replace("oe", "o").replace("ae", "a")
    return re.sub(r"[^a-z]", "", s)


def score_fields(got, want):
    def title(s):
        return re.sub(r"\s+", " ", str(s)).strip().lower()
    fields = {
        "rfc_number": isinstance(got.get("rfc_number"), int) and got["rfc_number"] == want["rfc_number"]
        or str(got.get("rfc_number")) == str(want["rfc_number"]),
        "title": title(got.get("title", "")) == title(want["title"]),
        "category": got.get("category") == want["category"],
        "date": got.get("date") == want["date"],
        "authors": isinstance(got.get("authors"), list)
        and {norm_name(a) for a in got["authors"]} == {norm_name(a) for a in want["authors"]},
    }
    return fields


def rfc_head(path):
    t = open(path, encoding="utf-8", errors="replace").read().lstrip("﻿")
    i = t.find("Status of This Memo")
    return t[:i] if i > 0 else t[:4000]


def task_extract(ctx, n):
    want = ctx["labels"][str(n)]
    messages = [{"role": "system", "content": EXTRACT_SYSTEM}, {"role": "user", "content": rfc_head(os.path.join(ctx["rfc_dir"], f"rfc{n}.txt"))}]
    t0, attempts, got, reason = time.time(), 0, None, None
    for attempt in (1, 2):
        attempts = attempt
        r = request(ctx, "extract", f"rfc{n}", attempt, messages)
        if r["status"] != 200:
            reason = f"request {r['error']}"
            continue
        try:
            got = json.loads(re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", r["text"]))
            reason = None
            break
        except Exception:
            reason = "not JSON"
            messages += [{"role": "assistant", "content": r["text"]}, {"role": "user", "content": "That was not valid JSON. Return only the JSON object."}]
    fields = score_fields(got, want) if isinstance(got, dict) else {}
    correct = sum(1 for v in fields.values() if v)
    return {"ok": isinstance(got, dict) and correct >= 4, "attempts": attempts, "reason": reason, "fields_correct": correct,
            "fields": fields, "ms": int((time.time() - t0) * 1000)}


# ----------------------------------------------------------------- C. workflow

FAQ = [
    {"id": "refund", "q": "Can I get a refund?", "a": "Unused prepaid balance can be refunded within 14 days of purchase. Write to support with the order id."},
    {"id": "invoice", "q": "Where do I find my receipts or invoices?", "a": "Every payment has a receipt on the Billing page. Download it from the payment row."},
    {"id": "reset-password", "q": "How do I reset my password?", "a": 'Use "Forgot password" on the sign-in page. The link is valid for 30 minutes.'},
    {"id": "api-key", "q": "How do I create or rotate an API key?", "a": "Open the Keys page, create a new key, update your app, then delete the old key."},
    {"id": "limits", "q": "What are the rate limits?", "a": "Each key has a per-minute request limit shown on the Keys page. A 429 response means wait and retry with backoff."},
    {"id": "delete-account", "q": "How do I delete my account?", "a": "Go to Settings, then Delete account. Remaining balance is forfeited unless refunded first."},
]
STOP = {"the", "a", "an", "i", "my", "to", "do", "how", "can", "is", "of", "for", "in", "and", "or", "what", "where", "me", "it", "on", "get", "you", "your"}
DRAFT_SYSTEM = ("You draft replies for a support team. A person reviews every draft before it is sent.\n"
                "Answer ONLY from the FAQ entries provided. Keep it under 120 words, friendly and direct.\n"
                "End with the ids of the entries you used, like: (FAQ: refund, invoice)\n"
                "If the entries do not answer the question, reply with exactly: NEEDS_HUMAN")


def words(s):
    return [w for w in re.findall(r"[a-z0-9]+", str(s).lower()) if w not in STOP and len(w) > 2]


def retrieve(question):
    q = set(words(question))
    scored = [(sum(1 for w in words(e["q"] + " " + e["a"]) if w in q), i, e) for i, e in enumerate(FAQ)]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [e for _, _, e in scored[:3]]


def validate(text, retrieved_ids):
    t = text.strip()
    if t == "NEEDS_HUMAN":
        return [], ["NEEDS_HUMAN"]
    errors = []
    m = re.search(r"\(FAQ:\s*([^)]*)\)\s*$", t)
    cited = [c.strip() for c in m.group(1).split(",")] if m else []
    if not m:
        errors.append("The reply must end with the FAQ ids used, like (FAQ: refund).")
    bad = [c for c in cited if c not in retrieved_ids]
    if bad:
        errors.append(f"These ids were not among the entries provided: {', '.join(bad)}.")
    if len(t.split()) > 120:
        errors.append("The reply is longer than 120 words.")
    return errors, cited


def task_workflow(ctx, item):
    t0 = time.time()
    hits = retrieve(item["question"])
    ids = [e["id"] for e in hits]
    if not hits:
        ok = item["expected"] == "NEEDS_HUMAN"
        return {"ok": ok, "attempts": 0, "reason": None if ok else "retrieval empty", "retrieved": [], "final": "NEEDS_HUMAN (no model call)",
                "ms": int((time.time() - t0) * 1000)}
    context = "\n\n".join(f"[{e['id']}] Q: {e['q']}\nA: {e['a']}" for e in hits)
    messages = [{"role": "system", "content": DRAFT_SYSTEM},
                {"role": "user", "content": f"Customer question:\n{item['question']}\n\nFAQ entries:\n{context}"}]
    final, cited, attempts, reason = None, [], 0, None
    for attempt in (1, 2):
        attempts = attempt
        r = request(ctx, "workflow", item["id"], attempt, messages)
        if r["status"] != 200:
            reason = f"request {r['error']}"
            continue
        errors, cited = validate(r["text"], ids)
        final = r["text"].strip()
        if not errors:
            reason = None
            break
        reason = "; ".join(errors)
        messages += [{"role": "assistant", "content": r["text"]},
                     {"role": "user", "content": "Your reply failed these checks:\n- " + "\n- ".join(errors) + "\nRewrite it."}]
    valid = reason is None and final is not None
    if item["expected"] == "NEEDS_HUMAN":
        ok = valid and final == "NEEDS_HUMAN"
    else:
        ok = valid and item["expected"] in cited
    return {"ok": ok, "attempts": attempts, "reason": reason if not ok else None, "retrieved": ids, "cited": cited,
            "final": (final or "")[:300], "ms": int((time.time() - t0) * 1000)}


# ----------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--conc", type=int, default=1)
    ap.add_argument("--types", default="A,B,C")
    ap.add_argument("--out", required=True)
    ap.add_argument("--quixbugs", required=True)
    ap.add_argument("--rfc-dir", required=True)
    ap.add_argument("--work", default="/tmp/kn-b02-work")
    a = ap.parse_args()
    if not KEY:
        raise SystemExit("KUNAVO_API_KEY is not set")
    os.makedirs(a.work, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    ctx = {"model": a.model, "conc": a.conc, "out": a.out, "quixbugs": a.quixbugs, "rfc_dir": a.rfc_dir, "work": a.work,
           "labels": json.load(open(os.path.join(HERE, "extraction-labels.json")))}
    plan = {
        "A": ("code", task_code, json.load(open(os.path.join(HERE, "code-repair-programs.json")))["programs"], lambda p: p),
        "B": ("extract", task_extract, json.load(open(os.path.join(HERE, "extraction-rfcs.json")))["rfcs"], lambda n: f"rfc{n}"),
        "C": ("workflow", task_workflow, json.load(open(os.path.join(HERE, "workflow-questions.json"))), lambda q: q["id"]),
    }
    for t in a.types.split(","):
        name, fn, items, key = plan[t]
        started = time.time()
        with cf.ThreadPoolExecutor(max_workers=a.conc) as ex:
            futs = {ex.submit(fn, ctx, it): it for it in items}
            for f in cf.as_completed(futs):
                it = futs[f]
                try:
                    res = f.result()
                except Exception as e:  # a harness bug is recorded, not hidden
                    res = {"ok": False, "attempts": None, "reason": f"harness {type(e).__name__}: {e}"}
                log(a.out, {"kind": "task", "model": a.model, "conc": a.conc, "type": name, "task": key(it), **res})
        log(a.out, {"kind": "type_done", "model": a.model, "conc": a.conc, "type": name, "wall_s": round(time.time() - started, 1)})
        print(f"{a.model} c{a.conc} {name}: done in {round(time.time() - started)} s", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Helper CLI used by the /outreach skill in Claude Code.

  python outreach.py check "Full Name" "Company" [--linkedin URL]   email guess + already-contacted check
  python outreach.py draft batch.json [--dry-run]                   fill templates -> Outlook drafts
  python outreach.py status                                         history
  python outreach.py config-ok                                      is config.yaml set up?
"""
import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.yaml"
EXAMPLE = ROOT / "config.example.yaml"
DB_PATH = ROOT / "outreach.db"
REVIEW_DIR = ROOT / "review"


def load_config():
    if not CONFIG.exists():
        sys.exit("NO_CONFIG: config.yaml not found. Run the /outreach setup to create it.")
    cfg = yaml.safe_load(CONFIG.read_text()) or {}
    example = yaml.safe_load(EXAMPLE.read_text()) if EXAMPLE.exists() else {}
    cfg.setdefault("companies", cfg.pop("banks", None) or example.get("companies", []))  # older configs
    cfg.setdefault("templates", example.get("templates", {}))
    cfg.setdefault("target", example.get("target", {}))
    return cfg


CFG = load_config()


# ───────────────────────────── storage ─────────────────────────────
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS people (
        key TEXT PRIMARY KEY, name TEXT, title TEXT, bank TEXT, linkedin TEXT,
        email TEXT, email_source TEXT, status TEXT, note TEXT,
        subject TEXT, body TEXT, created TEXT)""")   # "bank" column = company
    return con


def norm_url(u):
    return (u or "").split("?")[0].rstrip("/").lower().replace("http://", "https://").replace("://linkedin", "://www.linkedin")


def person_key(name, company):
    return f"{ascii_name(name)}|{(company or '').lower()}"


def previously_contacted(con, name, company, linkedin=None, email=None):
    row = con.execute(
        "SELECT status, created FROM people WHERE key=? OR (linkedin!='' AND linkedin=?) OR (email!='' AND email=?)",
        (person_key(name, company), norm_url(linkedin), (email or "").lower())).fetchone()
    return dict(row) if row else None


# ───────────────────────────── companies & emails ─────────────────────────────
def ascii_name(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z\- ]", "", s.lower()).strip()


def find_company(name):
    clean = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower().replace("&", "and")).strip()
    n = clean(name or "")
    if not n:
        return None
    for c in CFG["companies"]:
        for a in map(clean, [c["name"]] + c.get("aliases", [])):
            if a == n or (len(a) > 3 and re.search(rf"\b{re.escape(a)}\b", n)):
                return c
    return None


def split_name(full):
    parts = [p for p in re.split(r"\s+", (full or "").replace(",", " ").strip())
             if p and p.strip(".").upper() not in {"CFA", "CPA", "MBA", "JR", "SR", "II", "III", "PHD", "JD", "PE"}]
    if len(parts) < 2:
        return (parts[0] if parts else ""), ""
    return parts[0], parts[-1]


def email_guesses(full_name, company):
    first, last = split_name(full_name)
    f, l = ascii_name(first).replace(" ", ""), ascii_name(last).replace(" ", "").replace("-", "")
    if not f or not l:
        return []
    forms = {"first.last": f"{f}.{l}", "flast": f"{f[0]}{l}", "firstlast": f"{f}{l}",
             "first_last": f"{f}_{l}", "f.last": f"{f[0]}.{l}", "first-last": f"{f}-{l}",
             "first": f, "lastf": f"{l}{f[0]}"}
    return [f"{forms[p]}@{company['email_domain']}" for p in company["patterns"] if p in forms]


def cmd_check(name, company_name, linkedin):
    company = find_company(company_name)
    con = db()
    print(json.dumps({
        "name": name,
        "company": company["name"] if company else None,
        "in_company_list": bool(company),
        "email_guesses": email_guesses(name, company) if company else [],
        "pattern_confidence": company.get("confidence", "medium") if company else None,
        "previously_contacted": previously_contacted(con, name, company["name"] if company else company_name, linkedin),
    }, indent=2))


# ───────────────────────────── templates ─────────────────────────────
class _Blank(dict):
    def __missing__(self, key):
        return "{" + key + "}"          # leave unknown placeholders visible so they're easy to spot


def compose(d):
    tpl = CFG["templates"][d["template"]]
    me = {k: v for k, v in (CFG.get("me") or {}).items() if not isinstance(v, (list, dict))}
    target = CFG.get("target", {}) or {}
    fields = _Blank(**me, **target, Field=" ".join(w[:1].upper() + w[1:] for w in str(target.get("field", "")).split()),
                    availability="\n\n".join(CFG.get("availability", [])),
                    first_name=d["first_name"], company=d["company"], title=d["title"],
                    group=d["group"], connection=d["connection"].strip())
    subject = tpl["subject"].format_map(fields).strip()
    body = re.sub(r"\n{3,}", "\n\n", tpl["body"].format_map(fields)).strip()
    return subject, body


# ───────────────────────────── drafting ─────────────────────────────
REQUIRED = ["name", "first_name", "company", "email", "email_note", "template", "title", "group", "connection"]


def resume_path():
    p = (CFG.get("me") or {}).get("resume_path") or ""
    return str(ROOT / p) if p else ""     # absolute paths pass through


def cmd_draft(batch_path, dry_run=False):
    batch = json.loads(Path(batch_path).read_text())
    for d in batch:                       # accept older "bank"/"personal_paragraph" keys
        d.setdefault("company", d.pop("bank", ""))
        if not d.get("connection") and d.get("personal_paragraph"):
            d["connection"] = d["personal_paragraph"]
    resume = resume_path()
    if not dry_run and resume and not Path(resume).exists():
        sys.exit(f"Resume not found at {resume}. Fix me.resume_path in config.yaml")

    con, todo = db(), []
    for d in batch:
        missing = [k for k in REQUIRED if k not in d]
        if missing:
            print(f"✗ {d.get('name')}: missing fields {missing}")
            continue
        if d["template"] not in CFG["templates"]:
            print(f"✗ {d['name']}: unknown template '{d['template']}' (have: {list(CFG['templates'])})")
            continue
        if previously_contacted(con, d["name"], d["company"], d.get("linkedin"), d["email"]):
            print(f"• skip {d['name']}: already contacted")
            continue
        subject, body = compose(d)
        todo.append((d, subject, body))
        if dry_run:
            print(f"\n{'=' * 70}\nTo: {d['email']}\nSubject: {subject}\n\n{body}")
            leftover = re.findall(r"\{[a-z_]+\}", subject + body)
            if leftover:
                print(f"\n⚠️ unfilled placeholders: {sorted(set(leftover))}")

    if dry_run or not todo:
        return

    from outlook_web import create_drafts
    done = set(create_drafts([{"to": d["email"], "subject": s, "body": b, "attach": resume}
                              for d, s, b in todo], headless=True))

    review = []
    for d, subject, body in todo:
        if d["email"] not in done:
            continue
        con.execute("INSERT OR REPLACE INTO people VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            person_key(d["name"], d["company"]), d["name"], d["title"], d["company"], norm_url(d.get("linkedin")),
            d["email"].lower(), d["email_note"], "drafted", d.get("reviewer_notes", ""), subject, body,
            datetime.now().isoformat(timespec="seconds")))
        flag = "⚠️ " if d["email_note"].upper().startswith("UNCONFIRMED") else ""
        review.append(
            f"## {d['name']}, {d['title']} @ {d['company']}\n"
            f"- Email: {flag}{d['email']} ({d['email_note']})\n"
            f"- LinkedIn: {d.get('linkedin') or '-'}\n- Template: {d['template']}\n"
            + (f"- Note: {d['reviewer_notes']}\n" if d.get("reviewer_notes") else "")
            + "- Facts used:\n" + "".join(f"  - {f['fact']} ({f['source']})\n" for f in d.get("facts_used", [])))
    con.commit()

    if review:
        REVIEW_DIR.mkdir(exist_ok=True)
        path = REVIEW_DIR / f"{datetime.now():%Y-%m-%d_%H%M}.md"
        path.write_text("# Drafts to review in Outlook\n\nCheck ⚠️ emails and any facts that look off before sending.\n\n"
                        + "\n".join(review))
        print(f"\nReview sheet: {path}")
    print(f"{len(done)}/{len(todo)} drafts created in Outlook > Drafts")


def cmd_status():
    con = db()
    for row in con.execute("SELECT status, COUNT(*) c FROM people GROUP BY status"):
        print(f"{row['status']:>10}: {row['c']}")
    for r in con.execute("SELECT created,name,bank,email FROM people ORDER BY created DESC LIMIT 20"):
        print(f"  {r['created'][:10]}  {r['name']} ({r['bank']})  {r['email']}")


def cmd_config_ok():
    me = CFG.get("me") or {}
    problems = [f"me.{k} is empty" for k in ("name",) if not me.get(k)]
    if me.get("resume_path") and not Path(resume_path()).exists():
        problems.append(f"resume not found at {resume_path()}")
    for name, t in CFG["templates"].items():
        if "{connection}" not in t.get("body", ""):
            problems.append(f"template '{name}' has no {{connection}} placeholder")
    print("OK" if not problems else "PROBLEMS:\n- " + "\n- ".join(problems))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("name"); c.add_argument("company"); c.add_argument("--linkedin")
    d = sub.add_parser("draft"); d.add_argument("batch"); d.add_argument("--dry-run", action="store_true")
    sub.add_parser("status"); sub.add_parser("config-ok")
    a = ap.parse_args()
    {"check": lambda: cmd_check(a.name, a.company, a.linkedin),
     "draft": lambda: cmd_draft(a.batch, a.dry_run),
     "status": cmd_status, "config-ok": cmd_config_ok}[a.cmd]()

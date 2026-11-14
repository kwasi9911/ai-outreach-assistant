#!/usr/bin/env python3
"""
Creates Outlook drafts through Outlook on the web (outlook_url in config.yaml), using a dedicated
Chrome profile in .browser_profile/ so you only sign in once.

  python outlook_web.py login                 sign in once; the session is saved locally
  python outlook_web.py draft drafts.json     create every draft in the file

drafts.json: [{"to": "...", "subject": "...", "body": "plain text", "attach": "/path/resume.pdf"}, ...]
"""
import html
import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT = Path(__file__).resolve().parent
PROFILE = ROOT / ".browser_profile"
def _mail_url():
    try:
        import yaml
        return (yaml.safe_load((ROOT / "config.yaml").read_text()) or {}).get("outlook_url") or "https://outlook.office.com/mail/"
    except Exception:
        return "https://outlook.office.com/mail/"


MAIL_URL = _mail_url()
NEW_MAIL = re.compile(r"^New (mail|email|message)", re.I)


def to_html(body):
    paras = [html.escape(p).replace("\n", "<br>") for p in body.strip().split("\n\n")]
    return "".join(f"<div>{p}</div><div><br></div>" for p in paras)


def open_outlook(p, headless=False):
    opts = dict(headless=headless, viewport={"width": 1400, "height": 900},
                args=["--disable-blink-features=AutomationControlled"])
    try:
        ctx = p.chromium.launch_persistent_context(str(PROFILE), channel="chrome", **opts)
    except Exception:  # no Google Chrome installed -> Playwright's own Chromium
        ctx = p.chromium.launch_persistent_context(str(PROFILE), **opts)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(MAIL_URL)
    return ctx, page


def login():
    with sync_playwright() as p:
        ctx, page = open_outlook(p)
        print("Sign in to Outlook in the browser window (up to 10 minutes)...")
        page.get_by_role("button", name=NEW_MAIL).first.wait_for(timeout=600_000)
        print("✓ Signed in. Session saved.")
        time.sleep(2)
        ctx.close()


def make_draft(page, d):
    page.get_by_role("button", name=NEW_MAIL).first.click()

    # To
    to_box = page.locator('[aria-label="To"][contenteditable="true"], div[role="textbox"][aria-label="To"]').last
    to_box.wait_for(timeout=30_000)
    to_box.click()
    page.keyboard.insert_text(d["to"])
    page.keyboard.press("Enter")   # turn the address into a recipient chip
    time.sleep(0.5)

    # Subject
    subj = page.locator('input[aria-label="Subject"], input[placeholder="Add a subject"]').last
    subj.fill(d["subject"])

    # Body: paste as HTML so paragraphs/line breaks survive
    body = page.locator('div[role="textbox"][aria-label^="Message body"]').last
    body.click()
    body.evaluate("""(el, data) => {
        const dt = new DataTransfer();
        dt.setData('text/html', data.html);
        dt.setData('text/plain', data.text);
        el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
    }""", {"html": to_html(d["body"]), "text": d["body"]})
    time.sleep(0.5)
    first_line = d["body"].strip().splitlines()[0]
    if first_line not in body.inner_text():   # fallback: type it
        body.click()
        for i, para in enumerate(d["body"].strip().split("\n")):
            if i:
                page.keyboard.press("Shift+Enter") if para else page.keyboard.press("Enter")
            page.keyboard.insert_text(para)

    # Attachment
    if d.get("attach"):
        with page.expect_file_chooser(timeout=15_000) as fc:
            page.get_by_role("button", name=re.compile(r"^Attach", re.I)).first.click()
            browse = page.get_by_role("menuitem", name=re.compile(r"Browse this computer|Upload from this device", re.I))
            try:
                browse.first.click(timeout=3_000)
            except PWTimeout:
                pass
        fc.value.set_files(d["attach"])
        # match on the plain-ASCII start of the filename (accents like "é" can be encoded differently)
        stem = re.match(r"[A-Za-z0-9 _\-]+", Path(d["attach"]).name).group(0).strip()
        page.get_by_text(re.compile("^" + re.escape(stem))).first.wait_for(timeout=60_000)
        time.sleep(3)  # let the upload finish

    # Save draft and close the compose pane
    page.keyboard.press("Meta+s" if sys.platform == "darwin" else "Control+s")
    time.sleep(2)


def create_drafts(drafts, headless=False):
    with sync_playwright() as p:
        ctx, page = open_outlook(p, headless=headless)
        try:
            page.get_by_role("button", name=NEW_MAIL).first.wait_for(timeout=60_000)
        except PWTimeout:
            ctx.close()
            sys.exit("NOT_SIGNED_IN: run outlook_web.py login and sign in to Outlook, then retry.")
        done = []
        for i, d in enumerate(drafts):
            for attempt in (1, 2):
                try:
                    if i or attempt > 1:
                        # Outlook keeps the saved draft open and hides "New mail"; start fresh each time
                        time.sleep(2)
                        page.goto(MAIL_URL)
                        page.get_by_role("button", name=NEW_MAIL).first.wait_for(timeout=60_000)
                    make_draft(page, d)
                    done.append(d["to"])
                    print(f"✓ draft {i + 1}/{len(drafts)}: {d['to']}")
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"✗ draft {i + 1}/{len(drafts)} failed: {d['to']}: {str(e).splitlines()[0]}")
        time.sleep(3)
        ctx.close()
        return done


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "login":
        login()
    elif len(sys.argv) >= 3 and sys.argv[1] == "draft":
        create_drafts(json.loads(Path(sys.argv[2]).read_text()))
    else:
        print(__doc__)

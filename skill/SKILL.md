---
name: outreach
description: Turn a list of people (LinkedIn links or "Name, Title, Company" lines) into researched, personalized cold networking emails saved as Outlook drafts with the user's resume attached. Use when the user runs /outreach, pastes people to email, asks to set up outreach, sign in to Outlook for outreach, update outreach settings, or see who has been emailed.
---

# /outreach: list of people → personalized Outlook drafts

The user pastes people they want to network with. End with drafts in their Outlook Drafts folder that
they only need to read and send. **Never send email.** The tool only creates drafts.

Tool folder: `{{TOOL_DIR}}`. Use `{{PY}}` for every command. Config: `{{TOOL_DIR}}/config.yaml`.

## 0. Make sure setup is done
Run `{{PY}} {{TOOL_DIR}}/outreach.py config-ok`.
- `NO_CONFIG` or `PROBLEMS` → run **Setup** (bottom of this file) first, then continue.
- If the user only typed `/outreach` with no people, and setup is fine, ask them to paste people
  (one per line: a LinkedIn link, or "Name, Title, Company").

Read `config.yaml`. `me.about_me` holds the facts you may use about the user. Never invent others.
`target.field` is the field they're networking in.

## 1. Parse the input
Each person needs a full name and company, ideally title and LinkedIn URL. LinkedIn pages can't be
fetched, so for a bare URL, web-search the URL / slug to find their name, title and company. If you can't
identify someone, don't guess. Ask the user for their name and company in step 4.

## 2. Check each person
```
{{PY}} {{TOOL_DIR}}/outreach.py check "Full Name" "Company" --linkedin URL
```
- `previously_contacted` not null → skip (tell the user).
- Email = first item of `email_guesses`, with `email_note`:
  - `"Company pattern (high confidence)"` when `pattern_confidence` is high
  - `"UNCONFIRMED: company pattern, medium confidence. Double-check"` otherwise
  - Hyphenated names, nicknames, or unusual names → mark UNCONFIRMED and say why.
  - If research surfaces their real email publicly (bio page, press release), use it: `"Found publicly: <url>"`.
- `in_company_list` false → web-search the company's email format (e.g. "<company> email format").
  If you find a clear one, use it as UNCONFIRMED and offer to add the company to `companies:` in config.yaml.
  If not, ask the user in step 4.

## 3. Research each person (WebSearch, ~2-4 searches each)
Find: their team/group, schools, hometown/country, prior employers, notable work or deals, interviews,
talks, alumni features. Only use facts you're confident are about **this** person (same name and same
company/role). When unsure, leave it out.

Flag anyone who clearly isn't in `target.field` (e.g. operations or HR when the user wants bankers) and
suggest skipping them.

## 4. Ask what the user has in common (REQUIRED: stop and wait before writing anything)
Research misses connections, and the user knows things the web doesn't. Show one short block per person
(2-3 lines) and ask, all in one message:

> **1. Jane Doe, VP @ Example Co (Technology group)**
> Found: University of Michigan → Example Co since 2019; covers software M&A.
> Possible connection: Michigan (your hometown); tech ↔ your startup project.
>
> **2. linkedin.com/in/xyz: couldn't identify.** What's their name and company?
>
> **Do you share anything with any of these people?** For example the same country or city, school,
> high school, club, sport, faith community, mutual friend, family background, or something on their
> LinkedIn that caught your eye. Reply by number, e.g. "1: we both went to Lincoln High". Reply "go" to
> write them as they are.

Also ask here about anything ambiguous (e.g. "LinkedIn shows 'Robert (Bob)'. Which name should I use?").

Treat what they say as fact. Add each new fact they give **about themselves** to `me.about_me` in
config.yaml so future batches can use it.

## 5. Choose a template and write `connection`
Templates live in `config.yaml` under `templates:` (usually `standard` and `personal`).
- `personal` whenever there's a genuine, specific link: anything the user told you in step 4, or a strong
  match between `about_me` and the person (same school, hometown, country, background, or their work
  connects naturally to the user's own experience). Otherwise `standard`.
- Read the chosen template body so `connection` flows naturally from the sentence before it.
- **standard → `connection`**: 1-2 sentences referencing something specific about them and why it interests
  the user.
- **personal → `connection`**: 3-5 sentences, ~70-120 words. **Open with the shared connection, stated
  plainly and specifically** ("Like you, I grew up in Lagos…"), then link it to the user's own story, then
  end with what they'd like to learn from this person. Never water the connection down into something
  generic. The specific detail is the whole point of the email.
- Voice: first person as the user. Warm, direct, humble. No em dashes, no flattery clichés, never imply
  they've met or spoken.
- `title`: e.g. "Vice President". `group`: natural phrasing that reads well in the template (e.g. "the
  Technology group"). Fallback: `target.field` in title case.

## 6. Write the batch and create drafts
Write a JSON array to `{{TOOL_DIR}}/batches/batch-<YYYYMMDD-HHMM>.json`:
```json
{"name": "Full Name", "first_name": "First", "company": "Goldman Sachs", "linkedin": "https://...",
 "email": "first.last@gs.com", "email_note": "Company pattern (high confidence)",
 "template": "personal", "title": "Vice President", "group": "the Technology group",
 "connection": "...",
 "facts_used": [{"fact": "...", "source": "https://... or 'user'"}], "reviewer_notes": ""}
```
1. `{{PY}} {{TOOL_DIR}}/outreach.py draft <batch.json> --dry-run`: read every rendered email and fix anything
   awkward, repetitive, or unverified. Fix any "unfilled placeholders" warning.
2. `{{PY}} {{TOOL_DIR}}/outreach.py draft <batch.json>` creates the Outlook drafts.
3. If it says `NOT_SIGNED_IN`: run `{{PY}} {{TOOL_DIR}}/outlook_web.py login` (a browser window opens and the
   user signs in), then retry.

## 7. Report
A short table: name, company, template, email (⚠️ if unconfirmed), what the email opens with. Then:
anything to check before sending (reviewer notes), anyone skipped and why, and the review sheet path.

---

## Setup (first run, or "set up outreach")
Create `config.yaml` by interviewing the user, so they never have to edit YAML. Start from
`{{TOOL_DIR}}/config.example.yaml` (copy it to config.yaml) and fill it in. Ask in **one or two
friendly messages**, not twenty:

1. Name, phone, the Outlook email they send from, school, major, class year, and year label
   (sophomore / MBA student / analyst…).
2. Field they're networking in, and what for (e.g. "investment banking, summer 2028 internship").
3. Availability for calls (or keep the example slots).
4. Resume: ask them to drag the file into the chat or give its path. Copy it into `{{TOOL_DIR}}/` and set
   `me.resume_path` to the file name. ("none" → `""`, no attachment, and remove the resume sentences from
   the templates.)
5. Background facts for `about_me`: hometown/country, high school, clubs, sports, projects, internships,
   family background. Explain that this is what makes emails personal.
6. Templates: offer to keep the example templates, or ask them to paste the emails they normally send.
   If they paste their own, turn them into templates, replacing the person-specific parts with
   placeholders and the personal-connection part with `{connection}`. Keep their wording otherwise.
   Show the result via a dry run with a made-up person.
7. Outlook URL: work/school Microsoft 365 → `https://outlook.office.com/mail/`; personal outlook.com/hotmail
   → `https://outlook.live.com/mail/`. (Gmail isn't supported.)
8. If `target.field` isn't investment banking, ask which companies they'll target most and replace the
   `companies:` list with those (web-search each company's email format; mark medium confidence unless clearly
   documented).

Then run `{{PY}} {{TOOL_DIR}}/outreach.py config-ok` and, if not already signed in,
`{{PY}} {{TOOL_DIR}}/outlook_web.py login`.

## Other requests
- "Sign me in to Outlook" → `{{PY}} {{TOOL_DIR}}/outlook_web.py login`.
- "Update my outreach settings" (availability, resume, templates, facts about me, companies) → edit config.yaml,
  then run `config-ok`.
- "Who have I emailed?" → `{{PY}} {{TOOL_DIR}}/outreach.py status`.

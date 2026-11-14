# AI Networking Outreach Assistant

Paste a list of LinkedIn profiles into Claude and get back **researched, personalized cold emails sitting
in your Outlook Drafts folder** with your resume attached. You read each one and hit Send.

Built for students networking into investment banking, but it works for any field.

| Before (by hand) | With this tool |
|---|---|
| Search LinkedIn → look up the email in Apollo → verify it in Hunter → research the person → write the email → attach your resume | Paste links → answer "anything in common?" → review drafts |
| ~35 minutes per email | ~3 minutes per email |

## How it works

```
You paste:  linkedin.com/in/jane-doe
            John Smith, Vice President, Citi
                    │
                    ▼
 1. Identify    Finds each person's name, title and company
 2. Email       Builds their address from the company's known format (first.last@gs.com, flast@hl.com, ...)
 3. Research    Web-searches their group, schools, background and deals
 4. Ask you     "Do you share anything with these people?"   ← the step that makes emails personal
 5. Write       Fills in YOUR templates and opens with the shared connection
 6. Draft       Creates the drafts in Outlook on the web, resume attached
                    │
                    ▼
            Outlook > Drafts → you read and send
```

- **It never sends anything.** It only creates drafts.
- **No paid APIs.** No Apollo, Hunter, or Anthropic API keys. It runs on your Claude subscription.
- **No duplicates.** It remembers everyone you've drafted.
- **Review sheet.** Each batch writes a summary of the facts used (with sources) and flags ⚠️ email
  addresses worth double-checking.
- **It doesn't scrape LinkedIn.** That's against LinkedIn's terms and can get your account banned. You paste
  the profiles you found; it does the rest.

## Requirements

- **macOS**
- **A paid Claude plan** (Pro or Max) and the [Claude desktop app](https://claude.ai/download) or Claude Code
- **An Outlook account**: Microsoft 365 (work/school) or outlook.com. Gmail isn't supported yet.
- Google Chrome (optional; a private browser is downloaded if you don't have it)

## Install

1. Download this repo (green **Code** button → **Download ZIP**) and unzip it, or `git clone` it.
2. Double-click **`Setup.command`**.
   > If macOS says it can't verify the file: click **Done**, open **System Settings → Privacy & Security**,
   > scroll down and click **Open Anyway** next to Setup.command. Or run `bash Setup.command` in Terminal.
3. Open the Claude app, go to the **Code** tab and type **`/outreach`**.
   The first time, Claude asks a few questions: your name, school, resume, background, and your
   availability. You can keep the built-in email templates or paste in the emails you normally send.
   A browser window then opens once so you can sign in to Outlook.

The tool installs to `~/OutreachTool`. Your settings, history and Outlook sign-in stay on your Mac.

## Use

In the Claude app (Code tab):

```
/outreach
https://www.linkedin.com/in/someone
https://www.linkedin.com/in/someone-else
Jane Doe, Vice President, Goldman Sachs
```

Claude researches everyone, then asks what you have in common:

> **1. Jane Doe, VP @ Goldman Sachs (Technology group)**
> Found: University of Michigan → Goldman since 2019; covers software M&A.
> Possible connection: Michigan; tech ↔ your startup project.
>
> **Do you share anything with any of these people?**

Reply like `1: we're both from Detroit` (or `go`), and the drafts appear in Outlook a minute later.

Other things you can ask Claude:
- "Update my outreach settings": change your availability, resume, templates or background facts
- "Who have I emailed?"
- "Sign me in to Outlook": if your Outlook session expires

## Customize

Everything lives in `~/OutreachTool/config.yaml` (Claude edits it for you, but you can too):

- **`templates`**: your email templates, with placeholders like `{first_name}`, `{company}`, `{title}`,
  `{group}` and `{connection}` (the part Claude writes for each person).
- **`about_me`**: facts about you that Claude uses to find common ground. Grows automatically as you
  answer the "anything in common?" question.
- **`companies`**: firms and their email formats. It ships with major investment banks. Add your own.

## Good to know

- **Email addresses are educated guesses** from each company's standard format. Most big companies'
  mail servers accept any address, so the format can't be verified automatically. Addresses marked ⚠️ are
  worth a quick check with a free Apollo or Hunter lookup.
- **Read every draft before sending.** Claude only uses facts it found or you gave it, and lists its sources
  in the review sheet, but you're the one hitting Send.
- **Throughput** depends on your Claude plan's usage limits. Our first user went from ~20 to ~120 emails a week.

## Files

| File | What it does |
|---|---|
| `Setup.command` | One-click installer |
| `skill/SKILL.md` | The `/outreach` instructions Claude follows |
| `outreach.py` | Email-format guessing, duplicate checks, template filling, history |
| `outlook_web.py` | Creates the drafts in Outlook on the web (Playwright) |
| `config.example.yaml` | Default settings, templates and company list |

## License

MIT

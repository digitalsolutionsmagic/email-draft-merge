# email-draft-merge

A small, free command-line tool that turns a CSV of leads and a text template into email drafts. One Python file, standard library only, no network access, no API keys. **It never sends anything.**

## What it does

- Reads a CSV (comma, semicolon or tab separated; UTF-8 with or without BOM).
- Fills `{{placeholders}}` in your template from each row. Placeholder names match column names ignoring case, spaces and underscores (`{{first_name}}` matches `First Name`).
- Only writes a draft when every placeholder has a value in that row. If a field is empty, the lead is skipped and the reason is recorded, so no draft contains made-up or blank facts.
- Skips rows with a missing, invalid or duplicate email address.
- Writes one CSV with `row`, `to`, `subject`, `body`, `status` and `reason`, ready to paste or import wherever you send mail.

## What it does not do

- It does not send email, connect to any mail account, or check that an address exists.
- It does not write the personalization for you. The text comes from your template and your CSV.

## Usage

```bash
python3 draftmerge.py leads.csv template.txt                # writes leads.drafts.csv
python3 draftmerge.py leads.csv template.txt -o drafts.csv  # choose the output file
python3 draftmerge.py leads.csv template.txt --email-col "Work Email"
```

The template's first line must be `Subject: ...`. Everything after it is the body. Needs Python 3.8 or newer. It refuses to overwrite an existing output file unless you pass `--force`.

`sample_template.txt`:

```
Subject: A question about {{Company}}

Hi {{First Name}},

I noticed {{Recent Post}} and wanted to ask a quick question.

Thanks,
Your Name
```

## Example

Running it on the included `sample_leads.csv` prints:

```
Read 5 rows from sample_leads.csv
  drafted: 1
  skipped: 4
    row 2: missing email
    row 3: missing value for: Recent Post
    row 4: duplicate email
    row 5: invalid email
Wrote 5 rows to sample_leads.drafts.csv. Nothing was sent.
```

The one draft it wrote, for `ana@acme-example.com`:

```
Subject: A question about Acme Example

Hi Ana,

I noticed your new pricing page and wanted to ask a quick question.

Thanks,
Your Name
```

## Before you send

Read [COMPLIANCE.md](COMPLIANCE.md). It is a short checklist, not legal advice.

## Tests

```bash
python3 -m unittest -v
```

## Want more?

This tool is the free, offline part. The same author sells the **[Cold Email Personalizer](https://payaion.com/m/G5JzEGfU2ueG)** ($19.99 USDC): a Claude skill that drafts personalized cold emails, follow-ups and subject lines from your own lead list using only facts in each lead's row, plus a Python helper that cleans leads and flags bad or duplicate emails, templates, a compliance checklist and examples. It drafts only; nothing is sent.

Payments are in USDC and settle on-chain, so read the listing before you buy. More at the [DigitalSolutions site](https://throbbing-water-9fc1.digitalsolutionsmagic.workers.dev/). To clean a list before merging, see [lead-list-cleaner](https://github.com/digitalsolutionsmagic/lead-list-cleaner).

## License

MIT. See `LICENSE`.

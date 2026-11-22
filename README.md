# Scam Shield UAE

A privacy-conscious verification assistant that recognises **selected, documented UAE scam patterns** (delivery and banking impersonation, English and Arabic) and tells you the safe next step through official channels.

It does **not** say "this is a scam". It says *"this matches a documented warning pattern; don't pay, share codes or click; verify through the official channel."* And it never treats "no match" as "safe".

> Status: v0.1 (core engine, rules, tests, CI). Web UI and live demo are next. See the [roadmap](#roadmap).

## Try it

```bash
pip install -e ".[dev]"
python -m scamshield "Your parcel is on hold. Update your delivery information: http://dhl-parcel-uae.top/track"
```

Example output (abridged):

```
Result: Verify before taking action
[DEL-001] Shipment claim asking you to update or confirm details via a link
  Matched: shipment='parcel', update_or_confirm='update', link='(link present)'
  Source: Abu Dhabi Customs - https://www.adcustoms.gov.ae/... (checked 2026-11-22)
Link hxxp://dhl-parcel-uae[.]top/track: suspicious_tld, lookalike_brand:dhl
What to do: Do not pay, reply, or open any link... Open the courier's official site yourself.
```

API: `pip install -e ".[api]" && uvicorn scamshield.api:app` then `POST /check {"message": "..."}`.

## How it works

- **Evidence-linked rules** (`src/scamshield/data/rules.json`): every rule cites a primary source (publisher, URL, publication date, date checked, review date). Rules are data, not code.
- **CI fails bad rules** (`python -m scamshield.validate`): JSON-schema check, unique IDs, valid template, source host must be on a primary-domain allowlist, no future dates. A stale review date only warns, so the build doesn't break just because time passed.
- **Bilingual matching**: Arabic and English terms; normalisation handles hamza/alef variants, ta marbuta, diacritics, tatweel, Arabic-Indic digits and zero-width characters.
- **Passive URL analysis**: shorteners, IP hosts, suspicious TLDs, `user@host` tricks, and lookalikes of known official domains (DHL, Abu Dhabi Customs, CBUAE, UBF). Links are never fetched, and are returned defanged (`hxxp://evil[.]top`).
- **Official-channel guidance** instead of a score: each result carries concrete next steps from `templates.json`.

## Privacy

The message is analysed in memory and is never stored, logged or echoed back (there is a test for the last one). No accounts. Input is length-limited and validated; the API is rate-limited. Please don't paste passwords, OTPs or full card numbers.

## Evaluation (honest version)

```bash
python -m scamshield.evaluate
```

Latest run, 24 golden cases:

| Category | Positive cases | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| delivery | 7 | 6 | 0 | 1 | 1.00 | 0.86 | 0.92 |
| banking | 5 | 4 | 1 | 1 | 0.80 | 0.80 | 0.80 |

**Read these numbers carefully.** The cases are synthetic and written by the same person who wrote the rules, from the same advisories. This is a regression suite and a sanity check, **not** a measure of real-world detection. A held-out set of real, redacted messages (never used to write rules) is the next evaluation milestone. Until then the only claim made is: *recognises selected documented UAE scam patterns*.

### Known limitations (tested, not hidden)

Marked `known_limitation` in the golden file and run as strict `xfail`, so the suite tells us if a change fixes one by accident.

| Case | What happens | Why |
|---|---|---|
| `DEL-P07` | "Pay AED 5 customs fee to release it" with no link: no match | The cited advisories describe link-based patterns |
| `BNK-P05` | "Reply with the code sent to your phone": no match | No primary source for an OTP rule yet, so no OTP rule |
| `BNK-N04` | Harmless "update the account number in the spreadsheet": flagged | Keyword rules cannot see intent |

Other weaknesses: scam messages that copy "never share your PIN" wording can be suppressed; Cyrillic/Latin homoglyphs aren't handled; the registrable-domain logic is a small stand-in for the Public Suffix List.

## Sources

| Publisher | Document | Published | Used for |
|---|---|---|---|
| Abu Dhabi Customs | Warning on fraudulent text messages impersonating the authority | 2026-03-10 | DEL-001 |
| DHL Express UAE | Fraud awareness page | n/a (checked 2026-11-22) | DEL-002/003/004, official DHL domains |
| Central Bank of the UAE | National fraud awareness campaign release (with UBF, Abu Dhabi Police, Dubai Police) | 2020-04-14 | BNK-001/002/003 |

Not affiliated with any government authority. Not a substitute for official reporting.

## Repo layout

```
src/scamshield/   engine, normalisation, URL analysis, API, CLI, validator, evaluator
  data/           rules.json, schema, templates, brands, primary-source allowlist
tests/            unit tests + golden cases (tests/golden/cases.jsonl)
.github/          CI: validate rules, evaluate, test
```

## Roadmap

- [ ] Web UI (checker, examples, method page) and live demo
- [ ] Held-out evaluation on real, redacted messages
- [ ] Source for OTP-request pattern, then rule
- [ ] Job/visa and government-impersonation categories
- [ ] WhatsApp/Telegram forward-to-check bot
- [ ] Redaction layer (not needed while input is never logged or echoed)

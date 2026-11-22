# Scam Shield UAE

[![CI](https://github.com/NimraNadeemkhan/scam-shield-uae/actions/workflows/ci.yml/badge.svg)](https://github.com/NimraNadeemkhan/scam-shield-uae/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**A privacy-first checker that recognises documented UAE scam patterns and tells you the safe next step.**

Paste a suspicious delivery or banking message (English or Arabic). Scam Shield UAE matches it against source-linked rules, explains why it looks risky, and points you to the official channel to verify. It never opens links and never stores your message.

> **Status:** v0.1 - core engine, rules, tests and CI are done. Web UI and live demo are next ([roadmap](#roadmap)).

## Contents

- [What it does (and doesn't)](#what-it-does-and-doesnt)
- [Quickstart](#quickstart)
- [Example](#example)
- [How it works](#how-it-works)
- [Privacy and safety](#privacy-and-safety)
- [Evaluation](#evaluation)
- [Known limitations](#known-limitations)
- [Sources](#sources)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)

## What it does (and doesn't)

| It does | It does not |
|---|---|
| Recognise **selected, documented** delivery and banking scam patterns | Claim to detect every scam |
| Explain which indicators matched, with a cited official source | Say "this is definitely a scam" |
| Tell you to verify through official channels | Treat "no match" as proof a message is safe |
| Analyse links passively (lookalikes, shorteners, IP hosts) | Open, fetch or click any link |
| Work in English and Arabic | Replace police, bank or official reporting |

The promise is deliberately cautious: *"This matches a documented warning pattern. Don't pay, share codes or click links; verify through the official channel."*

## Quickstart

Requires Python 3.10+.

```bash
git clone https://github.com/NimraNadeemkhan/scam-shield-uae.git
cd scam-shield-uae
pip install -e ".[dev]"
```

Run a check from the command line:

```bash
python -m scamshield "Your parcel is on hold. Update your delivery information: http://dhl-parcel-uae.top/track"
```

Run the quality checks:

```bash
python -m scamshield.validate   # rules: schema, sources, dates
python -m scamshield.evaluate   # golden cases: precision / recall / F1
python -m pytest                # full test suite
```

Run the API:

```bash
uvicorn scamshield.api:app
# POST http://127.0.0.1:8000/check   {"message": "..."}
```

> **Windows tip:** if `pip` or script activation is blocked by your system policy, use `python -m pip ...` and call tools as `python -m ...` as shown above.

## Example

```
Result: Verify before taking action
This matches a documented delivery/customs impersonation warning pattern.

[DEL-001] Shipment claim asking you to update or confirm details via a link
  Matched: shipment='parcel', update_or_confirm='update', link='(link present)'
  Source: Abu Dhabi Customs - https://www.adcustoms.gov.ae/... (checked 2026-11-22)

Link hxxp://dhl-parcel-uae[.]top/track: suspicious_tld, lookalike_brand:dhl

What to do:
  - Do not pay, reply, or open any link in the message.
  - Check the parcel by opening the courier's official website or app yourself.
```

A message with no matching pattern gets an honest answer instead:

```
Result: No documented pattern matched
No documented pattern matched. This does not mean the message is safe.
```

## How it works

1. **Evidence-linked rules** (`src/scamshield/data/rules.json`). Every rule cites a primary source with publisher, URL, publication date, date checked and review date. Rules are data, not hard-coded logic.
2. **Rules are validated in CI** (`python -m scamshield.validate`). It checks the JSON schema, unique IDs, valid templates, that each source host is on a primary-domain allowlist, and that no dates are in the future. A stale review date only warns, so the build does not break just because time passed.
3. **Bilingual matching.** Arabic and English terms, with normalisation for hamza/alef variants, ta marbuta, diacritics, tatweel, Arabic-Indic digits and zero-width characters.
4. **Passive URL analysis.** Flags shorteners, IP hosts, suspicious TLDs, `user@host` tricks and lookalikes of known official domains (DHL, Abu Dhabi Customs, CBUAE, UBF). Official domains suppress link-based rules to avoid false alarms.
5. **Official-channel guidance, not a score.** Each result carries concrete next steps from `templates.json`.

## Privacy and safety

- The message is analysed in memory and is **never stored, logged or echoed back** (a test checks the last one).
- No accounts. Input is length-limited and validated. The API is rate-limited.
- Links are **never fetched**, and are returned defanged (`hxxp://evil[.]top`) so they cannot be clicked.
- Please do not paste passwords, OTPs or full card numbers.

## Evaluation

```bash
python -m scamshield.evaluate
```

Latest run on 24 golden cases:

| Category | Positive cases | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| Delivery | 7 | 6 | 0 | 1 | 1.00 | 0.86 | 0.92 |
| Banking | 5 | 4 | 1 | 1 | 0.80 | 0.80 | 0.80 |

> **Read these numbers carefully.** The cases are synthetic and were written by the same person who wrote the rules, from the same advisories. This is a regression suite and a sanity check, **not** a measure of real-world detection. A held-out set of real, redacted messages (never used to write rules) is the next evaluation milestone. Until then the only claim made is: *recognises selected documented UAE scam patterns*.

## Known limitations

These are tested, not hidden. Each is marked `known_limitation` in the golden file and run as a strict `xfail`, so the suite tells us if a change fixes one by accident.

| Case | What happens | Why |
|---|---|---|
| `DEL-P07` | "Pay AED 5 customs fee to release it" with no link: no match | The cited advisories describe link-based patterns |
| `BNK-P05` | "Reply with the code sent to your phone": no match | No primary source for an OTP rule yet, so no OTP rule |
| `BNK-N04` | Harmless "update the account number in the spreadsheet": flagged | Keyword rules cannot see intent |

Other weaknesses:
- Scam messages that copy "never share your PIN" wording can be suppressed.
- Cyrillic/Latin homoglyphs are not handled.
- The registrable-domain logic is a small stand-in for the Public Suffix List.
- Only delivery and banking are covered. Prize, job, visa and government scams are not.

## Sources

| Publisher | Document | Published | Used for |
|---|---|---|---|
| Abu Dhabi Customs | Warning on fraudulent text messages impersonating the authority | 2026-03-10 | DEL-001 |
| DHL Express UAE | Fraud awareness page | n/a (checked 2026-11-22) | DEL-002, DEL-003, DEL-004, official DHL domains |
| Central Bank of the UAE | National fraud awareness campaign release (with UBF, Abu Dhabi Police, Dubai Police) | 2020-04-14 | BNK-001, BNK-002, BNK-003 |

## Project structure

```
src/scamshield/       engine, normalisation, URL analysis, API, CLI, validator, evaluator
  data/               rules.json, schema, templates, brands, primary-source allowlist
tests/                unit tests + golden cases (tests/golden/cases.jsonl)
.github/workflows/    CI: validate rules, evaluate, test
```

## Roadmap

- [ ] Web UI (checker, examples, method page) and live demo
- [ ] Held-out evaluation on real, redacted messages
- [ ] Primary source for an OTP-request pattern, then a rule
- [ ] Job/visa and government-impersonation categories
- [ ] WhatsApp/Telegram forward-to-check bot
- [ ] Redaction layer (not needed while input is never logged or echoed)

---

*Not affiliated with any government authority. Informational guidance only; not an official fraud report and not a substitute for reporting through official channels.*

Built by [Nimra Nadeem](https://github.com/NimraNadeemkhan).

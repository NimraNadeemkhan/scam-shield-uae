(() => {
  "use strict";

  const MAX_LENGTH = 2000;
  const SAMPLE = "Shipment 7721 could not be delivered. Pay a redelivery fee of AED 4 at https://bit.ly/3xYz12";
  const IDLE_TEXT = "The desk is ready. Paste a message and press Check message. Your slip prints here.";

  const EXAMPLES = {
    suspicious: [
      { label: "Delivery fee with a short link", text: SAMPLE },
      { label: "Arabic shipment update", text: "تعذر توصيل شحنتك. يرجى تحديث بياناتك عبر الرابط https://uae-post-track.top/x" },
      { label: "Card blocked, send your PIN", text: "Your card is blocked. Reply with your card number and PIN to reactivate." },
      { label: "Job offer with a visa fee", text: "Job offer in Dubai: salary AED 9,000. Pay a visa fee of AED 1,500 to start." },
    ],
    normal: [
      { label: "Dinner plans", text: "Hey, are we still on for dinner tonight?" },
      { label: "Bank safety reminder", text: "Your bank will never ask you to share your card number, PIN or password. Stay safe." },
      { label: "Real DHL tracking link", text: "Confirm your delivery slot for your DHL parcel: https://www.dhl.com/ae-en/home/tracking.html" },
    ],
    uncovered: [
      { label: "Prize message", text: "Congratulations! You won AED 50,000. Send your name and Emirates ID to claim." },
      { label: "Traffic fine in Arabic", text: "مخالفة مرورية: ادفع الغرامة فورا لتجنب الحجز" },
      { label: "Asked for a verification code", text: "Please send me the verification code you just received." },
    ],
  };

  const BRAND_NAMES = {
    dhl: "DHL",
    abu_dhabi_customs: "Abu Dhabi Customs",
    cbuae: "the Central Bank of the UAE",
    uaebf: "the UAE Banks Federation",
  };

  const GROUP_LABELS = {
    shipment: "mentions a shipment",
    update_or_confirm: "asks you to update or confirm",
    payment: "asks for a payment or fee",
    request: "asks you to send or confirm something",
    sensitive_detail: "asks for card, PIN or account details",
    bank_context: "mentions your bank, account or card",
    update: "asks you to update or verify",
    details: "refers to your details",
    central_bank: "uses the Central Bank's name",
    prize_word: "sounds like a prize or reward",
    prize_action: "asks you to claim, pay or reply",
    job_word: "mentions a job or visa",
    job_offer: "offers a job or work visa",
    payment_request: "asks you to pay or transfer money",
    visit_visa: "mentions a visit or tourist visa",
    job_money: "asks for a fee, money or documents",
    gov_word: "mentions a fine or an authority",
    gov_action: "pushes you to pay or act fast",
    id_request: "asks you to send or share something",
    id_term: "mentions an ID or verification code",
    money_word: "mentions investing or sending money",
    money_cue: "adds pressure or promises returns",
  };

  const STAMPS = {
    verify: ["Verify first", "Do not pay or click"],
    caution: ["Check the link", "Do not open it"],
    out_of_scope: ["Not covered", "Verify it yourself"],
    no_match: ["No match", "Not a guarantee"],
  };

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const $ = (selector) => document.querySelector(selector);
  const form = $("#check-form");
  const input = $("#message");
  const counter = $("#counter");
  const checkBtn = $("#check-btn");
  const clearBtn = $("#clear-btn");
  const printer = $("#printer");
  const resultEl = $("#result");

  /* ---------- DOM helpers (text only, never innerHTML) ---------- */
  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    if (props) {
      for (const [key, value] of Object.entries(props)) {
        if (key === "class") node.className = value;
        else if (key === "text") node.textContent = value;
        else node.setAttribute(key, value);
      }
    }
    for (const child of children) {
      if (child != null) node.append(child);
    }
    return node;
  }

  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function describeFlag(flag) {
    if (flag === "shortener") return "A link shortener hides where the link really goes.";
    if (flag === "suspicious_tld") return "The address ends in a domain often used for throwaway sites.";
    if (flag === "ip_host") return "The link points to a raw number address instead of a website name.";
    if (flag === "punycode") return "The address uses look-alike characters that can imitate another site.";
    if (flag === "userinfo_trick") return "The link contains a trick that disguises the real website.";
    if (flag.startsWith("lookalike_brand:")) {
      const brand = BRAND_NAMES[flag.split(":")[1]] || "a known organisation";
      return "The address contains the name of " + brand + " but is not one of its official sites.";
    }
    return flag;
  }

  function sourceLine(src, className) {
    const line = el("p", { class: className }, "Source: ");
    if (typeof src.url === "string" && src.url.startsWith("https://")) {
      line.append(el("a", { href: src.url, target: "_blank", rel: "noopener noreferrer", text: src.publisher }));
    } else {
      line.append(src.publisher);
    }
    line.append(". " + (src.published ? "Published " + src.published : "Publication date not stated") + ", checked " + src.checked + ".");
    return line;
  }

  /* ---------- annotating the message (built in the browser from your own text) ---------- */
  function escapeRegex(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Length-preserving folding so match positions in the folded text apply to the original.
  function fold(text) {
    return text
      .replace(/[A-Z]/g, (c) => c.toLowerCase())
      .replace(/[أإآٱ]/g, "ا")
      .replace(/ى/g, "ي")
      .replace(/ة/g, "ه")
      .replace(/’/g, "'");
  }

  function termPattern(term) {
    const body = escapeRegex(fold(term).trim()).replace(/\s+/g, "\\s+");
    return /^[\x00-\x7f]+$/.test(term) ? "(?<![\\p{L}\\p{N}])" + body + "(?![\\p{L}\\p{N}])" : body;
  }

  function collectSignals(data) {
    const list = [];
    for (const match of data.matches) {
      for (const ind of match.matched_indicators) {
        if (ind.term === "(link present)") continue;
        if (!list.some((s) => s.term === ind.term)) list.push({ term: ind.term, group: ind.group });
      }
    }
    for (const topic of data.topics || []) {
      for (const ind of topic.matched_indicators) {
        if (!list.some((s) => s.term === ind.term)) list.push({ term: ind.term, group: ind.group });
      }
    }
    return list;
  }

  function defangedNode(token, delayBase) {
    const node = el("span", { class: "defanged" });
    const cleaned = token.replace(/^http/i, "hxxp");
    cleaned.split(".").forEach((piece, index) => {
      if (index > 0) {
        const dot = el("span", { class: "dot", text: "[.]" });
        dot.style.setProperty("--k", String(delayBase + index));
        node.append(dot);
      }
      node.append(piece);
    });
    return node;
  }

  function annotate(text, data, signals) {
    const bubble = el("p", { class: "message-text", dir: "auto" });
    const hosts = data.url_indicators.map((u) => u.host).filter(Boolean);
    const segments = [];
    if (hosts.length) {
      const linkRe = new RegExp("(\\S*(?:" + hosts.map(escapeRegex).join("|") + ")\\S*)", "gi");
      text.split(linkRe).forEach((part, i) => segments.push({ part, link: i % 2 === 1 }));
    } else {
      segments.push({ part: text, link: false });
    }

    const sorted = signals.map((s, i) => ({ ...s, i })).sort((a, b) => b.term.length - a.term.length);
    const termRe = sorted.length ? new RegExp(sorted.map((s) => termPattern(s.term)).join("|"), "gu") : null;
    let dotCount = 0;

    for (const { part, link } of segments) {
      if (link) {
        const node = defangedNode(part, dotCount);
        dotCount += (part.match(/\./g) || []).length;
        bubble.append(node);
        continue;
      }
      if (!termRe) { bubble.append(part); continue; }
      const folded = fold(part);
      let last = 0;
      for (const m of folded.matchAll(termRe)) {
        if (m.index > last) bubble.append(part.slice(last, m.index));
        const hit = sorted.find((s) => fold(s.term).replace(/\s+/g, " ") === m[0].replace(/\s+/g, " "));
        const ink = el("span", { class: "ink" }, part.slice(m.index, m.index + m[0].length));
        if (hit) {
          ink.style.setProperty("--i", String(hit.i));
          ink.append(el("sup", { text: String(hit.i + 1) }));
        }
        bubble.append(ink);
        last = m.index + m[0].length;
      }
      if (last < part.length) bubble.append(part.slice(last));
    }
    return bubble;
  }

  /* ---------- the slip ---------- */
  function buildSlip(text, data, example) {
    const signals = collectSignals(data);
    const stamp = STAMPS[data.verdict] || STAMPS.no_match;
    const stamped = new Date().toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

    const title = el("h2", { class: "verdict-title", tabindex: "-1", text: data.verdict_label });
    const slip = el("article", { class: "slip result--" + data.verdict },
      el("header", { class: "slip-head" },
        el("span", { class: "slip-name", text: "Inspection slip" }),
        el("span", { text: example ? "Example check" : "Your check" }),
        el("span", { text: stamped }),
        el("span", { text: "Rules version " + data.rules_version })),
      el("div", { class: "verdict-row" },
        el("div", { class: "verdict-text" }, title, el("p", { text: data.summary })),
        el("div", { class: "stamp", "aria-hidden": "true" }, stamp[0], el("span", { class: "stamp-sub", text: stamp[1] }))));

    const message = el("section", { class: "slip-section" },
      el("h3", { class: "slip-h", text: "Your message" }),
      annotate(text, data, signals),
      el("p", { class: "note", text: data.url_indicators.length
        ? "Links are shown with their dots replaced so they can't be tapped." + (signals.length ? " Numbered ink marks are the signals listed below." : "")
        : (signals.length ? "Numbered ink marks are the signals listed below." : "No warning signals were found in the words of this message.") }));
    slip.append(message);

    if (signals.length || data.matches.some((m) => m.matched_indicators.some((i) => i.term === "(link present)"))) {
      const list = el("ol", { class: "signals" });
      signals.forEach((s, i) => {
        list.append(el("li", null, el("span", { class: "sig-n", text: String(i + 1) }),
          el("span", { text: "“" + s.term + "” " + (GROUP_LABELS[s.group] || s.group) })));
      });
      if (data.matches.some((m) => m.matched_indicators.some((i) => i.term === "(link present)"))) {
        list.append(el("li", null, el("span", { class: "sig-n", text: "+" }), el("span", { text: "The message contains a link" })));
      }
      slip.append(el("section", { class: "slip-section" }, el("h3", { class: "slip-h", text: "Signals found" }), list));
    }

    const steps = el("ol", { class: "checklist" });
    data.recommended_actions.forEach((a) => steps.append(el("li", { text: a })));
    slip.append(el("section", { class: "slip-section" },
      el("h3", { class: "slip-h", text: "What to do" }), steps, el("p", { class: "route", text: data.official_route })));

    if (data.matches.length) {
      const why = el("section", { class: "slip-section" }, el("h3", { class: "slip-h", text: "Why it was flagged" }));
      data.matches.forEach((m) => {
        why.append(el("div", { class: "match" }, el("h4", { text: m.title }), el("p", { text: m.why }), sourceLine(m.source, "source")));
      });
      slip.append(why);
    }

    if (data.url_indicators.length) {
      const list = el("ul", { class: "link-list" });
      data.url_indicators.forEach((u) => {
        const notes = u.flags.map(describeFlag);
        if (u.official_brand) notes.push("This is an official address of " + (BRAND_NAMES[u.official_brand] || "a known organisation") + ".");
        if (!notes.length) notes.push("No warning signs in the address itself. That does not prove the page is safe.");
        list.append(el("li", null, el("span", { class: "link-url", text: u.url }), el("span", { class: "source", text: notes.join(" ") })));
      });
      slip.append(el("section", { class: "slip-section" }, el("h3", { class: "slip-h", text: "About the link" + (data.url_indicators.length > 1 ? "s" : "") }), list));
    }

    slip.append(el("p", { class: "fine", text: data.disclaimer }));
    return { wrap: el("div", { class: "slip-wrap" }, slip), slip, title };
  }

  let printTimer = 0;

  function printSlip(parts, { focus }) {
    const { wrap, slip, title } = parts;
    clearTimeout(printTimer);
    resultEl.replaceChildren(wrap);
    const height = slip.getBoundingClientRect().height;
    const ms = reduceMotion.matches ? 0 : Math.min(3000, Math.max(1100, Math.round(height * 2.6)));
    slip.style.setProperty("--print", ms + "ms");
    slip.style.setProperty("--lines", String(Math.max(12, Math.round(height / 22))));
    if (ms) {
      printer.classList.add("is-printing");
      printTimer = setTimeout(() => printer.classList.remove("is-printing"), ms);
    }
    if (focus) {
      title.focus({ preventScroll: true });
      const top = resultEl.getBoundingClientRect().top;
      if (top < 0 || top > window.innerHeight * 0.6) {
        resultEl.scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth", block: "start" });
      }
    }
  }

  function showError(message) {
    clearTimeout(printTimer);
    printer.classList.remove("is-printing");
    resultEl.replaceChildren(el("p", { class: "error", role: "alert", text: message }));
  }

  function showIdle() {
    resultEl.replaceChildren(el("p", { class: "printer-idle", text: IDLE_TEXT }));
  }

  /* ---------- talking to the API ---------- */
  async function fetchCheck(text) {
    const res = await fetch("/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    if (res.status === 429) throw new Error("Too many checks in a short time. Wait a minute, then try again.");
    if (res.status === 422) throw new Error("The message must be between 1 and " + MAX_LENGTH + " characters.");
    if (!res.ok) throw new Error("Something went wrong on our side. Try again in a moment.");
    return res.json();
  }

  async function runCheck(rawText, { example = false } = {}) {
    const text = rawText.trim();
    if (!text) {
      showError("Paste a message first. It needs at least one character.");
      input.focus();
      return;
    }
    if (!example) {
      checkBtn.disabled = true;
      checkBtn.textContent = "Checking";
      form.classList.add("is-scanning");
    }
    try {
      const [data] = await Promise.all([fetchCheck(text), example || reduceMotion.matches ? null : wait(800)]);
      printSlip(buildSlip(text, data, example), { focus: !example });
    } catch (err) {
      if (!example) showError(err instanceof TypeError ? "Couldn't reach the checker. Check your connection and try again." : err.message);
    } finally {
      form.classList.remove("is-scanning");
      checkBtn.disabled = false;
      checkBtn.textContent = "Check message";
    }
  }

  /* ---------- wiring ---------- */
  function updateCounter() {
    counter.textContent = input.value.length + " / " + MAX_LENGTH;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    runCheck(input.value);
  });

  input.addEventListener("input", updateCounter);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      runCheck(input.value);
    }
  });

  clearBtn.addEventListener("click", async () => {
    input.value = "";
    updateCounter();
    const wrap = resultEl.querySelector(".slip-wrap");
    if (wrap && !reduceMotion.matches) {
      wrap.classList.add("is-tearing");
      await wait(450);
    }
    showIdle();
    input.focus();
  });

  for (const [group, items] of Object.entries(EXAMPLES)) {
    const list = $("#examples-" + group);
    items.forEach((example) => {
      const button = el("button", { type: "button", class: "tag", text: example.label });
      button.addEventListener("click", () => {
        input.value = example.text;
        updateCounter();
        runCheck(example.text);
        $("#check").scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth", block: "start" });
      });
      list.append(el("li", null, button));
    });
  }

  async function loadRules() {
    const list = $("#rules-list");
    try {
      const res = await fetch("/rules");
      if (!res.ok) throw new Error("bad status");
      const data = await res.json();
      list.replaceChildren();
      data.rules.forEach((rule) => {
        list.append(el("li", null, el("span", { class: "ledger-title", text: rule.id + "  " + rule.title }), sourceLine(rule.source, "ledger-meta")));
      });
      const version = $("#version");
      if (version) version.textContent = "Rules version " + data.version;
    } catch (err) {
      list.replaceChildren(el("li", { class: "ledger-loading", text: "The rule list couldn't be loaded. Reload the page to try again." }));
    }
  }

  updateCounter();
  loadRules();
  runCheck(SAMPLE, { example: true }); // the desk shows what it does before you use it
})();

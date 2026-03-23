# Pitfalls Research

**Domain:** Autonomous job-hunting agent (scraping, scoring, auto-apply, Telegram reporting, France-focused)
**Researched:** 2026-03-23
**Confidence:** MEDIUM (HIGH for legal/GDPR; MEDIUM for platform detection; MEDIUM-LOW for ATS behavior)

---

## Critical Pitfalls

### Pitfall 1: Platform Ban from Scraping Velocity

**What goes wrong:**
LinkedIn, Indeed, and other job boards detect bot activity by measuring action velocity — the speed at which profiles are visited, pages are scraped, or requests are made. A headless Playwright browser that scrapes 50 job pages in 60 seconds, or sends requests in mechanical uniform intervals, gets flagged and IP-banned. LinkedIn in particular cross-references IP reputation, device fingerprint, and account behavior simultaneously. Apollo and Seamless were officially banned from LinkedIn in 2025 for this exact pattern.

**Why it happens:**
Developers focus on correctness (get all the jobs) and performance (do it fast) and ship with no rate-limiting. The stealth plugin patches the JavaScript `navigator.webdriver` property but does nothing about request timing, IP fingerprint, or behavioral patterns at the network layer. A data-center IP making 300 requests per hour with 2.3-second intervals is not a human, regardless of user-agent spoofing.

**How to avoid:**
- Randomize delays between page loads: use a range like `sleep(random.uniform(3, 12))` not `sleep(5)`
- Use residential proxies or the VPS's clean IP — never a cloud datacenter IP block
- Throttle per platform: 15-20 LinkedIn profile visits per session maximum
- Interleave scraping actions with idle time between platforms
- Implement per-platform rate-limit configs in `career_agent/config/` rather than hardcoding
- Check `robots.txt` for each target platform and respect crawl-delay directives
- Run scraping sessions at varied times (not always 09:00 UTC)

**Warning signs:**
- HTTP 429 responses, CAPTCHA interception, or redirect to `/challenge` page
- Playwright timing out on page loads that previously worked
- Sessions returning empty result sets on platforms that previously had results
- Login-required redirects when scraper is not authenticated

**Phase to address:**
Scraping foundation phase — must be designed with rate limiting before any platform integrations are added.

---

### Pitfall 2: Cloudflare / Turnstile Blocking Playwright Stealth

**What goes wrong:**
`playwright_stealth` is no longer sufficient against modern Cloudflare Turnstile deployments (2025). The library patches the JavaScript surface (removes `navigator.webdriver`, fakes Chrome APIs) but Cloudflare's current bot detection analyzes browser internals, TLS fingerprint (JA3/JA4), mouse movement patterns, and Canvas/WebGL rendering — none of which stealth patches address. As of February 2025, `puppeteer-extra-stealth` is no longer maintained. Indeed, Glassdoor, and LinkedIn all use Cloudflare or equivalent WAFs. Real-browser fingerprinting now catches standard Playwright in high-security contexts.

**Why it happens:**
The stealth plugin was designed for 2022-era bot checks. The detection arms race has moved significantly. Developers see "stealth" in the plugin name and assume it handles everything.

**How to avoid:**
- Use Camoufox (modified Firefox internals, not JavaScript-patched Chromium) for high-security targets
- Consider a headful browser session strategy (non-headless) for platforms with aggressive detection
- For CAPTCHA challenges: integrate a CAPTCHA-solving service (CapSolver) as a fallback, not a primary strategy
- Maintain a per-platform detection log — when a platform starts blocking, the scraper must fail loudly and report via Telegram rather than silently returning empty results
- Accept that some platforms (LinkedIn Easy Apply) may require API-based approaches or official partner integrations

**Warning signs:**
- Playwright returns Cloudflare challenge page HTML instead of job listings
- `cf_clearance` cookie absent or expired despite stealth patches
- Scraper returns 403 instead of redirecting to login (WAF block, not auth block)

**Phase to address:**
Scraping foundation phase. The fallback strategy (fail loudly, report to user, skip platform) must be designed before production scraping begins.

---

### Pitfall 3: Duplicate Application — Same Job Applied Twice

**What goes wrong:**
The agent applies to the same job posting twice: once via direct company website and once via LinkedIn Easy Apply, or once in this run and once in a future run because the deduplication check failed. This gets the candidate flagged as spam in the employer's ATS and potentially blacklisted in shared hiring databases. Some ATS platforms surface duplicate submissions to reviewers with a note, which creates a terrible first impression.

**Why it happens:**
The current `memory.py` uses UUIDv5 derived from the raw URL as the deduplication key. The same job posting appears with different URLs across platforms:
- `https://www.welcometothejungle.com/fr/companies/acme/jobs/senior-dev-123`
- `https://www.linkedin.com/jobs/view/3801234567/` (same role, same company)
- `https://acme.com/careers/senior-dev` (company site)
- `https://www.welcometothejungle.com/fr/companies/acme/jobs/senior-dev-123?utm_source=linkedin` (tracking param variant)

All four produce different UUIDv5 hashes. No deduplication fires. Four applications sent to one employer.

Additionally, tracking parameters (`?utm_source=`, `?trk=`, `?ref=`) on URLs produce different UUIDs for identical job pages.

**How to avoid:**
- Canonicalize URLs before hashing: strip all query parameters that are tracking-only (utm_*, trk, ref, source), normalize scheme to https, remove trailing slashes
- Add a company+role fingerprint layer: hash `(company_name_normalized + role_title_normalized)` as a secondary deduplication key independent of URL
- Deduplicate at the job-entity level, not just the URL level — a job posted on 3 platforms is one entity
- Store both the canonical job ID and all observed URLs in the Qdrant payload
- Before any application submission, check BOTH the canonical URL hash AND the company+title fingerprint
- Log every application with timestamp, platform, and company+title in a structured format

**Warning signs:**
- Multiple entries in Qdrant with different URLs but the same company name and job title
- Telegram reports show the same company/role in two consecutive daily digests
- Application tracking shows "applied" status entries with identical company+role but different source URLs

**Phase to address:**
Deduplication/memory phase — must be hardened before auto-apply is enabled.

---

### Pitfall 4: LLM Hallucination in Auto-Generated Cover Letters

**What goes wrong:**
Gemini generates a cover letter that contains:
- The wrong company name (residual context from a previous generation call)
- Fabricated facts about the company ("Your recent Series B funding round demonstrates...")
- Invented salary expectations the user never specified
- Skills the candidate does not have (hallucinated from job description)
- Wrong role title (especially when the job title is abbreviated or ambiguous)

Since there is no human review gate, these letters go out as-is. The consequence is not just rejection — it is reputational damage. A cover letter claiming false facts about a company is worse than no cover letter.

**Why it happens:**
Gemini (like all LLMs) fills gaps in context with plausible-sounding text. The `tailor.py` prompt sends the job description and `Bio_Context.md` together. If the job description is poorly scraped (truncated, encoded, or garbled by the scraper), the model hallucinates missing details. Context bleed between sequential calls in a batch is also a known failure pattern.

**How to avoid:**
- Add a structured validation step after generation: parse the output and check that company name matches the job listing, role title matches, and no hallucinated credentials appear
- Use a constrained output format (JSON schema) that forces the model to separate factual claims from stylistic text — easier to validate
- Pass the company name and role title as explicit variables in the prompt, not embedded in the job description only
- Implement a post-generation confidence check: re-prompt Gemini to verify the letter only uses facts from the provided context
- Set `temperature=0.3` or lower for letter generation to reduce hallucination rate
- Telegram daily digest should include a summary of what each letter claimed — gives the user a post-hoc review signal

**Warning signs:**
- Cover letters referencing events, products, or facts not mentioned in the job description
- Company name inconsistency between the log entry and the letter content
- Skills in the letter that are absent from `Bio_Context.md`

**Phase to address:**
Cover letter generation phase. Validation must be a first-class concern, not added post-MVP.

---

### Pitfall 5: GDPR / CNIL Legal Risk — France-Specific

**What goes wrong:**
The agent collects, stores, and processes personal data (candidate CV, contact info, application history) and submits it to third parties (employers) without proper legal framework. In France, this triggers GDPR obligations and specific CNIL enforcement. Key risks:

1. **Article 22 GDPR + French Data Protection Act Article 47**: Individuals are protected against fully automated decisions. An employer who uses automated ATS scoring to screen candidates must provide transparency and allow human review. The agent, by submitting applications without any human sign-off, may itself constitute an automated decision-making system in the eyes of the CNIL if the candidate has no awareness of exactly which jobs were applied to.

2. **EU AI Act (in force February 2025)**: HR and recruitment AI tools are classified as high-risk AI systems. Systems that support candidate selection decisions must include risk management, technical documentation, and human oversight mechanisms. An agent that auto-applies without the user reviewing the shortlist may qualify as a high-risk system deployed without required safeguards.

3. **Data minimization**: Scraping job boards and storing job data including employer contact details, recruiter names, and posting text in Qdrant constitutes personal data processing. Qdrant's local deployment at `./qdrant_db` has no encryption at rest by default.

4. **Right to erasure**: If a recruiter's personal data (name, contact) is stored in Qdrant memory, the candidate must be able to delete it on request and prove it was deleted.

**Why it happens:**
Developers treat GDPR as a frontend/web-app concern, not an agentic backend concern. The agent is the user's agent — but the user is also the data subject. Automating actions on behalf of a person does not eliminate their legal obligations as a data controller.

**How to avoid:**
- Implement a "review before first application" confirmation via Telegram: the agent can shortlist and prepare, but the first application to any employer requires a one-time explicit `/apply` command per session or per employer
- Store only what is necessary in Qdrant: job URL, title, company name, score, application date, status — not full job descriptions or recruiter personal details
- Add encryption at rest for Qdrant data (or use Qdrant's built-in encryption config)
- Log every application submission with timestamp and provide the user a retrievable log via Telegram command
- Document the data processing in a simple `DATA_PROCESSING.md`: what is stored, for how long, and why — this is the minimum required documentation under GDPR Article 30
- Set a data retention policy: auto-purge Qdrant entries older than 12 months

**Warning signs:**
- Qdrant collection contains recruiter names, email addresses, or phone numbers scraped from job listings
- No mechanism for the user to see or delete stored application data
- Agent applies to jobs without any user awareness of which specific employers received the application

**Phase to address:**
Legal/compliance review should be a dedicated milestone before production auto-apply is enabled. Not optional.

---

### Pitfall 6: Auto-Follow-Up Sending at Wrong Time or to Wrong Status

**What goes wrong:**
The agent schedules follow-up messages to employers who have not responded after N days. It sends the follow-up:
- To a job the employer already rejected (race condition between status update and follow-up trigger)
- After the user has already been invited to interview and replied manually
- Multiple times because the follow-up itself is not logged as an event in the deduplication system
- In imperfect French (or English instead of French when the original application was in French)

**Why it happens:**
Application status tracking and follow-up scheduling are decoupled. If the status update (rejection email parsed, interview confirmed) arrives after the follow-up job has already been queued, there is no cancellation mechanism. Follow-ups are a separate action from applications and may not be written to Qdrant with the same deduplication key structure.

**How to avoid:**
- Treat follow-up as a state machine: `applied → followed_up → awaiting_response`. A follow-up can only fire if the current state is `applied` and N days have elapsed with no state change
- Store follow-up timestamp in Qdrant payload on submission — not as a separate scheduler entry
- Before sending any follow-up, re-check current status; abort if status has changed since scheduling
- Match follow-up language to the original application language — store the application language in Qdrant metadata
- Rate-limit follow-ups: one follow-up per application, maximum, with configurable day threshold

**Warning signs:**
- Qdrant entries with `status: rejected` that also have a `follow_up_sent` timestamp later than the rejection timestamp
- Telegram reports mentioning a follow-up sent to a company the user was already interviewing with
- Duplicate follow-up entries in the log

**Phase to address:**
Application tracking and follow-up phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Raw URL as deduplication key (current `memory.py`) | Simple to implement, already works | Misses cross-platform duplicates; tracking params cause false misses | Never for production auto-apply |
| Placeholder zero-vector in Qdrant (`[0.0] * 384`) | Avoids embedding API call | Semantic search returns random results; cosine distance meaningless | Acceptable if only using `scroll` + filter queries, not vector search |
| No retry logic on Gemini API calls | Simpler code | Single 429 error aborts an entire job cycle; no graceful degradation | Never for autonomous agent |
| Hardcoded scraper selectors in code (not config) | Faster to write | One HTML change on target site breaks everything silently | Never; selectors must be externalized (already done in `selectors.yaml`) |
| No application state machine (just `applied: bool`) | Minimal schema | Cannot express interview/rejected/offer states; follow-up logic impossible | Never for production tracking |
| Polling instead of webhook for Telegram | No SSL/domain config needed | Higher latency, keeps connection open; 429 risk at high message volume | Acceptable for development; switch to webhook before production |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LinkedIn scraping | Scraping while authenticated with the real user account | Use a dedicated scraping account or no auth where possible; a ban on the scraping account must not affect the user's real account |
| Gemini API (OpenAI-compat layer) | Not handling 429 with exponential backoff | Implement `tenacity`-based retry with jitter; free tier dropped to 5 RPM in December 2025 |
| Qdrant local (`./qdrant_db`) | Path is relative — breaks when the agent runs from a different working directory | Use absolute path via `os.path.abspath()` or env var `QDRANT_DB_PATH` |
| Telegram Bot API | Sending more than 1 message/second to the same chat triggers 429 | Queue all outbound messages; flush at max 1/sec per chat |
| Telegram webhooks | Port must be 443, 80, 88, or 8443; must respond within 60 seconds | Use 443 (already behind Traefik); async handler must not block; set timeout on long operations |
| ATS form submission via Playwright | Bots fill forms faster than humans; honeypot hidden fields get filled | Add human-like delays between field inputs; never fill fields with `display:none` or `visibility:hidden` |
| Welcome to the Jungle / WTTJ | Multiple scraper actors exist on Apify; some are marked DEPRECATED | Verify scraper compatibility before relying on third-party scrapers; build own as fallback |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential Gemini calls for scoring 50 jobs | Cycle takes 15+ minutes; Telegram reports arrive stale | Use `asyncio.gather` with concurrency cap (already in `app.py` with limit=5) | At 20+ jobs per cycle |
| Scraping all platforms in one session | Session ends with a ban from one platform that cascade-invalidates the IP for others | Isolate platforms to separate sessions/IPs; fail one without failing all | First time a platform bans the IP |
| Loading full `Bio_Context.md` in every prompt | Token costs escalate; context window hits limit on long bios | Extract only relevant sections per job type; keep bio under 2,000 tokens | Bio > 3,000 tokens |
| Storing full job descriptions in Qdrant | Qdrant payload bloats; scroll queries slow down | Store only structured metadata: title, company, URL, score, status, date | After 1,000+ stored jobs |
| Polling Telegram for updates in a tight loop | CPU waste; risk of exceeding update poll rate | Use `allowed_updates` filter; set 30-second long-poll timeout | Always; resolve before production |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing `GEMINI_API_KEY` in Qdrant payload or logs | Key leaked in Telegram output or log files | Never log secrets; use env vars exclusively; audit log output before shipping |
| No Telegram user ID whitelist enforcement | Anyone who finds the bot token can trigger job applications on behalf of the user | Enforce `NEMO_AUTH_USER_ID` check on every command handler; reject all other senders |
| Qdrant data unencrypted at rest | Candidate CV data, application history exposed if VPS compromised | Enable filesystem encryption on VPS volume; or migrate to Qdrant Cloud with at-rest encryption |
| Scraping credentials (LinkedIn login) in `.env` | Credential exposure if `.env` committed or VPS breached | Use secret scanning in CI (already in place); confirm `.env` is in `.gitignore`; rotate credentials if ever exposed |
| Auto-apply with no audit log | No way to prove what was submitted, to whom, when | Write immutable application log to append-only file in addition to Qdrant; expose via `/history` Telegram command |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent failures — scraper blocked, no Telegram alert | User thinks agent is working; no applications going out | Every scraper failure must emit a Telegram alert immediately with platform name and error type |
| Daily digest too long (50 jobs processed listed individually) | User ignores digests; important alerts buried | Digest = summary stats + top 3 matches + any interviews/rejections. Details available on demand via `/pipeline` |
| No pause/resume capability | User cannot stop agent during active job negotiations | `/pause` and `/resume` commands are not optional; without them, user loses control of autonomous system |
| Follow-up sent in English to French employer | Breaks formality; signals bot behavior | Store `application_language` in metadata; follow-up prompt must match |
| Cover letter not archived | User cannot see what was sent; cannot retrieve for interview prep | Store cover letter text (or hash + key passages) in Qdrant payload at application time |

---

## "Looks Done But Isn't" Checklist

- [ ] **Deduplication:** URL-based check passes — verify company+title fingerprint check also exists and fires before application submission
- [ ] **Scraping:** Jobs are returned — verify the scraper is not hitting a cached/static page rather than live listings
- [ ] **Cover letter generation:** Letter produced — verify company name, role title, and no fabricated facts against source job description
- [ ] **Auto-apply:** Form submitted — verify a confirmation (HTTP 200, success page text, or email receipt) was received; not just "form was filled"
- [ ] **Application tracking:** Entry in Qdrant — verify status field exists and is set to a valid enum value, not just `True`
- [ ] **Follow-up:** Scheduled — verify follow-up cannot fire if status has changed to `rejected` or `interview` between scheduling and execution
- [ ] **GDPR compliance:** Data stored — verify only minimum necessary fields are stored; no recruiter PII stored without specific need
- [ ] **Telegram reporting:** Message sent — verify the bot token and chat ID are correct; test delivery with a known-good message at startup

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Platform ban (IP or account) | HIGH | Rotate IP (VPS IP change or proxy); wait 24-72 hours before retrying; consider dedicated scraping proxy service |
| Duplicate application sent | MEDIUM | Cannot unsend; document in Qdrant with `duplicate: true` flag; user can optionally send a withdrawal email via Telegram command |
| LLM hallucination in sent cover letter | HIGH | No recovery; retrospective review of all letters sent in the same batch; compare against job description to identify other affected applications |
| GDPR violation (unauthorized data storage) | HIGH | Delete affected Qdrant collection; notify affected parties if required by CNIL; implement proper data minimization before resuming |
| Gemini API quota exhausted mid-cycle | LOW | Exponential backoff resumes cycle; incomplete jobs are re-queued next cycle; no data loss if Qdrant write is atomic |
| Qdrant corruption (local file-based store) | MEDIUM | Local Qdrant has no replication; implement periodic snapshot backup to `./qdrant_db_backup/`; restore from latest snapshot |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Platform ban from velocity | Scraping foundation | Rate-limit config exists; randomized delays verified in integration test; per-platform throttle enforced |
| Cloudflare/Turnstile blocking | Scraping foundation | Each target platform tested with a real request; fallback alert mechanism tested |
| Duplicate application | Deduplication hardening (before auto-apply) | Test: same job posted on 3 platforms → only 1 application; tracking-param URL variants → same UUID |
| LLM hallucination in letters | Cover letter generation | Validation step exists; JSON schema enforced on output; company name verified against job metadata |
| GDPR / CNIL compliance | Legal review milestone (before production) | Data minimization audit; encryption at rest confirmed; audit log accessible via Telegram |
| Auto-follow-up to wrong status | Application tracking phase | State machine implemented; follow-up tests against all status transitions |
| Silent scraping failure | Scraping foundation | Every scraper error emits Telegram alert; tested with simulated block |
| Gemini quota exhaustion | API integration phase | Retry with backoff implemented; tested with mocked 429 response |
| No pause/resume | Telegram command interface | `/pause` and `/resume` commands implemented before autonomous mode enabled |
| Qdrant data loss | Infrastructure phase | Backup strategy implemented; restore tested before production |

---

## Sources

- [LinkedIn Automation Safety Guide 2026 — Dux-Soup](https://www.dux-soup.com/blog/linkedin-automation-safety-guide-how-to-avoid-account-restrictions-in-2026)
- [LinkedIn Automation Limits 2025 — Konnector](https://konnector.ai/linkedin-automation-limits-2025/)
- [Why LinkedIn Thinks You're Using Automation — Bearconnect](https://bearconnect.io/blog/linkedin-automation-tool-warning/)
- [How Companies Detect and Disqualify Bot Applications — GetJobs AI](https://getjobs-ai.app/blog/how-companies-detect-and-disqualify-bot-assisted-application-submission)
- [Auto-Apply Job Bots Killing Your Chances — The Interview Guys](https://blog.theinterviewguys.com/auto-apply-job-bots-might-feel-smart-but-theyre-killing-your-chances/)
- [Can AI Cover Letters Be Detected — Originality.AI](https://originality.ai/blog/ai-detection-cover-letters)
- [GDPR for Recruiting 2025 — Moka HR](https://www.mokahr.io/myblog/gdpr-for-recruiting/)
- [Use of AI in Recruitment — Greenberg Traurig](https://www.gtlaw.com/en/insights/2025/5/use-of-ai-in-recruitment-and-hiring-considerations-for-eu-and-us-companies)
- [CNIL New Guidelines on HR Processing — Hogan Lovells](https://www.hoganlovells.com/en/publications/cnils-new-guidelines-on-hr-processing)
- [AI System Development: CNIL Recommendations — CNIL](https://www.cnil.fr/en/ai-system-development-cnils-recommendations-to-comply-gdpr)
- [Data Protection France 2025 — ICLG](https://iclg.com/practice-areas/data-protection-laws-and-regulations/france)
- [EU AI Act France 2025 — Chambers and Partners](https://practiceguides.chambers.com/practice-guides/artificial-intelligence-2025/france)
- [Autonomous AI Agent Failure Modes — Unite.AI](https://www.unite.ai/the-ai-agents-trap-the-hidden-failure-modes-of-autonomous-systems-no-one-is-preparing-for/)
- [Agentic AI Risks — Domino Data Lab](https://domino.ai/blog/agentic-ai-risks-and-challenges-enterprises-must-tackle)
- [Bypass Cloudflare with Playwright 2025 — Kameleo](https://kameleo.io/blog/how-to-bypass-cloudflare-with-playwright)
- [Playwright Stealth Bot Detection — Bright Data](https://brightdata.com/blog/how-tos/avoid-bot-detection-with-playwright-stealth)
- [Gemini API Rate Limits — Google AI for Developers](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Gemini API Error 429 Fix 2026 — AI Free API](https://www.aifreeapi.com/en/posts/gemini-api-error-429-resource-exhausted-fix)
- [LinkedIn URL Normalization Deduplication Failures — n8n GitHub](https://github.com/n8n-io/n8n/issues/16402)
- [Long Polling vs Webhook — grammY](https://grammy.dev/guide/deployment-types)
- [Telegram Bot FAQ — Telegram](https://core.telegram.org/bots/faq)
- [LLM Hallucination Examples — EvidentlyAI](https://www.evidentlyai.com/blog/llm-hallucination-examples)

---
*Pitfalls research for: Autonomous job-hunting agent (NemoClaw / Project Phoenix)*
*Researched: 2026-03-23*

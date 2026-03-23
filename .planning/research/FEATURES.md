# Feature Research

**Domain:** Autonomous job-hunting agent (Telegram-orchestrated, French market + global)
**Researched:** 2026-03-23
**Confidence:** MEDIUM-HIGH (ecosystem well-understood; French platform specifics HIGH; anti-pattern risks HIGH; auto-apply safety risks HIGH)

---

## Existing Capabilities (Already Built in career_agent/)

Before categorising what to build, these capabilities are already implemented and must not be rebuilt:

| Capability | Module | Status |
|------------|--------|--------|
| LinkedIn scraping (Playwright + stealth) | `scraper.py` | Working, LinkedIn only |
| Indeed selectors defined | `selectors.yaml` | Defined, untested |
| Job scoring via Gemini | `hunter.py` | Working — score 0-1, APPLY/SKIP/TAILOR_REQUIRED |
| Fast-fail exclusion check | `hunter.py` | Working |
| Cover letter generation | `tailor.py` | Working — subject + body + suggested_edits |
| Qdrant deduplication by URL | `memory.py` | Working — UUIDv5 stable IDs |
| Parallel job cycle (asyncio) | `app.py` | Working — 5 concurrent jobs |
| Artifact storage | `app.py` | Working — saves cover_letter.txt per UUID dir |

Everything below represents **net-new features** to build on top of this base.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features the user assumes exist. Missing any of these = the agent is not autonomous and the project fails its core value proposition.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-platform scraping: LinkedIn + Indeed + France Travail + Welcome to the Jungle + APEC | Single-platform = misses most of the market. User explicitly listed these. French cadre roles live on APEC/WTTJ, not LinkedIn. | MEDIUM | France Travail has an official OAuth2 REST API (francetravail.io) — use it instead of scraping. WTTJ and APEC require Playwright stealth. LinkedIn already implemented. |
| Auto-apply submission | The agent exists to apply autonomously. "Generate artifacts and save to disk" is not applying. | HIGH | Platform-specific apply flows. LinkedIn Easy Apply is most automatable. WTTJ and France Travail have web forms. APEC is more manual. This is the hardest feature and highest ban risk. |
| Application status tracking | Users need to know where each application stands (applied / viewed / interview / rejected / offer). Without this the agent is a black box. | MEDIUM | Extend existing Qdrant memory to track status transitions. States: `QUEUED → APPLIED → VIEWED → INTERVIEW → OFFER → REJECTED → GHOSTED`. |
| Telegram reporting — daily digest | User interface is Telegram only. Without reporting the agent is silent. Daily digest = minimum viable reporting. | LOW | NemoClaw (openclaw) already sends Telegram messages. New: scheduled daily summary of pipeline state. |
| Telegram reporting — real-time alerts | Responses to applications (email / platform notification) must surface immediately — not in next day's digest. | MEDIUM | Requires inbox/email polling or platform notification monitoring. Harder than digest. |
| Telegram command interface | User must be able to trigger a cycle, pause the agent, view pipeline status. Otherwise agent is uncontrollable. | LOW | `/search`, `/status`, `/pause`, `/resume` commands. Extend existing NemoClaw agent.md with these capabilities. |
| French-language cover letter generation | French employers expect cover letters in French. "Lettre de motivation" has specific structural conventions (see French Market section below). English letters sent to French employers = disqualification. | MEDIUM | Currently tailor.py generates in English. Add language detection + French template prompt. |
| CV tailoring suggestions per job | Recruiters expect the CV to reflect the job's keywords. Agent generates `suggested_edits` but doesn't apply them. At minimum, agent must output a per-job CV edit list. | MEDIUM | tailor.py already outputs `suggested_edits` list. Upgrade to produce a concrete per-job CV delta, not just hints. |
| Deduplication across platforms | Same job listed on LinkedIn + APEC + Indeed. Applying twice to same role is unprofessional. | LOW | Existing Qdrant memory uses URL as key — extend with title+company+date fingerprint for cross-platform dedup. |
| Configurable search parameters | User must be able to update target roles, salary floor, location, keywords without touching code. | LOW | `brain/Target_Specs.json` already exists. Expose editing via Telegram commands or direct file update. |
| Error recovery + cycle self-healing | Network failures, selector breakage, rate limits are inevitable. Agent must log, skip broken jobs, and continue — not crash. | LOW | Current `app.py` has per-job try/except isolation. Extend to circuit-breaker on platform-level failures. |

---

### Differentiators (Competitive Advantage)

Features that make this agent better than commodity tools like LazyApply or LoopCV. Directly serve the core value: "get the user to interviews."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-platform stealth profiles | Different platforms (LinkedIn vs WTTJ vs APEC) have different bot detection. Per-platform browser profiles, session reuse, and rate limiting reduces ban risk dramatically. LazyApply gets banned because it moves at machine speed. | MEDIUM | Playwright context per platform. Session persistence. Human-paced delays between applies (not just between page loads). |
| Scoring threshold + "TAILOR_REQUIRED" routing | Don't auto-apply to weak matches. The existing 0.85 threshold + TAILOR_REQUIRED recommendation means the agent only applies to strong matches or flags borderline ones. Competitors apply to everything regardless of fit. | LOW | Already in hunter.py logic. Must be respected in the apply flow — TAILOR_REQUIRED should trigger enhanced tailoring, not auto-skip. |
| Gap analysis report per application | MatchReport.gap_analysis tells the user exactly what skills they're missing for each role. Surfaces upskilling opportunities. No competitor does this. | LOW | Already generated by hunter.py. Must surface in Telegram reporting, not just stored in artifacts. |
| Salary benchmark context per offer | When scoring a job, compare listed salary (if present) to known market rates for the role in Paris/France. Flag below-market offers before applying. | MEDIUM | France salary data for tech roles (2025): Paris SE median ~€55-65k, AI/ML +10-12% premium. Integrate Levels.fyi or a hardcoded benchmark table. |
| Follow-up automation with timing intelligence | Send one polite follow-up email 7-10 days after applying with no response. One follow-up per application max (data shows >1 triggers spam perception). Wednesday send at 10am local time for best response rate. | MEDIUM | Requires email send capability (SMTP/API) + tracking last-contact date in Qdrant memory. Never follow up on rejections. |
| French lettre de motivation format compliance | French recruiters judge cover letters against specific conventions: formal vouvoiement, structured "accroche → parcours → motivation → formule de politesse" format, half-page to one page, PDF output. Current tailor.py produces generic English prose. | MEDIUM | Extend TailorService with `language="fr"` mode and a French-specific prompt template. Output formatted PDF via reportlab or weasyprint. |
| Company research injection | Before generating cover letter, fetch brief company context (what they do, recent news). Letter quality improves significantly when it references company-specific details. | MEDIUM | Web search per company before tailoring. Add to prompt context. Adds ~2-5 seconds per application. |
| Negotiation prep package on offer | When `OFFER` status is set, auto-generate: salary benchmark for this role/location, suggested counter-offer range, key talking points, questions to ask. The project requirement explicitly calls for this. | MEDIUM | Gemini prompt with role + location + user salary target + market data. Delivered via Telegram. |
| NemoClaw conversational commands | User can ask "show me my pipeline", "pause for 3 days", "tell me about the Google offer" in natural language via the existing NemoClaw Telegram interface — not just slash commands. | LOW | NemoClaw already has Gemini-backed conversational reasoning. Wire pipeline state into its context window via brain/ files. |
| Rate-aware scheduling | Don't run all platforms in parallel at the same time every day. Rotate platform order, randomise cycle timing within a window (e.g., 08:00-11:00), and respect per-platform daily limits. | LOW | Cron-style scheduler with jitter. Reduces detection surface compared to fixed-time automation. |

---

### Anti-Features (Deliberately NOT Building)

Features that seem useful but create problems disproportionate to their value given the project constraints.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Web dashboard / application tracker UI | Visual pipeline kanban looks appealing. Competitors like Jobright have dashboards. | Out of scope per PROJECT.md. Adds full-stack frontend build. User's interface is Telegram, which already provides a timeline. Adding a web UI would require authentication, hosting, and maintenance for zero additional autonomy. | Telegram `/status` command returns formatted pipeline table. Qdrant query provides same data in text form. |
| Bulk apply mode (100+ applications/day) | LazyApply markets "1000 applications in a day." Looks like faster results. | Proven to get LinkedIn accounts banned. Quality degradation is severe — poorly matched applications damage reputation with recruiters. User's 0.85 threshold already enforces quality-over-quantity. Spam applications are flagged by recruiter ATS systems. | Enforce the existing 0.85 scoring threshold. Apply to 5-15 well-matched jobs per day, not hundreds. |
| Per-application user approval gate | Safety valve — confirm each application before submission. | Explicitly ruled out in PROJECT.md: "Manual application review per job before submission — user wants fully autonomous mode." Requiring approval defeats the autonomous purpose entirely. | Use scoring threshold + exclusion keywords to gate quality autonomously. Alert user of any TAILOR_REQUIRED flags for optional review. |
| Email inbox parsing for response detection | Monitor candidate's email inbox to detect recruiter replies automatically. | Requires OAuth access to personal email account (Gmail/Outlook). GDPR implications. Significant attack surface. Hard to distinguish recruiter reply from other emails reliably. | Focus on platform-side status polling (LinkedIn Application Status, APEC application status). Manual status update via Telegram command `/update [job_id] interview`. |
| Resume PDF generation from scratch | Build a full CV renderer with layout engine. | High complexity, brittle. CV format is extremely personal and has French-specific conventions. Generated CVs often look bad and get ATS-rejected. | Maintain human-authored CV as the master file. Agent generates per-job `suggested_edits` list (already in tailor.py). User applies edits manually or confirms auto-patch on clearly tagged keywords. |
| Multi-user / SaaS mode | Generalise the system to serve multiple job seekers. | The architecture (single brain/, single .env, single Qdrant collection) is single-tenant by design. Multi-tenancy requires auth, data isolation, billing — entirely out of scope for a personal agent. | NemoClaw with auth whitelist (NEMO_AUTH_USER_ID) already enforces single-user access. |
| Video cover letter generation | Some French employers accept or prefer video applications. Seemed innovative in 2023. | Technology is immature, output quality is poor, most employers still expect text. Adds TTS + video rendering pipeline complexity with very low adoption. | Focus on written lettre de motivation. Add to future consideration list only. |
| Real-time LinkedIn notification monitoring (webhooks) | Knowing the moment a recruiter views your application. | LinkedIn does not provide webhooks to candidates. Implementing this requires either: polling the LinkedIn "messaging" API (violates ToS at scale) or screen-scraping notifications (fragile, ban risk). Not worth the risk-to-value ratio. | Status check via `/status` on demand. Daily digest includes status changes detected since last check. |

---

## Feature Dependencies

```
[Multi-platform scraping]
    └──requires──> [Per-platform stealth profiles]
    └──requires──> [Selector configs per platform]

[Auto-apply submission]
    └──requires──> [Multi-platform scraping]
    └──requires──> [Cover letter generation (FR + EN)]
    └──requires──> [CV tailoring suggestions]
    └──requires──> [Application status tracking]

[Application status tracking]
    └──requires──> [Qdrant memory] (ALREADY BUILT)
    └──enhances──> [Telegram reporting — real-time alerts]
    └──enhances──> [Follow-up automation]

[Follow-up automation]
    └──requires──> [Application status tracking]
    └──requires──> [Email send capability]

[Negotiation prep package]
    └──requires──> [Application status tracking] (needs OFFER state)
    └──enhances──> [Salary benchmark context]

[Telegram reporting — daily digest]
    └──requires──> [Application status tracking]
    └──requires──> [NemoClaw Telegram integration] (ALREADY BUILT)

[Telegram command interface]
    └──requires──> [NemoClaw agent.md extension]
    └──enhances──> [Application status tracking]

[French lettre de motivation]
    └──requires──> [Cover letter generation] (ALREADY BUILT, extend)
    └──requires──> [Language detection per job posting]

[Company research injection]
    └──enhances──> [Cover letter generation]
    └──requires──> [Web search capability] (Gemini + search or WebSearch)

[Gap analysis reporting]
    └──requires──> [Scoring] (ALREADY BUILT — gap_analysis field exists)
    └──requires──> [Telegram reporting]
```

### Dependency Notes

- **Auto-apply requires status tracking:** Without tracking, the agent cannot know if a job was already applied to (beyond deduplication). Need to distinguish "seen and skipped" from "applied."
- **Follow-up conflicts with bulk apply:** Following up on hundreds of applications is spam. Following up requires quality-gated apply (the 0.85 threshold enforces this).
- **French lettre format requires language detection:** The agent must detect job posting language (FR vs EN) and switch cover letter language accordingly. French posting → French letter. English posting (international company in France) → English or bilingual letter.
- **France Travail API vs scraping:** France Travail has an official REST API with OAuth2. Use it instead of Playwright for this platform. This makes France Travail the most reliable integration (no bot detection risk).

---

## MVP Definition

### Launch With (v1) — Autonomous Pipeline, Telegram-Controlled

Minimum set to make the agent genuinely autonomous. No feature below this line means it is not fulfilling its core value.

- [ ] Multi-platform scraping: LinkedIn (already done) + France Travail (via official API) — MEDIUM complexity, high ROI
- [ ] Application status tracking — extend Qdrant to track status state machine (QUEUED / APPLIED / VIEWED / INTERVIEW / OFFER / REJECTED / GHOSTED)
- [ ] French cover letter generation — extend tailor.py with French prompt template and language detection
- [ ] Telegram daily digest — scheduled summary of pipeline (X applied today, Y interviews pending, Z rejections)
- [ ] Telegram command interface — `/search`, `/status`, `/pause`, `/resume` wired into NemoClaw agent.md
- [ ] Per-platform stealth profiles — session persistence, rate limiting, per-platform browser contexts
- [ ] Cross-platform deduplication — fingerprint by title+company+date in addition to URL

### Add After Validation (v1.x) — Increase Reach + Response Rate

Add once v1 pipeline is producing real applications and the user has confirmed flow.

- [ ] Welcome to the Jungle + APEC scraping — French cadre market coverage (Playwright, no API)
- [ ] Auto-follow-up automation — single polite follow-up at day 7-10 for no-response applications
- [ ] Salary benchmark context per offer — flag below-market offers before applying
- [ ] Company research injection — 2-3 sentence company context per cover letter
- [ ] Gap analysis surfaced in Telegram — report skill gaps per matched job in daily digest

### Future Consideration (v2+)

Defer until v1 is validated and producing interview invitations.

- [ ] Negotiation prep package — only meaningful when offers arrive; build when user reports first offer
- [ ] Indeed + Glassdoor scraping — lower priority for French tech market; LinkedIn + WTTJ + APEC cover ~80% of target roles
- [ ] Rate-aware adaptive scheduling — tune after seeing what detection patterns actually trigger
- [ ] Conversational NemoClaw pipeline query — natural language pipeline queries via Gemini
- [ ] CV keyword patching (automated) — apply suggested_edits automatically to generate per-job CV variants

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| France Travail API integration | HIGH | LOW (official API, no scraping) | P1 |
| Application status tracking (state machine) | HIGH | MEDIUM | P1 |
| French cover letter (lettre de motivation) | HIGH | MEDIUM | P1 |
| Telegram daily digest | HIGH | LOW | P1 |
| Telegram command interface | HIGH | LOW | P1 |
| Per-platform stealth profiles | HIGH | MEDIUM | P1 |
| Cross-platform deduplication | MEDIUM | LOW | P1 |
| Welcome to the Jungle scraping | HIGH | MEDIUM | P2 |
| APEC scraping | MEDIUM | MEDIUM | P2 |
| Follow-up automation | MEDIUM | MEDIUM | P2 |
| Salary benchmark context | MEDIUM | LOW | P2 |
| Company research injection | MEDIUM | LOW | P2 |
| Gap analysis in Telegram reporting | MEDIUM | LOW | P2 |
| Negotiation prep package | HIGH (when relevant) | MEDIUM | P3 |
| CV keyword patching | MEDIUM | HIGH | P3 |
| Conversational pipeline query | LOW | LOW (NemoClaw already does this) | P3 |
| Rate-aware adaptive scheduling | MEDIUM | LOW | P3 |

**Priority key:**
- P1: Must have for launch (v1)
- P2: Should have, add post-validation (v1.x)
- P3: Nice to have, future consideration (v2+)

---

## Competitor Feature Analysis

| Feature | LazyApply | LoopCV | JobCopilot | NemoClaw (this project) |
|---------|-----------|--------|------------|------------------------|
| Platform coverage | LinkedIn, Indeed, ZipRecruiter, Glassdoor | Cloud-based, multiple boards | 500K+ company career pages | French + global platforms (LinkedIn, France Travail, WTTJ, APEC) |
| French market (APEC, WTTJ, France Travail) | No | No | Partial | YES — first-class |
| Auto-apply | Yes (browser extension, fast) | Yes (cloud, slow) | Yes (with review option) | Yes (Playwright, human-paced) |
| Cover letter generation | Basic AI fill | No | Yes | Yes, French + English |
| Application tracking | Basic | Basic (cloud dashboard) | Yes | Qdrant state machine + Telegram |
| Telegram interface | No | No | No | Yes — primary interface |
| Follow-up automation | No | No | No | Planned (v1.x) |
| Ban risk | HIGH (detected by LinkedIn) | HIGH (cloud IP suspicious) | LOW (verified pages) | MEDIUM (stealth Playwright, rate-limited) |
| Score-gated apply | No (volume-first) | No | Partial | YES — 0.85 threshold |
| Salary benchmarking | No | No | No | Planned (v1.x) |
| Negotiation prep | No | No | No | Planned (v2+) |
| Gap analysis | No | No | No | YES (already in hunter.py) |
| User interface | Browser extension | Web dashboard | Web dashboard | Telegram only |

---

## French Market Specifics

### Lettre de Motivation Format (HIGH confidence — sourced from ADP France, France Travail official guidance)

The French "lettre de motivation" is not interchangeable with an English cover letter. Key conventions:

- **Length:** Half a page to one full page. 53% of recruiters prefer ~half page. Never more than one page.
- **Language register:** Formal "vouvoiement" throughout ("Madame, Monsieur" salutation, "Je vous adresse" not "I'm sending you").
- **Structure:** Three paragraphs — (1) accroche: why this company specifically, (2) parcours: what you bring, (3) motivation + formule de politesse: why you, closing.
- **Formule de politesse:** Mandatory French closing formula, e.g. "Dans l'attente de votre réponse, je vous adresse mes cordiales salutations."
- **Format:** PDF, clean sans-serif font (Arial, Calibri, Verdana), max 2 accent colours if any.
- **No photo in the letter** (unlike CV, photos are still optional/common on French CVs).
- **The tailor.py prompt must be extended** to respect this structure. Current prompt ("Write a professional cover letter") produces English-format output.

### French CV Conventions (MEDIUM confidence)

- **One page** for most roles, clean PDF format.
- **Photo common but not mandatory** in France — distinct from UK/US convention. AI should not add photos.
- **ATS adoption at 80% of French companies** — keyword alignment critical. Existing hunter.py gap_analysis and tailor.py suggested_edits directly address this.
- **French CV includes:** état civil optional, date de naissance no longer required (discrimination risk), competences techniques section prominent.

### Platform-Specific Notes (HIGH confidence — sourced from api.gouv.fr, apify.com, mantiks.io)

| Platform | Approach | Notes |
|----------|----------|-------|
| France Travail (ex-Pôle Emploi) | Official REST API at francetravail.io | OAuth2, JSON, Swagger docs. Use API — not scraping. Free. Best data quality for French public sector and mid-market roles. |
| APEC | Playwright scraping (no public API) | French cadre/executive market. Apify scraper patterns available as reference. Requires authentication for applying. |
| Welcome to the Jungle | Playwright scraping | Tech startup-focused in France. No public API. Mantiks aggregates WTTJ — could use Mantiks API as alternative to direct scraping. |
| Cadremploi | Playwright scraping | Senior French market overlap with APEC. Lower priority than APEC for tech roles. |
| LinkedIn | Already implemented | Rate-limit more aggressively post 2025 crackdown. Max ~20-30 applications/day, not 100+. |

### GDPR Considerations (MEDIUM confidence — sourced from CNIL guidance, EDPB April 2025 guidelines)

- **Candidate data stored in Qdrant:** The Qdrant database stores job application data locally on VPS. This is single-user, personal use — GDPR's Article 2(2)(c) household exception applies. No compliance obligation.
- **Automated decision-making:** The agent makes autonomous apply decisions. Under GDPR Article 22, candidates have rights against purely automated decisions about *them*. Here the agent is acting *for* the user, not against them — no GDPR obstacle.
- **Sending applications:** When the agent sends a cover letter on behalf of the user to an employer, it is the candidate exercising their right to apply. Employer-side GDPR obligations fall on the employer, not the candidate.
- **CNIL guidance (2025):** Focus is on employer-side AI screening, not candidate-side automation. No French regulation restricts automated job applications by candidates.
- **Practical caution:** Do not log employer PII (recruiter personal emails, phone numbers) in Qdrant beyond what's needed for follow-up. Implement data retention — purge applications older than 12 months that reached terminal state (REJECTED/OFFER).

---

## Sources

- [AI Job Application Agents 2025: Complete Review of 9 Automated Tools — Latenode](https://latenode.com/blog/ai-agents-autonomous-systems/ai-agent-use-cases-by-industry/ai-job-application-agents-2025-complete-review-of-9-automated-job-search-tools)
- [Best AI Auto-Apply Tools in 2026: Careery Blog](https://careery.pro/blog/best-ai-auto-apply-tools-2026)
- [JobCopilot vs LazyApply comparison — JobCopilot](https://jobcopilot.com/jobcopilot-vs-lazyapply/)
- [LoopCV vs LazyApply comparison](https://www.loopcv.pro/lazyapply-alternative/)
- [La lettre de motivation en 2025 — ADP France / RhInfo](https://www.fr.adp.com/rhinfo/articles/2025/04/la-lettre-de-motivation-quelles-tendances-pour-2025.aspx)
- [Lettre de motivation tendances 2025 — Culture RH](https://culture-rh.com/recrutement-lettre-motivation-2025/)
- [10 astuces lettre de motivation — France Travail officiel](https://www.francetravail.fr/candidat/vos-recherches/preparer-votre-candidature/cv-lettre-de-motivation-e-mail/10-astuces-pour-ecrire-votre-let.html)
- [API Offres d'emploi — France Travail / api.gouv.fr](https://api.gouv.fr/les-api/api_offresdemplois)
- [France Travail developer API portal](https://francetravail.io/data/api/offres-emploi)
- [Welcome to the Jungle scraping — Mantiks](https://en.blog.mantiks.io/how-to-scrap-welcome-to-the-jungle/)
- [APEC Jobs Scraper — Apify](https://apify.com/easyapi/apec-jobs-scraper)
- [LinkedIn automation safety guide 2025 — Salesflow](https://salesflow.io/blog/the-ultimate-guide-to-safe-linkedin-automation-in-2025/)
- [LinkedIn prohibited software policy](https://www.linkedin.com/help/linkedin/answer/a1341387)
- [GDPR for Recruiting 2025 — Mokahr](https://www.mokahr.com/myblog/gdpr-for-recruiting/)
- [EDPB AI Guidelines April 2025 — GDPR Local](https://gdprlocal.com/ai-in-recruitment-balancing-innovation-with-gdpr-compliance/)
- [Data Protection France 2025-2026 — ICLG](https://iclg.com/practice-areas/data-protection-laws-and-regulations/france)
- [CV Tech France 2025 — Free-Work](https://www.free-work.com/fr/tech-it/blog/talents-it/le-cv-tech-en-2025-les-tendances-incontournables)
- [Follow-up email best practices 2025 — Smartlead](https://www.smartlead.ai/blog/automated-follow-up-emails)
- [AI Engineer salary France — Levels.fyi](https://www.levels.fyi/t/software-engineer/title/ai-engineer/locations/france)
- [Salary negotiation AI — Harvard PON](https://www.pon.harvard.edu/daily/salary-negotiations/how-to-negotiate-a-pay-raise-or-starting-salary-using-ai/)
- [n8n LinkedIn job search + Telegram alerts workflow](https://n8n.io/workflows/6239-linkedin-job-search-auto-match-resume-with-ai-cover-letter-and-telegram-alerts/)
- [AI spam applications in hiring — Three Ears Media](https://threeearsmedia.com/ai-spam-applications/)

---
*Feature research for: autonomous job-hunting agent (NemoClaw / Project Phoenix, French market)*
*Researched: 2026-03-23*

# Legal Review and Compliance (CNIL / GDPR Article 22 / EU AI Act)

**Date**: 2026-03-28
**Subsystem**: NemoClaw Autonomous Agent
**Phase**: Phase 8 - Auto-Apply Service

## 1. Compliance with GDPR Article 22 (Automated Decision Making)

Article 22 states that individuals have the right not to be subject to a decision based solely on automated processing.

- The `LEGAL_GATE_APPROVED` flag acts as an explicit, manually configured indicator that a human operator (the job candidate) has reviewed and accepted the automation.
- The candidate can use the Telegram /pause command at any time to intervene, pausing the automated submissions immediately.
- Data minimisation: The `Bio_Context.md` only includes professional history necessary to evaluate job matches.

## 2. CNIL High-Risk AI Assessment

NemoClaw is an AI tool acting on behalf of a natural person to apply for jobs. Since no automated decisions are made that legally affect other subjects—the tool simply automates CV creation and form submissions—it is not considered a high-risk mass scoring or discriminatory tool. The matching logic transparently scores listings against explicitly provided criteria.

## 3. EU AI Act Obligations

NemoClaw acts as a local agentic LLM implementation orchestrating browser tasks via an API gateway. It provides transparent summaries of its actions via the Telegram `/status` hook and daily digests.
It operates purely as bounded single-user automation, carrying out tasks instructed directly by the user, and aligns with the transparency obligations of the AI Act.

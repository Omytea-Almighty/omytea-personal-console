# Privacy Policy — Omytea Personal Future Console (Public Beta)

**Effective**: pending public deployment (see `DEPLOYMENT_GUIDE.md`)
**Last updated**: 2026-05-18
**Operator**: Omytea LLC, Wyoming, USA
**Contact**: `lewxam0102@gmail.com`

This policy governs the **publicly deployed Streamlit Cloud version** of the Omytea Personal Future Console. Early testers reached via a manual hand-off receive a parallel notice off-line; that notice is functionally equivalent to this one for their data.

---

## 1. What this product is

A probabilistic decision-support tool that takes a user-described personal decision (career / lifestyle / relationship / life-direction) and generates probability-calibrated future scenarios. **Not** fortune-telling, oracular prediction, medical/legal/financial advice, or psychotherapy.

---

## 2. What data we collect

When you submit a prediction request, we collect:

| Data | Purpose |
|---|---|
| Decision context (free-text fields you fill in the form) | Generate your prediction |
| User handle (`user_id` you pick) | Match your prediction to followup |
| Generated prediction (model output) | Display to you + store for 6-week verification |
| Optional H4 metrics (NPS / utility / pay willingness) | Product research |
| Optional 6-week measurement update (actual outcomes) | Product research (H3 hypothesis validation) |
| Browser locale (auto) | Currency display (USD default) |

**We do NOT collect**:
- Your real name or email (unless you choose to put them in your handle / decision context)
- Tracking pixels, third-party analytics, advertising IDs
- Browser fingerprint, IP address (beyond Streamlit Cloud's standard logging)
- Any data not visible in the form

---

## 3. Where data lives

| Storage | Provider | Retention |
|---|---|---|
| App database | (Postgres on Neon / Supabase / Hetzner — TBD per DEPLOYMENT_GUIDE.md §5) | Until you request deletion |
| Anthropic API call transcripts | Anthropic | 30 days per their privacy policy |
| Streamlit Cloud platform logs | Snowflake (parent company of Streamlit) | Per Streamlit Cloud retention policy |
| Founder's local backup | Encrypted disk on founder's laptop | Same as app database |

---

## 4. Who has access

- **Founder**: full access. Reviews predictions to confirm output quality during beta.
- **Cofounder**: limited; only with separate signed approval for specific debugging tasks.
- **Anthropic** (model provider): processes your decision context to generate predictions, subject to their privacy policy.
- **Streamlit / Snowflake** (hosting): server logs only; not application data.
- **Third parties**: never sold, never shared with employers / governments / advertisers / data brokers unless legally compelled with notice to you.

---

## 5. Your rights

- **Access**: request a machine-readable export of your data
- **Rectification**: correct errors
- **Deletion**: permanent removal from all systems we control
- **Withdraw consent**: stop the 6-week followup nudge anytime
- **Opt out of academic publication**: even if previously opted in
- **Object**: tell us to stop processing for any reason

To exercise: email `lewxam0102@gmail.com` with subject "Omytea data request". Response within 7 days.

---

## 6. Anonymization for academic publication

If you opt in (separate consent checkbox in the form), your data may appear in:

- Academic papers (arXiv / journal / workshop / NeurIPS-style)
- Conference talks / public blog posts
- Public research reports

**Anonymization rules**:
- User handle → random pseudonym (`user_001`, `user_002`, …)
- Decision context paraphrased to remove identifying details (company names, specific cities, named individuals)
- Direct quotes attributed only as "anonymized beta participant"

**Will never publish**:
- Your name, email, original handle if it looks identifying
- Verbatim decision context (only paraphrased)
- Employer / city / institution names

You may withdraw consent until 14 days before submission of any specific work.

---

## 7. Data security

- Encrypted disks for all backups
- 2FA on Anthropic API, GitHub, email accounts
- No third-party tracking pixels
- Postgres connection over TLS (when production DB is configured)
- Server access logs reviewed weekly
- No public-facing admin panel

**Breach notification**: in the event of a confirmed unauthorized access, we notify affected users within 72 hours of discovery.

---

## 8. Children's privacy

This product is **not intended for users under 18**. If you are under 18, do not use this product. If we learn we collected data from a minor, we delete it.

---

## 9. International data transfer

Omytea LLC is Wyoming-based. Your data + the Anthropic API call may transit US servers regardless of your location. By using this product you consent to this transit.

For users in jurisdictions with stronger privacy frameworks (EU GDPR, California CCPA, China PIPL): we honor the underlying rights (access / rectification / deletion / objection) regardless of where you are. Contact us for jurisdiction-specific clarifications.

---

## 10. Limitations on this product

- **Not professional advice**. Don't make medical / legal / financial decisions based solely on this. We're a decision-thinking aid, not a doctor / lawyer / financial advisor.
- **Beta product**. Bugs, downtime, output errors are possible. We don't warrant any specific accuracy threshold.
- **Calibrated, not deterministic**. Probabilities are estimates; actual outcomes will vary. The point is to think about uncertainty, not eliminate it.

---

## 11. Cookies + analytics

- We use only Streamlit Cloud's session cookies (functional, required for the app to work)
- No third-party analytics (no Google Analytics, no Mixpanel, no Segment)
- No advertising pixels
- No retargeting

---

## 12. Children of users / discussed persons

If you describe a decision involving other people (partner, family, coworker), be aware that you're sharing third-party information with us + Anthropic. Avoid full names and other identifying details if possible. We treat all such content as confidential to you, but the data minimization principle applies.

---

## 13. Changes to this policy

Material changes will be:
1. Posted at this URL with updated "Last updated" date
2. Emailed to known users at the address they used during signup
3. Effective 14 days after notice

Continued use after 14 days = consent to new terms. You may withdraw participation at any point during or after the notice window.

---

## 14. Governing law + disputes

Wyoming, USA. Disputes through arbitration (American Arbitration Association). You retain right to small-claims court in your jurisdiction for amounts under $5,000.

---

## 15. Contact

For all privacy questions, data requests, complaints:

**Email**: `lewxam0102@gmail.com`
**Subject**: start with `Omytea privacy:` for fastest routing
**Response time**: within 7 calendar days

---

**Plain-language summary**: We collect what you give us on the form. We use it to make your prediction + do research. We don't sell it, share with employers, or run ads. We anonymize before publishing anything publicly. Delete on request. Beta product so things may break. If in doubt, email Jiaxuan.

— Jiaxuan, Omytea LLC, 2026-05-18

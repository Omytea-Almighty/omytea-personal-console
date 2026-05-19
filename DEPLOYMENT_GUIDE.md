# Streamlit Cloud Deployment Guide — Omytea Personal Future Console

**Hybrid distribution policy**: deploy publicly only AFTER ≥ 1-2 high-trust early testers have completed a manual round-trip and validated the prediction quality is OK.

**Estimated effort**: 1-2 hours (assuming GitHub repo + Streamlit Cloud account already exist).

**Estimated ongoing cost**: ~$0.30-2.50 total API spend for 10 users × 3-5 queries each, plus $0 hosting on Streamlit Cloud free tier (Community plan).

---

## §0 Pre-deployment checklist

Before deploying:

- [ ] Founder has completed self-test step 1-5 (✅ done 2026-05-18, prediction_id `5fc55de0-784e-4287-beec-3b2ad28f7c36`)
- [ ] Cofounder + 1 close friend have completed Path α manual self-test
- [ ] Path α prediction quality is OK (founder reviews their outputs, confirms not embarrassing)
- [ ] Founder has Anthropic API key with non-zero balance + monthly budget cap set (recommend: $20/month cap)
- [ ] Repository is pushed to GitHub
- [ ] Streamlit Cloud account created (free; sign in with GitHub)
- [ ] Privacy policy reviewed + linked from app footer (`PRIVACY_POLICY.md`)

---

## §1 Repository preparation

### §1.1 Decide: separate repo or subdir?

Two options:

**Option A**: Keep `omytea-personal-console/` as a subdir of the WMDB monorepo. Streamlit Cloud supports subdir-as-app via the "Main file path" config.

**Option B**: Spin out to a separate dedicated public repo `omytea-personal-console` for clean isolation.

**Recommendation**: **Option B for public deploy.** Reasons:
- WMDB has sensitive `legal/` artifacts + research drafts we don't want public-visible (even with .gitignore, public repos are forensically scannable)
- Cleaner separation: deployment repo = product surface; WMDB = R&D
- Easier for cofounder to push frontend fixes without touching WMDB
- Public repo lets us accept GitHub Issues from friend testers

Plan: when ready to deploy, `git subtree split` the `omytea-personal-console/` subtree into a new public repo `Adonyth/omytea-personal-console` (or similar org/repo).

### §1.2 Subtree split commands (when ready)

```bash
cd /Users/chenjiaxuan/Downloads/WMDB

# Create the split branch (new history rooted at the subdir)
git subtree split --prefix=omytea-personal-console -b deploy-split

# Create new GitHub repo first (UI or `gh repo create Adonyth/omytea-personal-console --public`)

# Push to new repo
git remote add console-deploy git@github.com:Adonyth/omytea-personal-console.git
git push console-deploy deploy-split:main
```

### §1.3 Files that MUST be in the deploy repo

After subtree split, verify these are present at the deploy repo root:

- [ ] `streamlit_app.py` (entrypoint)
- [ ] `app.py` (main UI logic)
- [ ] `compiler.py`
- [ ] `console.py`
- [ ] `storage.py`
- [ ] `scenarios/` directory
- [ ] `tests/` directory
- [ ] `requirements.txt`
- [ ] `.streamlit/config.toml`
- [ ] `README.md` (with "try the demo" link section)
- [ ] `PRIVACY_POLICY.md` (linked from app footer)
- [ ] `DEPLOYMENT_GUIDE.md` (this file)

### §1.4 Files to ADD to deploy repo `.gitignore`

```
# Deployment repo — never commit these
__pycache__/
*.pyc
.venv/
venv/
.env
*.sqlite
*.db
.streamlit/secrets.toml      # NEVER commit secrets file
distribution_kit/            # internal-only kit
```

The `distribution_kit/` directory stays in WMDB only — not in public deploy repo.

### §1.5 omytea substrate dependency

The console imports `from omytea.quantum import ...` etc. For deployment we need to either:

**Option a**: Vendor the minimal Omytea modules into the deploy repo (`omytea_quantum/` flat package; copy `quantum.py` + `joint_belief.py` + `models.py` + minimal dependencies). Apache 2.0 license compatible. Pin to a specific Omytea commit hash.

**Option b**: Publish Omytea quantum substrate to PyPI as a separate package (`pip install omytea-quantum-substrate`), then `requirements.txt` adds it.

**Recommendation**: **Option a (vendor minimal)** for now — Option b is v4.16 P3 territory (the substrate-as-Apache-2.0-package release). Vendor 4 files (quantum.py, joint_belief.py, models.py, density.py), pin to commit `<TBD>`, mark in `VENDORED_FROM.md`.

⚠️ **Until vendored**: deploy will fail import. **DEPLOYMENT IS BLOCKED on completing this step.**

---

## §2 Streamlit Cloud configuration

### §2.1 Create app

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Click "New app"
4. Repository: `Adonyth/omytea-personal-console` (or wherever you pushed the subtree split)
5. Branch: `main`
6. Main file path: `streamlit_app.py`
7. (Advanced) Python version: 3.11+
8. Click "Deploy"

### §2.2 Set secrets

After initial deploy (will fail until secrets set):

1. App dashboard → ⚙️ Settings → Secrets
2. Paste:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
# Optional: customize per scenario
# OMYTEA_CONSOLE_LOG_LEVEL = "INFO"
```

3. Save. App auto-restarts with secrets injected as env vars.

### §2.3 Set monthly budget cap (Anthropic console)

CRITICAL — protects against API runaway:

1. https://console.anthropic.com → Billing
2. Set monthly cap: **$20/month** (10× expected for 10 self-test users)
3. Set email alert at 50% threshold

---

## §3 Privacy + Terms surface

### §3.1 Footer link in app.py

Add to `render_sidebar()` in `app.py`:

```python
st.sidebar.markdown(
    "[Privacy](https://github.com/Adonyth/omytea-personal-console/blob/main/PRIVACY_POLICY.md) · "
    "[GitHub](https://github.com/Adonyth/omytea-personal-console) · "
    "© 2026 Omytea LLC"
)
```

### §3.2 First-use consent screen

Add a one-time "I understand + agree" gate before first prediction. Store consent in `st.session_state`. On consent, allow form access. On decline, show "no problem, come back later".

This is **MUST-HAVE for public deploy** even though Path α users consent via email.

### §3.3 Data deletion endpoint

Provide an email + form for users to request deletion. Per `PRIVACY_POLICY.md`, response within 7 days.

---

## §4 Public README adjustments

The current `omytea-personal-console/README.md` is geared toward developers. For public deploy, modify the top section to include:

```markdown
# Try Omytea

**Live demo**: https://omytea-personal-console.streamlit.app (or your actual URL)

Probability-calibrated decision-support for personal-future scenarios.
Free during research beta. Not for medical / legal / financial advice.
By participating you consent to our [Privacy Policy](PRIVACY_POLICY.md).
```

Move the developer-detail sections (Architecture, Quick start, etc.) below this.

---

## §5 SQLite data extraction strategy

Streamlit Cloud containers have ephemeral filesystems by default. The SQLite database at `~/.omytea-personal-console/predictions.db` will be **wiped on container restart** unless we configure persistence.

Three options:

### Option α — Periodic snapshot to GitHub

Add a `scripts/snapshot_predictions.py` that pulls the SQLite to a JSON dump + commits to a private "predictions-mirror" repo every hour. Crontab-style via Streamlit Cloud (does not natively support cron; use a separate small fly.io or Render free-tier worker).

**Pros**: simple data audit trail in git.
**Cons**: extra infra.

### Option β — Direct DB push from app

After each `storage.save_prediction()`, push the file to a private GCS bucket / S3 bucket / Hetzner Storage Box. Requires service account credentials as another Streamlit secret.

**Pros**: real-time persistence.
**Cons**: ~$0.10/month storage cost + service account complexity.

### Option γ — Postgres via Neon or Supabase free tier

Replace SQLite with a Postgres connection (free tier). Update `storage.py` to support both backends via env var.

**Pros**: cleanest data lifecycle.
**Cons**: code change (replace SQLite-specific code in `storage.py`) + adds dependency.

**Recommendation**: **Option γ Postgres** for sustained deploy. For first-week MVP, **Option α GitHub snapshot is acceptable**.

⚠️ **DEPLOYMENT BLOCKED on resolving this — until then, user data will be wiped on container restart.**

---

## §6 First-week monitoring

After deploy:

- [ ] Day 1: founder + cofounder use the public URL to test. Verify substrate works.
- [ ] Day 1-3: invite 3 friends to Path β URL. Watch logs.
- [ ] Day 3-7: invite remaining 5-7 friends.
- [ ] Daily: check Anthropic API usage on console (predict.streamlit cap)
- [ ] Daily: check SQLite dump (Option α / β / γ) for any malformed predictions
- [ ] Each prediction: founder reviews privately to confirm output quality remains acceptable

---

## §7 Rollback plan

If anything breaks:

1. Disable the Streamlit app via dashboard (one click)
2. Email all known users: "demo is paused, no data loss, will resume after fix"
3. Diagnose locally
4. Re-deploy when fixed

**Worst case**: data extracted from snapshot/backup; manual completion of remaining users via Path α.

---

## §8 Decision gate: deploy or not?

Path γ recommendation says **deploy only after Path α validation**. Before clicking "Deploy" on Streamlit Cloud, founder should confirm:

- [ ] Cofounder Path α self-test completed
- [ ] ≥ 1 friend Path α self-test completed
- [ ] Founder reviewed both predictions and is OK with the quality
- [ ] Anthropic monthly budget cap is set
- [ ] PRIVACY_POLICY.md is committed in deploy repo
- [ ] First-use consent gate is implemented
- [ ] SQLite persistence strategy is implemented (Option α / β / γ)
- [ ] omytea substrate has been vendored (per §1.5)

**If any unchecked**: don't deploy yet. Run Path α only.

---

## §9 Companion files

- `streamlit_app.py` — Streamlit Cloud entrypoint
- `.streamlit/config.toml` — server + theme config
- `PRIVACY_POLICY.md` — required for public deploy
- `requirements.txt` — Python dependencies
- `distribution_kit/` (WMDB only, not in deploy repo) — Path α materials

---

**END OF DEPLOYMENT GUIDE**

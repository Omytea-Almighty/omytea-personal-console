# Streamlit Cloud Deployment Guide — Omytea Personal Future Console

Notes for hosting the Python version on Streamlit Cloud. The browser version at https://omytea-console.pages.dev is hosted separately.

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

This is **required for any public deploy**.

### §3.3 Data deletion endpoint

Provide an email + form for users to request deletion. Per `PRIVACY_POLICY.md`, response within 7 days.

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

~~⚠️ **DEPLOYMENT BLOCKED on resolving this — until then, user data will be wiped on container restart.**~~

**Status (2026-05-19)**: ✅ **unblocked via Option α**. `scripts/snapshot_predictions.py` dumps the SQLite DB to a portable JSON artifact. Run it on a cron (Streamlit Cloud doesn't natively schedule, so use a tiny external worker — fly.io free, Render free, or a scheduled GitHub Action). Commit the JSON to a private "predictions-mirror" repo or push to private bucket per your preference. Option γ (Postgres swap in `storage.py`) remains the long-term solution but is no longer release-blocking.

```bash
# On any external worker every N minutes:
python scripts/snapshot_predictions.py \
  --db-path ~/.omytea-personal-console/predictions.db \
  --output-dir /var/snapshots \
  --pretty

# Outputs predictions_snapshot_<unix>.json
```

---

## §7 Rollback plan

If anything breaks:

1. Disable the Streamlit app via dashboard (one click)
2. Email all known users: "demo is paused, no data loss, will resume after fix"
3. Diagnose locally
4. Re-deploy when fixed

**Worst case**: data extracted from snapshot/backup.

---

## §9 Companion files

- `streamlit_app.py` — Streamlit Cloud entrypoint
- `.streamlit/config.toml` — server + theme config
- `PRIVACY_POLICY.md` — required for public deploy
- `requirements.txt` — Python dependencies

---

**END OF DEPLOYMENT GUIDE**

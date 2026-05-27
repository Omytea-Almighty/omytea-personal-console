# SETUP_TURSO.md — durable storage for Omytea Console

**Why this exists.** Streamlit Community Cloud's filesystem is ephemeral — on every redeploy (push to `main` / manual reboot) the container's disk is wiped. That means the local SQLite DB at `~/.omytea-personal-console/predictions.db` does **not** survive across redeploys. The Omytea PMF candidate loop (`predict → wait N months → score`) cannot work without durable storage.

Iter #44 wires **[Turso](https://turso.tech/)** — a hosted libSQL service that's 100% wire-compatible with SQLite. When the env vars `OMYTEA_TURSO_URL` + `OMYTEA_TURSO_AUTH_TOKEN` are set the console writes predictions + measurements + drill-downs to Turso instead of the local filesystem.

Without these env vars the console falls back to local SQLite — local dev, local tests, and the existing offline-first behavior are unchanged.

---

## ~3-minute founder setup

You need a Turso account + one database + one auth token.

### 1. Install the Turso CLI

```bash
brew install tursodatabase/tap/turso
# or curl -sSfL https://get.tur.so/install.sh | bash
```

### 2. Sign up + log in

```bash
turso auth login          # opens GitHub OAuth in your browser
turso auth whoami         # confirm
```

The free tier ships 9 GB of DB across 500 databases — comfortably oversized for the calibration-research scope.

### 3. Create the database

```bash
turso db create omytea-personal-console --location lhr
# pick a location near your users: lhr (London), iad (US east),
# sin (Singapore), nrt (Tokyo) — see `turso db locations` for all.
```

### 4. Get the connection URL + token

```bash
# URL:
turso db show omytea-personal-console --url
# → libsql://omytea-personal-console-<your-org>.turso.io

# Token (paste output below into secrets):
turso db tokens create omytea-personal-console
# → eyJhbGciOi...  (long JWT)
```

### 5. Paste into Streamlit Cloud secrets

Go to https://share.streamlit.io/ → `omytea-personal-console` row → ⋮ → **Settings** → **Secrets**. Paste:

```toml
[turso]
url = "libsql://omytea-personal-console-<your-org>.turso.io"
auth_token = "eyJhbGciOi..."
```

Click **Save**. Streamlit Cloud restarts the app. After ~110s the console is writing to Turso.

### 6. Verify durability

1. Open the live demo and make a prediction.
2. Note the prediction ID.
3. Trigger a manual Reboot from `share.streamlit.io` ⋮ → Reboot.
4. Wait for the redeploy (~110s) and revisit the live demo.
5. Open `More → Measurement update`, paste the prediction ID into the "Have a prediction ID? Paste it here" expander — the prediction loads, confirming the row survived the redeploy.

If it doesn't load: check the Streamlit Cloud logs for a line like `[storage] WARNING: OMYTEA_TURSO_URL is set but neither libsql_experimental nor libsql is installed`. That means the wheel didn't install; verify `libsql-experimental` is in `requirements.txt` (it is, as of iter 44).

---

## Local dev

For local development just leave the env vars unset — the console falls back to the local SQLite at `~/.omytea-personal-console/predictions.db`. Tests pass either way.

If you want to point a local checkout at Turso for an integration sanity check:

```bash
export OMYTEA_TURSO_URL='libsql://omytea-personal-console-<your-org>.turso.io'
export OMYTEA_TURSO_AUTH_TOKEN='<your-token>'
streamlit run app.py
```

---

## Privacy posture (for beta testers)

The beta consent banner already says "Data is stored on the demo server (not your device); see Privacy for what's collected and how to delete it." With Turso wired in, "demo server" is now Turso's edge (a US/EU region you pick). The PRIVACY_POLICY.md should be updated to mention this when Turso goes live. Until then the existing banner copy is technically accurate (Turso *is* the demo server).

If a beta tester asks for data deletion: run

```bash
turso db shell omytea-personal-console \
  "DELETE FROM predictions WHERE user_id = '<their-handle>'; \
   DELETE FROM measurement_updates WHERE user_id = '<their-handle>';"
```

For complete account erasure, also clear `branch_drilldowns`, `entitlements`, `preorder_interest`, `categories`, `prediction_labels` by `prediction_id`.

---

## Cost

Free tier is **9 GB / 500 dbs / 1 billion row-reads per month / 25 million row-writes per month**. The Console writes ~50KB per prediction + ~1KB per measurement; even 10,000 beta predictions stays comfortably under any limit. Re-evaluate at GA.

---

## Rollback

Remove the `[turso]` block from Streamlit Cloud secrets → app restarts → falls back to local SQLite (ephemeral). No code changes needed.

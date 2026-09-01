# Local SEO Audit Engine

A small web service that generates a free, instant local-SEO snapshot for any
business website — the same report format used for outreach.

- `GET /` — a simple form to try it by hand
- `GET /audit?url=...&name=...&city=...` — returns the full HTML report
- `GET /audit.json?url=...&name=...&city=...` — returns the raw JSON findings
- `GET /health` — health check (used by the hosting platform)

Once this is deployed, `https://your-app.onrender.com/audit?url=https://somebusiness.com&name=Some+Business&city=Malvern,+PA`
generates a report for *any* business in seconds — no manual research needed.

---

## Deploy it — step by step (no coding required from here)

This assumes you have **neither** a GitHub account nor a Render account yet.
Both are free to create. Total time: about 15 minutes.

### Step 1 — Create a GitHub account
1. Go to **github.com/join** and sign up (free).
2. Verify your email when it asks.

### Step 2 — Create a new repository for this project
1. Once logged in, click the **+** icon (top right) → **New repository**.
2. Name it `seo-audit-engine` (or anything you like).
3. Set it to **Public** (Render's free tier needs this) or Private if you
   upgrade later.
4. Click **Create repository** — leave everything else as default.

### Step 3 — Upload these files to the repository
You do **not** need to install git or use the command line.
1. On your new (empty) repository page, click **uploading an existing file**
   (a link GitHub shows on empty repos).
2. Drag in every file from this folder: `app.py`, `audit_engine.py`,
   `report_generator.py`, `requirements.txt`, `render.yaml`, `.gitignore`,
   and this `README.md`.
3. Scroll down and click **Commit changes**.

### Step 4 — Create a Render account
1. Go to **render.com** and click **Get Started**.
2. Sign up using **"Sign up with GitHub"** — this is the easiest option
   since it connects the two automatically.
3. Authorize Render to access your GitHub account when prompted.

### Step 5 — Deploy the service
1. In the Render dashboard, click **New +** → **Web Service**.
2. Choose **Build and deploy from a Git repository**, then select the
   `seo-audit-engine` repo you just created.
3. Render should auto-detect the settings from `render.yaml`. If it asks you
   to fill them in manually instead, use:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
4. Click **Create Web Service**. Render will install dependencies and start
   the app — this takes a few minutes the first time. Watch the deploy log;
   when it says the service is **live**, you're done.
5. Render gives you a URL like `https://seo-audit-engine-xxxx.onrender.com`.
   That's your live audit engine.

### Step 6 — Test it
Open in your browser:
```
https://YOUR-APP-NAME.onrender.com/
```
You'll see a simple form. Enter any business website and city, click
**Run Audit**, and you'll get a full report — generated live, for real,
against any actual site.

---

## A note on the free tier

Render's free plan "spins down" the service after periods of inactivity, so
the first request after a while can take ~30-60 seconds to wake back up.
That's fine for generating audits by hand for outreach. If you later want it
to be instant (e.g. an embedded tool on a landing page), upgrade to a paid
Render plan (~$7/month).

## What changed from the earlier prototype

The original `audit_engine.py` was built and tested logically in a sandbox
that couldn't make outbound requests to arbitrary websites — every report so
far was hand-researched via search instead. This deployment removes that
limitation entirely: once live on Render, the exact same code can fetch and
score any real website directly, automatically, in a couple of seconds.

# Deployment guide

The live deployment is **compulsory** (rulebook section 6), and a video of a locally
running app does not replace it. Allow about 20 minutes, and do it well before the
9:00 PM IST freeze.

## 1. MongoDB Atlas (once)

1. Create a free **M0** cluster at <https://cloud.mongodb.com>.
2. **Database Access**: add a user with a password (letters and digits only avoids
   URL-encoding trouble). Role: *Read and write to any database*.
3. **Network Access**: add `0.0.0.0/0`. Free hosting providers use changing IP
   addresses, so a fixed allow-list will not work. Fine for a hackathon; mention it
   as a known limitation if asked.
4. **Connect → Drivers → Python**: copy the `mongodb+srv://...` string and put the
   password in it.
5. Locally: put it in `.env` as `MONGODB_URI=...`, then run:

```bash
python -m guard doctor
```

All lines must say PASS. If the connection times out, campus Wi-Fi may be blocking
port 27017, so try a phone hotspot.

## 2. Render (recommended, free)

1. Push this repo to GitHub (it must be accessible to the judges anyway).
2. <https://dashboard.render.com> → **New → Blueprint** → select the repo. Render reads
   `render.yaml`.
3. When asked, paste the Atlas connection string as `MONGODB_URI`.
4. Wait for the build, then open `https://<name>.onrender.com/api/health`; it should
   show `"ok": true` and the MongoDB version.
5. Open the root URL. On first start the app creates the collections, validators and
   indexes and loads the demo data automatically.

No Blueprint? Use **New → Web Service** instead:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn guard.api:app --host 0.0.0.0 --port $PORT --workers 1`
- Environment: `MONGODB_URI`, `PYTHON_VERSION=3.12.7`

### Render free-tier caveats

- The service **sleeps after 15 minutes idle**, and the first request then takes about
  50 seconds. Open the URL a minute before the judges or your demo.
- Keep `--workers 1`: running-run bookkeeping lives in process memory.

## 3. Alternatives

The `Dockerfile` works on Railway, Fly.io, Koyeb or Google Cloud Run (set `MONGODB_URI`
and `PORT`). The `Procfile` works on Heroku-style hosts. Neither has been tested yet,
so prefer Render.

## 4. Before submitting (check every item)

- [ ] `/api/health` returns `ok: true` on the public URL
- [ ] Live label in the header says **live: change stream** (not polling)
- [ ] Full demo works in the browser: Run v1 → Run v2 (NOT SAFE) → Run v3 (RISKY) →
      Run v3 with tc03, tc05, tc09 timeouts (INCONCLUSIVE)
- [ ] "Send result without run_id" says **rejected** (validator active on Atlas)
- [ ] "Show query plan" says **IXSCAN**
- [ ] Click **Reset run history** so judges start clean, or leave a finished demo
      history in place (decide as a team)
- [ ] The `.env` file is NOT in the GitHub repo

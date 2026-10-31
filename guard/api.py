"""HTTP API and live event stream for the dashboard (docs/SPEC.md sections 11-12).

Run locally:  uvicorn guard.api:app --reload
Every demo action is available here, because the deployed page is what judges test.

Live updates use a MongoDB change stream on the database, forwarded to the browser as
Server-Sent Events. If change streams are unavailable (e.g. a standalone mongod), the
stream says so and the page falls back to polling the REST endpoints.
"""
import asyncio
import json
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from pymongo import DESCENDING

from guard import compare as cmp
from guard import config
from guard import db as dbmod
from guard import demo as demomod
from guard import gitmeta, runner
from guard.seed import seed

LIVE_DELAY_S = 0.2           # pause between test cases so rows visibly stream in (30 cases ≈ 6 s)
MAX_CONCURRENT_RUNS = 3      # the deployment is public; keep it from being flooded
HEARTBEAT_S = 15             # keeps proxies from closing an idle SSE connection

_active_runs: set[str] = set()
_active_lock = threading.Lock()


def get_db():
    return dbmod.get_db()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Make a deployment usable immediately: schema + demo data, kept in sync with data/*.json.
    try:
        database = get_db()
        dbmod.ensure_schema(database)
        seed(database)  # idempotent upsert: picks up edits to data/*.json on every start
    except Exception as e:  # never block startup; /api/health reports the problem
        print(f"[startup] database not ready: {e}")
    yield


app = FastAPI(title="PARAKH", lifespan=lifespan)


def _json(data):
    return jsonable_encoder(data)


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    try:
        database = get_db()
        version = ".".join(map(str, dbmod.server_version(database)))
        return {"ok": True, "mongodb": version, "db": config.DB_NAME,
                "percentile": dbmod.supports_percentile(database),
                "project_id": config.PROJECT_ID}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/versions")
def versions():
    docs = get_db()[config.PROMPT_VERSIONS].find({"project_id": config.PROJECT_ID}).sort("version", 1)
    return _json(list(docs))


@app.get("/api/test-cases")
def test_cases():
    docs = get_db()[config.TEST_CASES].find({"project_id": config.PROJECT_ID}).sort("_id", 1)
    return _json(list(docs))


@app.get("/api/runs")
def runs(limit: int = 20):
    docs = get_db()[config.EVAL_RUNS].find({"project_id": config.PROJECT_ID}) \
        .sort("started_at", DESCENDING).limit(min(limit, 100))
    return _json(list(docs))


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    database = get_db()
    run = database[config.EVAL_RUNS].find_one({"_id": run_id})
    if run is None:
        raise HTTPException(404, f"run '{run_id}' not found")
    results = database[config.EVAL_RESULTS].find({"run_id": run_id}).sort("test_case_id", 1)
    return _json({"run": run, "results": list(results)})


@app.get("/api/history")
def history(limit: int = 20):
    """Per-run pass rate, p95, cost and readiness score, oldest -> newest (for the chart)."""
    return _json(cmp.run_history(get_db(), limit=min(max(limit, 1), 50)))


@app.get("/api/diff")
def diff(baseline: str, candidate: str, test_case_id: str):
    """Baseline vs candidate output and checks for one test case."""
    try:
        return _json(cmp.case_diff(get_db(), baseline, candidate, test_case_id))
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/explain/{run_id}")
def explain(run_id: str):
    """Query plan for "all results of run X": shows the index in use and docs examined."""
    return dbmod.explain_run_lookup(get_db(), run_id)


@app.get("/api/comparisons")
def comparisons(limit: int = 10):
    docs = get_db()[config.COMPARISONS].find({"project_id": config.PROJECT_ID}) \
        .sort("created_at", DESCENDING).limit(min(limit, 50))
    return _json(list(docs))


@app.get("/api/comparisons/latest")
def latest_comparison():
    doc = get_db()[config.COMPARISONS].find_one(
        {"project_id": config.PROJECT_ID}, sort=[("created_at", DESCENDING)])
    return _json(doc)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    version: str
    simulate_timeouts: list[str] = Field(default_factory=list)
    wait: bool = False  # True: run synchronously and return the finished run (CI / tests)


class CompareRequest(BaseModel):
    baseline: str   # version name (latest finished run) or run ID
    candidate: str


def _background_run(run_id: str, version: str, timeouts: set[str]) -> None:
    database = get_db()
    try:
        runner.run_eval(database, version, simulate_timeouts=timeouts,
                        run_id=run_id, delay_s=LIVE_DELAY_S)
    except Exception as e:
        runner.fail_run(database, run_id, f"{type(e).__name__}: {e}")
    finally:
        with _active_lock:
            _active_runs.discard(run_id)


@app.post("/api/runs")
def start_run(req: RunRequest):
    database = get_db()
    timeouts = set(req.simulate_timeouts)
    try:
        if req.wait:
            return _json(runner.run_eval(database, req.version, simulate_timeouts=timeouts,
                                          git=gitmeta.detect_cached()))
        with _active_lock:
            if len(_active_runs) >= MAX_CONCURRENT_RUNS:
                raise HTTPException(429, "too many runs in progress, try again shortly")
            run_id = runner.start_run(database, req.version, git=gitmeta.detect_cached())
            _active_runs.add(run_id)
    except runner.VersionNotFound as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    threading.Thread(target=_background_run, args=(run_id, req.version, timeouts),
                     daemon=True).start()
    return {"run_id": run_id, "status": "running"}


@app.post("/api/compare")
def compare(req: CompareRequest):
    try:
        doc = cmp.compare_runs(get_db(), req.baseline, req.candidate)
    except cmp.RunNotFound as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _json({**doc, "exit_code": cmp.exit_code(doc["verdict"])})


@app.post("/api/demo/duplicate")
def demo_duplicate(run_id: str | None = None):
    try:
        return demomod.replay_duplicate(get_db(), run_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/demo/incomplete")
def demo_incomplete():
    return demomod.insert_incomplete(get_db())


@app.post("/api/demo/reset")
def demo_reset():
    with _active_lock:
        if _active_runs:
            raise HTTPException(409, "a run is in progress; wait for it to finish")
    dbmod.reset_runs(get_db())
    return {"ok": True}


# ---------------------------------------------------------------------------
# Live stream (change streams -> Server-Sent Events)
# ---------------------------------------------------------------------------

WATCHED = {config.EVAL_RESULTS: "result", config.EVAL_RUNS: "run",
           config.COMPARISONS: "comparison"}


def change_stream_pipeline() -> list[dict]:
    return [{"$match": {
        "ns.coll": {"$in": list(WATCHED)},
        "operationType": {"$in": ["insert", "update", "replace"]},
    }}]


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(jsonable_encoder(data))}\n\n"


def _watch_thread(loop, queue: asyncio.Queue, stop: threading.Event) -> None:
    """Blocking change-stream loop in a worker thread; hands events to the async side."""
    def put(item):
        loop.call_soon_threadsafe(queue.put_nowait, item)
    try:
        with get_db().watch(change_stream_pipeline(), full_document="updateLookup",
                            max_await_time_ms=1000) as stream:
            put(("mode", {"mode": "change_stream"}))
            while not stop.is_set():
                change = stream.try_next()
                if change is None or not change.get("fullDocument"):
                    continue
                doc = change["fullDocument"]
                if doc.get("project_id") != config.PROJECT_ID:
                    continue
                put((WATCHED[change["ns"]["coll"]], doc))
    except Exception as e:
        put(("mode", {"mode": "polling", "reason": f"{type(e).__name__}: {e}"}))


@app.get("/api/stream")
async def stream(request: Request):
    """Server-Sent Events: `result`, `run` and `comparison` events as MongoDB writes them.
    The browser first loads current state over REST, then de-duplicates stream events by
    _id (avoids the race where results land before the stream is open)."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    stop = threading.Event()
    threading.Thread(target=_watch_thread, args=(loop, queue, stop), daemon=True).start()

    async def events():
        try:
            while not await request.is_disconnected():
                try:
                    kind, data = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_S)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield _sse(kind, data)
                if kind == "mode" and data["mode"] == "polling":
                    return
        finally:
            stop.set()

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def index():
    page = config.WEB_DIR / "index.html"
    if page.exists():
        return FileResponse(page)
    return HTMLResponse("<h1>PARAKH</h1><p>Dashboard not built yet. "
                        "API docs: <a href='/docs'>/docs</a></p>")

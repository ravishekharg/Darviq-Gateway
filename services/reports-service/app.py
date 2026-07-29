"""reports-service

Third routing target for the gateway demo. Includes one intentionally slow
endpoint (/slow, reached through the gateway as /api/reports/slow) used to
exercise Kong's upstream timeouts and to give the rate-limiting plugin
something meaningful to throttle in the demo walkthrough in the README.
"""

import asyncio
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

SERVICE_NAME = "reports-service"

app = FastAPI(title=SERVICE_NAME)

REPORTS = [
    {"id": "rpt-2026-q1", "title": "Q1 Usage Report", "rows": 482},
    {"id": "rpt-2026-q2", "title": "Q2 Usage Report", "rows": 511},
]


@app.middleware("http")
async def add_upstream_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Upstream-Service"] = SERVICE_NAME
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME}


# Kong's route for this service (kong/kong.yml -> reports-route) has
# strip_path: true and matches /api/reports, so a client request to
# /api/reports arrives here as GET / - this service knows nothing about
# the /api prefix, which is deliberate: the gateway owns the public URL
# shape, not the upstream.
@app.get("/")
async def list_reports(request: Request):
    return {
        "service": SERVICE_NAME,
        "upstream": f"{SERVICE_NAME}:8000",
        "receivedPath": str(request.url.path),
        "count": len(REPORTS),
        "reports": REPORTS,
    }


@app.get("/slow")
async def slow_report(request: Request):
    """Intentionally sleeps ~5s to demonstrate Kong upstream timeouts and to
    give rate-limiting something to throttle in the README's curl walkthrough.
    Declared before /{report_id} so it isn't shadowed by that catch-all."""
    started = time.time()
    await asyncio.sleep(5)
    return {
        "service": SERVICE_NAME,
        "receivedPath": str(request.url.path),
        "message": "this endpoint deliberately took ~5s to respond",
        "elapsedSeconds": round(time.time() - started, 2),
    }


@app.get("/{report_id}")
async def get_report(report_id: str):
    report = next((r for r in REPORTS if r["id"] == report_id), None)
    if not report:
        return JSONResponse(
            status_code=404,
            content={"service": SERVICE_NAME, "error": "report not found"},
        )
    return {"service": SERVICE_NAME, "report": report}

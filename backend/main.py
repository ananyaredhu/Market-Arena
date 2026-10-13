"""FastAPI app. Person C owns this file; it only mounts the routers.

Run: `make api`  (MOCK=1 LLM_MODE=mock). Docs at http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import council_routes, sim_routes
from backend.common.mock import mock_enabled
from backend.orchestrator import routes as orchestrator_routes
from backend.telegram import routes as telegram_routes

app = FastAPI(title="Market Arena")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (sim_routes.router, council_routes.router, orchestrator_routes.router, telegram_routes.router):
    app.include_router(r)


@app.get("/health")
def health():
    return {"status": "ok", "mock": mock_enabled()}

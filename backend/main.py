import os
import logging

from fastapi import FastAPI

from api.middleware import setup_middleware
from api.routes.products import router as products_router
from api.routes.inventory import router as inventory_router
from api.routes.payment import router as payment_router
from api.routes.loyalty import router as loyalty_router
from api.routes.fulfillment import router as fulfillment_router
from startup import run_startup

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Retail AI Agent API",
    description="Backend API for the Retail AI Agent — product search, inventory, payment, loyalty & fulfillment.",
    version="0.4.0",
)

# ── Middleware ────────────────────────────────────────────────────────────────
setup_middleware(app)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(products_router, prefix="/products", tags=["Products"])
app.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
app.include_router(payment_router, prefix="/payment", tags=["Payment"])
app.include_router(loyalty_router, prefix="/loyalty", tags=["Loyalty"])
app.include_router(fulfillment_router, prefix="/fulfillment", tags=["Fulfillment"])


# ── Root & Health ────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {"message": "Retail AI Agent API", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "retail-ai-agent-backend"}


# ── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    run_startup()


# ── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

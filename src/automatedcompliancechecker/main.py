from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from automatedcompliancechecker.routers import compliance
from automatedcompliancechecker.utils.lifespan import lifespan

app = FastAPI(
    title="GDPR Compliance Checker API",
    description="Automated GDPR/DSGVO compliance analysis for contracts and privacy policies.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compliance.router, prefix="/api/v1", tags=["compliance"])


@app.get("/health")
def health():
    return {"status": "ok"}

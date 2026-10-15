"""Foundation-only FastAPI application. No handoff business endpoints yet."""

from fastapi import FastAPI, Response, status

app = FastAPI(
    title="Handoff Hub Multichannel",
    version="0.1.0-dev",
    description="Foundation-only API. Handoff operations are not yet available.",
)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    """Process liveness, not dependency availability."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def readiness(response: Response) -> dict[str, str]:
    """Fail closed until persistent storage/auth and workers are ready."""
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready", "reason": "critical_dependencies_not_configured"}

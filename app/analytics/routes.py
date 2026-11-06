"""Analytics and Live Telemetry endpoints."""

from fastapi import APIRouter
from app.db.database import fetch_all, fetch_one

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics & Telemetry"])


@router.get("/overview")
async def get_overview():
    """Get high-level platform metrics: total tokens, estimated $ saved, request counts."""
    summary = await fetch_one(
        """
        SELECT 
            COUNT(*) as total_requests,
            COALESCE(SUM(total_tokens), 0) as total_tokens,
            COALESCE(SUM(savings_usd), 0.0) as total_savings_usd,
            COALESCE(AVG(duration_ms), 0.0) as avg_duration_ms
        FROM request_logs
        """
    )
    provider_counts = await fetch_all(
        """
        SELECT provider, COUNT(*) as count, SUM(total_tokens) as tokens
        FROM request_logs
        GROUP BY provider
        """
    )

    return {
        "total_requests": summary["total_requests"] if summary else 0,
        "total_tokens": summary["total_tokens"] if summary else 0,
        "total_savings_usd": round(summary["total_savings_usd"], 2) if summary else 0.0,
        "avg_duration_ms": round(summary["avg_duration_ms"], 1) if summary else 0.0,
        "providers_breakdown": provider_counts,
    }


@router.get("/logs")
async def get_logs(limit: int = 50):
    """Get recent request logs for the telemetry feed."""
    rows = await fetch_all(
        """
        SELECT id, api_key_name, provider, model, status_code, duration_ms, total_tokens, savings_usd, created_at
        FROM request_logs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (min(limit, 100),),
    )
    return rows

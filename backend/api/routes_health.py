from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"ok": True, "app": "elastitune", "version": "0.1.0"}

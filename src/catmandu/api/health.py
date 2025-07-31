from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Simple health check endpoint for Docker health checks."""
    return {"status": "healthy"}

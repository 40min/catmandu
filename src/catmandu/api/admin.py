from fastapi import APIRouter, Depends

from catmandu.api.dependencies import get_cattackle_registry
from catmandu.core.services.registry import CattackleRegistry

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reload")
async def reload_cattackles(
    cattackle_registry: CattackleRegistry = Depends(get_cattackle_registry),
):
    """Triggers a re-scan of the cattackles directory."""
    found_count = cattackle_registry.scan()
    return {"status": "reloaded", "found": found_count}

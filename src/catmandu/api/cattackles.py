from typing import List

from fastapi import APIRouter, Depends

from catmandu.api.dependencies import get_cattackle_registry
from catmandu.core.infrastructure.registry import CattackleRegistry
from catmandu.core.models import CattackleConfig

router = APIRouter()


@router.get("/cattackles", response_model=List[CattackleConfig])
async def list_cattackles(
    cattackle_registry: CattackleRegistry = Depends(get_cattackle_registry),
):
    """Lists all discovered cattackles."""
    return cattackle_registry.get_all()

from typing import List

from fastapi import APIRouter, Depends

from catmandu.core.models import CattackleConfig
from catmandu.core.services.registry import CattackleRegistry

router = APIRouter()


@router.get("/cattackles", response_model=List[CattackleConfig])
async def list_cattackles(
    cattackle_registry: CattackleRegistry = Depends(CattackleRegistry),
):
    """Lists all discovered cattackles."""
    return cattackle_registry.get_all()

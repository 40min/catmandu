from typing import List

from fastapi import APIRouter

from catmandu.core.models import CattackleConfig
from catmandu.core.services.registry import cattackle_registry

router = APIRouter()


@router.get("/cattackles", response_model=List[CattackleConfig])
async def list_cattackles():
    """Lists all discovered cattackles."""
    return cattackle_registry.get_all()

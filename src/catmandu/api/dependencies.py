from fastapi import Request

from catmandu.core.services.registry import CattackleRegistry


def get_cattackle_registry(request: Request) -> CattackleRegistry:
    """Returns the cattackle registry instance from the app state."""
    return request.app.state.cattackle_registry

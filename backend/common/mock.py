"""MOCK=1 switch shared by all routers: routes return fixtures until the real code replaces them."""
import os

from fastapi import HTTPException


def mock_enabled() -> bool:
    return os.getenv("MOCK", "1") == "1"


def not_built(route: str) -> HTTPException:
    """Raised by a stub route when MOCK=0 and the real implementation is not written yet."""
    return HTTPException(status_code=501, detail=f"{route} is not implemented yet (set MOCK=1)")

"""Session management endpoints.

POST   /sessions              create session
GET    /sessions/{id}         fetch session snapshot
DELETE /sessions/{id}         end session
"""

from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["sessions"])


# TODO: Implement route handlers

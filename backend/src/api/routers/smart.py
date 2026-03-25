"""SM-J Smart AI Processing — DEPRECATED.

All functionality has moved to POST /api/v1/pipeline/process/{batch_id}.
This module is kept temporarily so that main.py imports don't break; the router
is no longer mounted.  Remove once main.py has been cleaned up.
"""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/smart", tags=["Smart AI Processing (deprecated)"])


"""Deprecated authentication router.

The canonical JSON auth endpoints are implemented in app.api.auth and mounted by app.main.
This module intentionally exports no duplicate login route.
"""
from fastapi import APIRouter
router = APIRouter()

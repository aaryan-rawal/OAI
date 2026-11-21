from fastapi import APIRouter, HTTPException
from app.domain.routes import ROUTES, get_route, verify_route

router = APIRouter(tags=["routes"])

@router.get("/routes")
async def list_routes():
    """Return illustrative corridor definitions; these are not verified road routes."""
    return ROUTES

@router.get("/routes/{route_id}")
async def read_route(route_id: str):
    route = get_route(route_id)
    if not route:
        raise HTTPException(404, "Route not found.")
    return route

@router.post("/routes/{route_id}/verify")
async def verify_selected_route(route_id: str):
    """Verify the selected corridor against the configured OSRM road network."""
    try:
        route = verify_route(route_id)
    except KeyError:
        raise HTTPException(404, "Route not found.")
    return route

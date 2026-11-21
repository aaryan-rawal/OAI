"""Compatibility import for Alembic and older modules."""
from app.models import Base, User, ManualCargo, MatchRun, Shipment, FleetDriver, FleetContainer
__all__ = ["Base", "User", "ManualCargo", "MatchRun", "Shipment", "FleetDriver", "FleetContainer"]

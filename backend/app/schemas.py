"""Request/response schemas shared by the HTTP API."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from app.domain.india_vehicle_limits import assess_india_gvw

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Place(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

class RegisterIn(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=24)
    password: str = Field(min_length=8, max_length=128)
    account_type: Literal["client", "organization_owner", "organization_admin", "driver"] = "client"
    organization_id: str | None = None
    organization_name: str | None = Field(default=None, max_length=200)
    @model_validator(mode="after")
    def require_org_name(self):
        if self.account_type == "organization_owner" and not (self.organization_name or "").strip():
            raise ValueError("Organization name is required for owner accounts.")
        if self.account_type in {"organization_admin", "driver"} and not self.organization_id:
            raise ValueError("Select a company before registering this account type.")
        digits = "".join(ch for ch in self.phone if ch.isdigit())
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Enter a valid phone number including country code where applicable.")
        self.phone = ("+91" + digits) if len(digits) == 10 else ("+" + digits)
        return self

class RegisterStartIn(RegisterIn):
    pass

class RegisterVerifyIn(StrictModel):
    challenge_id: str
    otp: str = Field(min_length=6, max_length=6)

class LoginIn(StrictModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)

class ManualCargoIn(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=80)
    weight_kg: float = Field(gt=0)
    rate_inr: float | None = Field(default=None, ge=0)
    pickup: Place
    drop: Place
    pickup_window_start: str | None = None
    pickup_window_end: str | None = None
    loading_minutes: float | None = Field(default=None, ge=0)
    unloading_minutes: float | None = Field(default=None, ge=0)
    waiting_minutes: float | None = Field(default=None, ge=0)
    hazardous: bool = False
    hazardous_description: str | None = Field(default=None, max_length=1000)

class AxleGroupIn(StrictModel):
    kind: Literal["single_1_tyre", "single_2_tyres", "single_4_tyres", "tandem_rigid", "tandem_puller", "tridem_rigid", "modular_axle_row"]
    count: int = Field(default=1, ge=1, le=20)

class TruckIn(StrictModel):
    vehicle_class: str
    body_type: Literal["open_body", "closed_body", "flatbed_trailer", "container_carrier", "tanker", "reefer", "tipper"]
    max_payload_kg: float = Field(gt=0)
    available_payload_kg: float = Field(ge=0)
    available_volume_m3: float | None = Field(default=None, gt=0)
    baseline_active_minutes: float | None = Field(default=None, gt=0)
    location: Place
    available_from: str
    handling_equipment: list[str] = []
    vehicle_name: str | None = Field(default=None, max_length=120)
    min_payload_kg: float | None = Field(default=None, ge=0)
    legal_max_gvw_kg: float | None = Field(default=None, gt=0)
    vehicle_gvw_kg: float | None = Field(default=None, gt=0)
    length_m: float | None = Field(default=None, gt=0)
    width_m: float | None = Field(default=None, gt=0)
    height_m: float | None = Field(default=None, gt=0)
    axle_count: int | None = Field(default=None, ge=2, le=20)
    vehicle_form: Literal["rigid", "semi_articulated"] | None = None
    axle_groups: list[AxleGroupIn] = []
    type_approved_gvw_kg: float | None = Field(default=None, gt=0)
    tyre_capacity_gvw_kg: float | None = Field(default=None, gt=0)
    pneumatic_suspension: bool = False
    legal_load_assessment: dict | None = None
    permitted_states: list[str] = []
    restricted_cities: list[str] = []
    city_access_windows: list[dict] = []
    @model_validator(mode="after")
    def validate_vehicle_limits(self):
        if self.min_payload_kg is not None and self.min_payload_kg > self.max_payload_kg:
            raise ValueError("Minimum payload cannot exceed maximum payload.")
        if self.vehicle_form:
            assessment = assess_india_gvw(vehicle_form=self.vehicle_form,
                axle_groups=[x.model_dump() for x in self.axle_groups],
                type_approved_gvw_kg=self.type_approved_gvw_kg,
                tyre_capacity_gvw_kg=self.tyre_capacity_gvw_kg,
                pneumatic_suspension=self.pneumatic_suspension)
            self.legal_load_assessment = {"status": assessment.status, "maximum_gvw_kg": assessment.maximum_gvw_kg,
                "axle_capacity_kg": assessment.axle_capacity_kg, "reasons": list(assessment.reasons),
                "source": "MoRTH S.O. 3467(E) 16-07-2018 as amended by S.O. 3881(E) 06-08-2018"}
            self.legal_max_gvw_kg = assessment.maximum_gvw_kg
        if self.vehicle_gvw_kg is not None and self.legal_max_gvw_kg is not None and self.vehicle_gvw_kg > self.legal_max_gvw_kg:
            raise ValueError("Vehicle GVW exceeds the configured legal reference cap.")
        return self
    @model_validator(mode="after")
    def payload_within_vehicle_limit(self):
        if self.available_payload_kg > self.max_payload_kg:
            raise ValueError("Available payload cannot exceed maximum payload.")
        return self

class CostOverrides(StrictModel):
    diesel_inr_per_l: float | None = Field(default=None, gt=0)
    mileage_km_per_l: float | None = Field(default=None, gt=0)
    toll_inr_per_km: float | None = Field(default=None, ge=0)
    driver_inr_per_hour: float | None = Field(default=None, ge=0)
    handling_fee_inr: float | None = Field(default=None, ge=0)

class MatchIn(StrictModel):
    route_id: str
    route_version: int = Field(ge=1)
    truck: TruckIn
    off_route_enabled: bool = False
    cost_overrides: CostOverrides | None = None

class AcceptIn(StrictModel):
    run_id: str
    candidate_id: str
    route_id: str
    route_version: int
    snapshot: dict | None = None
    origin: Place | None = None
    destination: Place | None = None
    route_polyline: list[dict] | None = None
    route_name: str | None = None

class DriverIn(StrictModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    license_number: str | None = Field(default=None, max_length=40)
    date_of_birth: str | None = None
    address: str | None = Field(default=None, max_length=1000)

class ContainerIn(StrictModel):
    registration_number: str = Field(min_length=3, max_length=40)
    truck: TruckIn
    driver_id: str | None = None

class AssignmentIn(StrictModel):
    driver_id: str | None = None
    container_id: str | None = None
    @model_validator(mode="after")
    def both_or_none(self):
        if bool(self.driver_id) != bool(self.container_id):
            raise ValueError("Choose both a driver and a container, or clear both assignments.")
        return self


from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["functional", "performance"]

    description: str = Field(
        min_length=5,
        max_length=300
    )
    
class SystemIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]

    system_name: str = Field(
        min_length=3,
        max_length=100
    )

    system_type: Literal[
        "charging_system",
        "powertrain",
        "motor_controller",
        "thermal_management",
        "vehicle_control_unit",
        "other"
    ]

    description: str = Field(
        min_length=10,
        max_length=500
    )

    components: list[str] = Field(
        max_length=10
    )

    requirements: list[Requirement] = Field(
        min_length=1,
        max_length=20
    )

    constraints: list[str] = Field(
        max_length=10
    )

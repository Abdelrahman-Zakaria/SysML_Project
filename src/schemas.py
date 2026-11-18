from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class ProjectType(str, Enum):
    EMBEDDED = "embedded"
    SOFTWARE = "software"
    AI = "AI"
    OTHER = "other"


class ProjectIntent(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        strict=True
    )

    schema_version: str

    project_name: str = Field(
        min_length=3,
        max_length=80
    )

    project_type: ProjectType

    main_components: list[str] = Field(
        min_length=1
    )

    objectives: list[str] = Field(
        min_length=1
    )
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ItemIdInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: int = Field(gt=0)


class CheckConditionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: int = Field(gt=0)
    condition: Literal["exists", "available", "defined"]

    
class ListAvailableItemsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
from pydantic import BaseModel, Field


class PositiveInt(BaseModel):
    value: int = Field(strict=True, gt=0)  # Positive integer

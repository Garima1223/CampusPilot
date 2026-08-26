from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class GrievanceCreate(BaseModel):
    category: str
    description: str


class BookRequestCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    book_id: str = Field(alias="bookId")

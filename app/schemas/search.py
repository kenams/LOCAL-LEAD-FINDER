"""
Search schemas
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class SearchRequest(BaseModel):
    locations: List[str]
    categories: List[str]
    limit_per_location: int = 10
    language: str = "fr"

class SearchRunBase(BaseModel):
    locations: str
    categories: str
    limit_per_location: int
    language: str

class SearchRun(SearchRunBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: str
    completed_at: Optional[str]
    prospects_found: int
    status: str
    error_message: Optional[str]
    diagnostics_json: Optional[str]

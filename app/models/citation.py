from pydantic import BaseModel
from typing import Optional

class Citation(BaseModel):
    source: str
    location: Optional[str] = None
    score: Optional[float] = None

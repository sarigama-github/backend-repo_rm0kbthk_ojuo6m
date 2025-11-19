"""
Database Schemas for Shadow Sprint

Each Pydantic model corresponds to a MongoDB collection (lowercased class name).
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class PlayerSettings(BaseModel):
    player_id: str = Field(..., description="Client-provided id stored in localStorage")
    volume: bool = Field(True)
    vibration: bool = Field(True)
    language: Literal["en", "es"] = Field("es")

class InputSegment(BaseModel):
    start_ms: int
    end_ms: int
    kind: Literal["tap", "hold"]

class GhostRecord(BaseModel):
    player_id: str
    level: int = Field(..., ge=1, le=15)
    time_ms: int = Field(..., ge=0)
    inputs: List[InputSegment]

class ProgressRecord(BaseModel):
    player_id: str
    unlocked_upto: int = Field(1, ge=1, le=15)

# Example existing schemas kept for reference (not used by the app)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True

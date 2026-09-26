"""Data contracts. Claude references perception IDs (T# text tokens, C# circles) instead of guessing pixels.
Kept flat (few nullable fields) so it fits structured-output schema limits."""
from typing import List, Optional

from pydantic import BaseModel, Field


class Characteristic(BaseModel):
    balloon: int = Field(description="Balloon number read on the drawing; 0 if the drawing has no balloon for it")
    circle: str = Field(description="C# ID of its balloon circle, or '' if none")
    tokens: List[str] = Field(description="T# IDs of the text tokens that make up this requirement")
    box: List[int] = Field(description="[x0,y0,x1,y1] 0-1000, ONLY when tokens is empty; else []")
    name: str = Field(description="Short human-readable feature name, e.g. 'Overall Length'")
    notation: str = Field(description="Exact engineering notation as printed")
    type: str = Field(description="Linear, Diameter, Radius, Angle, Chamfer, Thread, Surface Finish, GD&T, Note, Basic")
    nominal: Optional[float]
    upper: Optional[float] = Field(description="Signed upper tolerance")
    lower: Optional[float] = Field(description="Signed lower tolerance")
    unit: str
    qty: int
    gdt: str = Field(description="GD&T characteristic, e.g. 'Position Ø0.35 Ⓜ | A | B'; '' if not GD&T")
    designator: str = Field(description="Key/Critical/Major/Minor ONLY if marked on the drawing, else ''")
    tool: str = Field(description="Inspection device, e.g. Caliper, Micrometer, Bore Gauge, CMM, Profilometer, Thread Gauge, Visual")
    confidence: float
    issue: str = Field(description="Short reason (<= 15 words) if a human must check this; '' if certain")


class DrawingInfo(BaseModel):
    part_number: str
    part_name: str
    drawing_number: str
    revision: str
    material: str
    material_spec: str
    general_tolerance: str


class Extraction(BaseModel):
    drawing: DrawingInfo
    characteristics: List[Characteristic]
    ignored_circles: List[str] = Field(description="C# IDs that are NOT balloons")
    warnings: List[str] = Field(description="Drawing-level problems (illegible areas, duplicate balloon numbers)")

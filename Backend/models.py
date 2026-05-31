from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    geometry: dict
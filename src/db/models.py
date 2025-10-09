from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class VideoAnalysisRequest(BaseModel):
    video_url: Optional[str] = None


class VideoAnalysisResponse(BaseModel):
    success: bool
    job_id: str
    ads_id: str
    video_id: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Simple request/response models
class SearchRequest(BaseModel):
    sentence: str


class SearchResponse(BaseModel):
    success: bool
    webset_id: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    saved_personas_count: Optional[int] = None
    error: Optional[str] = None

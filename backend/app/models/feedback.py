# backend/app/models/feedback.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FeedbackCreate(BaseModel):
    consultation_id: str
    rating: int = Field(..., ge=1, le=5)
    symptom_accuracy: int = Field(..., ge=1, le=5)
    recommendation_helpfulness: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "consultation_id": "123e4567-e89b-12d3-a456-426614174000",
                "rating": 5,
                "symptom_accuracy": 4,
                "recommendation_helpfulness": 5,
                "comment": "Very helpful consultation!"
            }
        }

class FeedbackResponse(BaseModel):
    id: str
    consultation_id: str
    rating: int
    symptom_accuracy: int
    recommendation_helpfulness: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "consultation_id": "123e4567-e89b-12d3-a456-426614174000",
                "rating": 5,
                "symptom_accuracy": 4,
                "recommendation_helpfulness": 5,
                "comment": "Very helpful consultation!",
                "created_at": "2024-03-11T10:00:00Z"
            }
        }


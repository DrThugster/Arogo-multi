# backend/app/models/consultation.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class LanguageCode(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    KANNADA = "kn"
    MALAYALAM = "ml"
    BENGALI = "bn"
    GUJARATI = "gu"
    MARATHI = "mr"
    PUNJABI = "pa"
    ASSAMESE = "as"
    BODO = "bo"
    MANIPURI = "mni"
    ODIA = "or"
    RAJASTHANI = "raj"
    URDU = "ur"

class ConsultationCreate(BaseModel):
    firstName: str = Field(..., min_length=1)
    lastName: str = Field(..., min_length=1)
    age: int = Field(..., gt=0, lt=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    height: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    email: EmailStr
    mobile: str = Field(..., min_length=10)
    preferred_language: LanguageCode = Field(default=LanguageCode.ENGLISH)
    interface_language: LanguageCode = Field(default=LanguageCode.ENGLISH)
    enable_auto_detection: bool = Field(default=True)
    medical_history: Optional[Dict[str, str]] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "firstName": "John",
                "lastName": "Doe",
                "age": 30,
                "gender": "male",
                "height": 175.0,
                "weight": 70.0,
                "email": "john.doe@example.com",
                "mobile": "1234567890",
                "preferred_language": "en",
                "interface_language": "en",
                "enable_auto_detection": True,
                "medical_history": {
                    "conditions": "None",
                    "medications": "None",
                    "allergies": "None"
                }
            }
        }

class MessageContent(BaseModel):
    original_text: str
    translated_text: Optional[str] = None
    source_language: LanguageCode
    target_language: Optional[LanguageCode] = None
    confidence_score: Optional[float] = None
    language_detected: Optional[bool] = None
    medical_terms: Optional[List[str]] = None

class Message(BaseModel):
    type: str = Field(..., pattern="^(user|bot)$")
    content: MessageContent
    audio_url: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict] = None

class ConsultationResponse(BaseModel):
    consultation_id: str
    user_details: ConsultationCreate
    status: str = Field(..., pattern="^(started|active|completed|terminated)$")
    language_preferences: Dict[str, str]
    messages: List[Message] = []
    created_at: datetime
    updated_at: datetime
    last_activity: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "consultation_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_details": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "age": 30,
                    "gender": "male",
                    "height": 175.0,
                    "weight": 70.0,
                    "email": "john.doe@example.com",
                    "mobile": "1234567890",
                    "preferred_language": "en",
                    "interface_language": "en"
                },
                "status": "active",
                "language_preferences": {
                    "preferred": "en",
                    "interface": "en",
                    "auto_detect": True
                },
                "messages": [
                    {
                        "type": "user",
                        "content": {
                            "original_text": "मुझे सिर दर्द है",
                            "translated_text": "I have a headache",
                            "source_language": "hi",
                            "target_language": "en",
                            "confidence_score": 0.95,
                            "language_detected": True,
                            "medical_terms": ["headache"]
                        },
                        "timestamp": "2024-03-14T10:00:00Z",
                        "metadata": {
                            "device_type": "mobile",
                            "input_method": "voice"
                        }
                    }
                ],
                "created_at": "2024-03-14T10:00:00Z",
                "updated_at": "2024-03-14T10:05:00Z",
                "last_activity": "2024-03-14T10:05:00Z"
            }
        }

class ConsultationUpdate(BaseModel):
    preferred_language: Optional[LanguageCode] = None
    interface_language: Optional[LanguageCode] = None
    enable_auto_detection: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|terminated)$")

    @validator('status')
    def validate_status(cls, v):
        if v not in ['active', 'completed', 'terminated']:
            raise ValueError('Invalid status')
        return v

class ConsultationSummary(BaseModel):
    consultation_id: str
    user_details: Dict
    symptoms: List[Dict]
    diagnosis: Dict
    recommendations: Dict
    language: LanguageCode
    created_at: datetime
    completed_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "consultation_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_details": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "age": 30,
                    "preferred_language": "en"
                },
                "symptoms": [
                    {
                        "name": "headache",
                        "severity": 7,
                        "duration": "2 days"
                    }
                ],
                "diagnosis": {
                    "condition": "Migraine",
                    "confidence": 0.85,
                    "severity": "moderate"
                },
                "recommendations": {
                    "immediate_action": "Rest in a dark room",
                    "medications": ["Paracetamol"],
                    "follow_up": "If persists > 24 hours"
                },
                "language": "en",
                "created_at": "2024-03-14T10:00:00Z",
                "completed_at": "2024-03-14T10:30:00Z"
            }
        }
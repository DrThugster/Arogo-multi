# backend/app/routes/consultation.py
from fastapi import APIRouter, HTTPException
from app.models.consultation import ConsultationCreate
from app.config.database import consultations_collection
from app.services.chat_service import ChatService
from datetime import datetime
import logging
import uuid
import json

logger = logging.getLogger(__name__)
router = APIRouter()
chat_service = ChatService()

@router.post("/start")
async def start_consultation(user_data: ConsultationCreate):
    """Start a new consultation session."""
    try:
        logger.info(f"Received consultation request with data: {json.dumps(user_data.dict())}")
        
        consultation_id = str(uuid.uuid4())
        logger.info(f"Generated consultation ID: {consultation_id}")
        
        consultation_data = {
            "consultation_id": consultation_id,
            "user_details": user_data.dict(),
            "status": "started",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "chat_history": [],
            "diagnosis": None,
            "language_preferences": {
                "preferred": user_data.preferred_language,
                "interface": user_data.interface_language
            }
        }
        
        try:
            result = await consultations_collection.insert_one(consultation_data)
            logger.info(f"Consultation created with ID: {consultation_id}")
            
            if not result.inserted_id:
                logger.error("Failed to get inserted_id from MongoDB")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create consultation record"
                )
            
            return {
                "status": "success",
                "consultationId": consultation_id,
                "userDetails": user_data.dict(),
                "message": "Consultation started successfully"
            }
            
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
    
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{consultation_id}")
async def get_consultation_status(consultation_id: str):
    """Get the current status of a consultation."""
    try:
        consultation = await consultations_collection.find_one(
            {"consultation_id": consultation_id}
        )
        
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        return {
            "status": "active",
            "consultationId": consultation_id,
            "userDetails": consultation["user_details"],
            "created_at": consultation["created_at"],
            "language_preferences": consultation.get("language_preferences", {})
        }
    
    except Exception as e:
        logger.error(f"Error getting consultation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message/{consultation_id}")
async def handle_message(consultation_id: str, message: dict):
    """Handle incoming chat messages."""
    try:
        # Process message based on language preferences
        consultation = await consultations_collection.find_one({"consultation_id": consultation_id})
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        preferred_language = consultation["language_preferences"]["preferred"]
        
        # Process message through chat service
        processed_response = await chat_service.process_message(
            consultation_id=consultation_id,
            message=message.get("content", ""),
            source_language=message.get("language", "en"),
            target_language=preferred_language
        )

        return processed_response

    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
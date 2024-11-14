# backend/app/routes/feedback.py
from fastapi import APIRouter, HTTPException, Depends
from app.models.feedback import FeedbackCreate, FeedbackResponse
from app.config.database import consultations_collection
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackCreate):
    """Submit feedback for a consultation"""
    try:
        # Verify consultation exists
        consultation = await consultations_collection.find_one(
            {"consultation_id": feedback.consultation_id}
        )
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        # Create feedback document
        feedback_id = str(uuid.uuid4())
        feedback_doc = {
            "id": feedback_id,
            **feedback.dict(),
            "created_at": datetime.utcnow()
        }

        # Update consultation with feedback
        result = await consultations_collection.update_one(
            {"consultation_id": feedback.consultation_id},
            {
                "$set": {
                    "feedback": feedback_doc,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to submit feedback")

        return FeedbackResponse(**feedback_doc)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{consultation_id}", response_model=FeedbackResponse)
async def get_feedback(consultation_id: str):
    """Get feedback for a specific consultation"""
    consultation = await consultations_collection.find_one(
        {"consultation_id": consultation_id},
        {"feedback": 1}
    )
    
    if not consultation or "feedback" not in consultation:
        raise HTTPException(status_code=404, detail="Feedback not found")
        
    return FeedbackResponse(**consultation["feedback"])

@router.get("/stats/{consultation_id}")
async def get_feedback_stats(consultation_id: str):
    """Get statistical analysis of feedback"""
    try:
        consultation = await consultations_collection.find_one(
            {"consultation_id": consultation_id},
            {"feedback": 1}
        )
        
        if not consultation or "feedback" not in consultation:
            raise HTTPException(status_code=404, detail="Feedback not found")
            
        feedback = consultation["feedback"]
        
        # Calculate average scores
        stats = {
            "average_rating": feedback["rating"],
            "average_symptom_accuracy": feedback["symptom_accuracy"],
            "average_recommendation_helpfulness": feedback["recommendation_helpfulness"],
            "has_comment": bool(feedback.get("comment")),
            "feedback_date": feedback["created_at"]
        }
        
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{consultation_id}")
async def delete_feedback(consultation_id: str):
    """Delete feedback for a specific consultation"""
    try:
        result = await consultations_collection.update_one(
            {"consultation_id": consultation_id},
            {
                "$unset": {"feedback": ""},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Feedback not found")
            
        return {"message": "Feedback deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# backend/app/routes/summary.py
from fastapi import APIRouter, HTTPException
from app.config.database import consultations_collection
from app.utils.symptom_analyzer import SymptomAnalyzer
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/summary/{consultation_id}")
async def get_consultation_summary(consultation_id: str):
    """Get consultation summary and generate diagnosis."""
    try:
        consultation = consultations_collection.find_one(
            {"consultation_id": consultation_id}
        )
        
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        try:
            chat_history = consultation.get('chat_history', [])
            symptom_analyzer = SymptomAnalyzer()
            
            analyzed_symptoms = await symptom_analyzer.analyze_conversation(chat_history)
            severity_assessment = await symptom_analyzer.get_severity_assessment(
                analyzed_symptoms.get('symptoms', [])
            )
            validation_result = await symptom_analyzer.validate_medical_response(
                str(analyzed_symptoms),
                chat_history
            )
            treatment_recommendations = await symptom_analyzer.get_treatment_recommendations(
                analyzed_symptoms.get('symptoms', [])
            )
            
            # Get user's preferred language
            preferred_language = consultation["language_preferences"]["preferred"]
            
            summary = {
                "consultation_id": consultation_id,
                "userDetails": consultation["user_details"],
                "diagnosis": {
                    "symptoms": analyzed_symptoms.get('symptoms', []),
                    "description": analyzed_symptoms.get('progression', ''),
                    "severityScore": severity_assessment.get('overall_severity', 0),
                    "riskLevel": severity_assessment.get('risk_level', 'unknown'),
                    "timeframe": severity_assessment.get('recommended_timeframe', ''),
                    "recommendedDoctor": symptom_analyzer.recommend_specialist(
                        analyzed_symptoms.get('symptoms', [])
                    )
                },
                "recommendations": {
                    "medications": treatment_recommendations.get("medications", []),
                    "homeRemedies": treatment_recommendations.get("homeRemedies", []),
                    "urgency": analyzed_symptoms.get('urgency', 'unknown'),
                    "safety_concerns": validation_result.get('safety_concerns', []),
                    "suggested_improvements": validation_result.get('suggested_improvements', [])
                },
                "precautions": analyzed_symptoms.get('precautions', []),
                "chatHistory": chat_history,
                "language": preferred_language,
                "created_at": consultation["created_at"],
                "completed_at": datetime.utcnow()
            }
            
            # Update consultation
            result = consultations_collection.update_one(
                {"consultation_id": consultation_id},
                {
                    "$set": {
                        "status": "completed",
                        "diagnosis_summary": summary,
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count == 0:
                logger.warning(f"No consultation was updated for ID: {consultation_id}")
            
            return summary
            
        except Exception as analysis_error:
            logger.error(f"Error analyzing consultation data: {str(analysis_error)}")
            raise HTTPException(status_code=500, detail=str(analysis_error))
            
    except Exception as e:
        logger.error(f"Error generating consultation summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
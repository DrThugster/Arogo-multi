# backend/app/routes/report.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.config.database import consultations_collection
from app.utils.report_generator import MultilingualReportGenerator
from app.routes.summary import get_consultation_summary
import io
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize the report generator
report_generator = MultilingualReportGenerator()

@router.get("/{consultation_id}")
async def get_consultation_report(consultation_id: str):
    """Generate and download PDF report."""
    try:
        consultation = consultations_collection.find_one(
            {"consultation_id": consultation_id}
        )
        
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")
        
        try:
            # Get or generate summary
            if "diagnosis_summary" not in consultation:
                summary = await get_consultation_summary(consultation_id)
            else:
                summary = consultation["diagnosis_summary"]
            
            # Ensure symptoms data is available
            if "symptoms" not in summary and "diagnosis" in summary:
                summary["symptoms"] = summary["diagnosis"].get("symptoms", [])
            
            # Get user's preferred language for the report
            preferred_language = consultation["language_preferences"]["preferred"]
            
            # Generate PDF in preferred language
            pdf_buffer = await report_generator.create_pdf_report(summary, preferred_language)
            
            return StreamingResponse(
                io.BytesIO(pdf_buffer.getvalue()),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=consultation-report-{consultation_id}.pdf"
                }
            )
            
        except Exception as report_error:
            logger.error(f"Error generating PDF report: {str(report_error)}")
            raise HTTPException(status_code=500, detail=str(report_error))
            
    except Exception as e:
        logger.error(f"Error handling report request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
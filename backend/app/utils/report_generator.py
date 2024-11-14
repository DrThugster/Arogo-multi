# backend/app/utils/report_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from app.utils.speech_processor import MultilingualSpeechProcessor
import logging

logger = logging.getLogger(__name__)

class MultilingualReportGenerator:
    def __init__(self):
        self.speech_processor = MultilingualSpeechProcessor()
        
        # Register fonts for different scripts
        self._register_fonts()
        
        # Translation labels for different languages
        self.section_labels = {
            "en": {
                "title": "Medical Consultation Report",
                "patient_info": "Patient Information",
                "diagnosis": "Diagnosis Summary",
                "symptoms": "Based on your reported symptoms:",
                "safety": "Safety Concerns",
                "urgency": "Urgency Level",
                "symptoms_analysis": "Detailed Symptoms Analysis",
                "chart": "Symptoms Analysis Chart",
                "followup": "Follow-up Information",
                "treatment": "Treatment Recommendations",
                "medications": "Recommended Medications:",
                "remedies": "Home Remedies:",
                "precautions": "Important Precautions",
                "disclaimer": "This is an AI-generated pre-diagnosis report and should not be considered as a replacement for professional medical advice."
            },
            "hi": {
                "title": "चिकित्सा परामर्श रिपोर्ट",
                "patient_info": "रोगी की जानकारी",
                # Add other Hindi translations
            },
            # Add other language translations
        }

    def _register_fonts(self):
        """Register fonts for different scripts."""
        try:
            # Register custom fonts for different scripts
            pdfmetrics.registerFont(TTFont('NotoSans', 'path/to/NotoSans-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('NotoSansDevanagari', 'path/to/NotoSansDevanagari-Regular.ttf'))
            # Add more script-specific fonts
        except Exception as e:
            logger.error(f"Error registering fonts: {e}")
            # Fallback to default fonts

    async def _get_translated_text(self, text: str, target_language: str) -> str:
        """Translate text if needed."""
        if target_language == "en":
            return text
        try:
            translation = await self.speech_processor.bhashini_service.translate_text(
                text=text,
                source_language="en",
                target_language=target_language
            )
            return translation["text"]
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    def _get_font_for_language(self, language: str) -> str:
        """Get appropriate font for language."""
        font_mapping = {
            "hi": "NotoSansDevanagari",
            "ta": "NotoSansTamil",
            # Add more language-font mappings
        }
        return font_mapping.get(language, "Helvetica")

    async def create_pdf_report(self, consultation_data: dict, language: str = "en") -> BytesIO:
        """Create multilingual PDF report."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Get labels for target language
        labels = self.section_labels.get(language, self.section_labels["en"])
        
        # Get appropriate font
        base_font = self._get_font_for_language(language)
        
        styles = getSampleStyleSheet()
        # Add custom styles with language-specific fonts
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1976d2'),
            fontName=base_font
        ))
        styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor('#1976d2'),
            fontName=base_font
        ))
        styles.add(ParagraphStyle(
            name='NormalMulti',
            parent=styles['Normal'],
            fontName=base_font
        ))

        story = []
        
        # Header with translated title
        title = await self._get_translated_text(labels["title"], language)
        story.append(Paragraph(title, styles['CustomTitle']))
        
        consultation_id_text = await self._get_translated_text("Consultation ID:", language)
        story.append(Paragraph(f"{consultation_id_text} {consultation_data['consultation_id']}", styles['NormalMulti']))
        
        date_text = await self._get_translated_text("Date:", language)
        story.append(Paragraph(f"{date_text} {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['NormalMulti']))
        story.append(Spacer(1, 20))

        # Patient Information
        patient_info_title = await self._get_translated_text(labels["patient_info"], language)
        story.append(Paragraph(patient_info_title, styles['SectionTitle']))
        
        # Translate patient data labels
        patient_data = [
            [await self._get_translated_text("Name", language), 
             f"{consultation_data['userDetails']['firstName']} {consultation_data['userDetails']['lastName']}"],
            [await self._get_translated_text("Age", language), 
             str(consultation_data['userDetails']['age'])],
            [await self._get_translated_text("Gender", language), 
             await self._get_translated_text(consultation_data['userDetails']['gender'], language)],
            [await self._get_translated_text("Height", language), 
             f"{consultation_data['userDetails']['height']} cm"],
            [await self._get_translated_text("Weight", language), 
             f"{consultation_data['userDetails']['weight']} kg"]
        ]

        # Similar updates for other sections...
        # Continue with the same structure but with translations

        # Diagnosis Summary
        diagnosis_title = await self._get_translated_text(labels["diagnosis"], language)
        story.append(Paragraph(diagnosis_title, styles['SectionTitle']))
        
        # Translate and format symptoms
        symptoms_text = await self._get_translated_text(labels["symptoms"], language) + "\n"
        for symptom in consultation_data['diagnosis']['symptoms']:
            symptom_name = await self._get_translated_text(symptom['name'], language)
            intensity_text = await self._get_translated_text("intensity", language)
            confidence_text = await self._get_translated_text("confidence", language)
            symptoms_text += f"- {symptom_name}: {symptom['severity']}/10 {intensity_text} {symptom.get('confidence', 'N/A')}% {confidence_text}\n"
        
        story.append(Paragraph(symptoms_text, styles['NormalMulti']))
        story.append(Spacer(1, 10))

        # Continue with other sections...
        # Add translated charts, recommendations, etc.

        # Disclaimer in target language
        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=styles['NormalMulti'],
            fontSize=8,
            textColor=colors.grey,
            alignment=1
        )
        
        disclaimer_text = await self._get_translated_text(labels["disclaimer"], language)
        story.append(Paragraph(disclaimer_text, disclaimer_style))
        
        # Build document
        doc.build(story)
        buffer.seek(0)
        return buffer

    def create_symptoms_chart(self, symptoms, language: str = "en"):
        """Create symptoms radar chart with translated labels."""
        try:
            # Translate symptom names
            names = [symptom['name'] for symptom in symptoms]
            values = [symptom.get('severity', symptom.get('intensity', 0)) for symptom in symptoms]
            
            num_vars = len(names)
            angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
            angles += angles[:1]
            values += values[:1]
            
            fig, ax = plt.subplots(figsize=(4, 5), subplot_kw=dict(projection='polar'))
            
            # Use appropriate font for the language
            plt.rcParams['font.family'] = self._get_font_for_language(language)
            
            ax.plot(angles, values)
            ax.fill(angles, values, alpha=0.25)
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(names)
            
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', bbox_inches='tight')
            plt.close()
            
            return img_buffer
            
        except Exception as e:
            logger.error(f"Error creating symptoms chart: {e}")
            return None
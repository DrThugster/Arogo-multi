# backend/app/utils/symptom_analyzer.py
from typing import Dict, List
import logging
from app.utils.ai_config import GeminiConfig
import json
import re
from transformers import pipeline

logger = logging.getLogger(__name__)


from transformers import pipeline
from typing import Dict, List
import logging

class SymptomAnalyzer:
    def __init__(self):
        self.ai_config = GeminiConfig()
        # Using a verified medical NER model
        self.ner_pipeline = pipeline("ner", model="samrawal/bert-base-uncased_clinical-ner")
        
    async def analyze_conversation(self, chat_history: List[Dict]) -> Dict:
        try:
            # Extract conversation text
            conversation_text = "\n".join([msg["content"] for msg in chat_history])
            
            # Use NER to identify medical entities
            medical_entities = self.ner_pipeline(conversation_text)
            
            # Structure prompt for Gemini
            analysis_prompt = f"""
            Analyze these medical symptoms and entities:
            
            Conversation: {conversation_text}
            Identified Medical Entities: {medical_entities}
            
            Provide structured analysis with:
            1. Each symptom's severity (1-10)
            2. Duration
            3. Pattern (constant/intermittent)
            4. Related factors
            
            Format as JSON:
            {{
                "symptoms": [
                    {{
                        "name": "symptom name",
                        "severity": numeric_value,
                        "duration": "duration",
                        "pattern": "pattern"
                    }}
                ],
                "risk_level": "low|medium|high",
                "urgency": "routine|prompt|immediate"
            }}
            """
            
            # Get AI analysis
            response = self.ai_config.model.generate_content(analysis_prompt)
            return self._parse_ai_response(response.text)
            
        except Exception as e:
            logger.error(f"Error analyzing symptoms: {str(e)}")
            return {
                "symptoms": [],
                "risk_level": "unknown",
                "urgency": "unknown"
            }


    def _extract_symptoms(self, text: str) -> List[Dict]:
        symptoms = []
        for match in re.finditer(self.symptom_patterns['pain'], text, re.IGNORECASE):
            severity = re.search(self.symptom_patterns['severity'], text[match.start():match.start()+50])
            duration = re.search(self.symptom_patterns['duration'], text[match.start():match.start()+50])
            frequency = re.search(self.symptom_patterns['frequency'], text[match.start():match.start()+50])
            
            symptoms.append({
                "name": match.group(),
                "severity": int(severity.group(1)) if severity else 5,
                "duration": duration.group() if duration else "Not specified",
                "pattern": frequency.group() if frequency else "Not specified"
            })
        return symptoms

    async def validate_medical_response(self, response: str, context: List[Dict]) -> Dict:
        """Validate medical response using AI."""
        try:
            validation_prompt = f"""
            Validate this medical response for quality and safety:

            Response to validate:
            {response}

            Context:
            {self._format_chat_history(context)}

            Check for:
            1. Medical accuracy
            2. Appropriate caution/disclaimers
            3. Emergency recognition
            4. Completeness of response
            5. Professional tone
            
            Format response as JSON with these exact keys:
            {{
                "is_valid": true|false,
                "safety_concerns": ["concern1", "concern2"],
                "missing_elements": ["element1", "element2"],
                "emergency_level": "none|low|high",
                "improvement_needed": true|false,
                "suggested_improvements": ["improvement1", "improvement2"]
            }}
            """

            validation_response = self.ai_config.model.generate_content(validation_prompt)
            return self._parse_ai_response(validation_response.text)

        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            raise

    def _format_chat_history(self, chat_history: List[Dict]) -> str:
        """Format chat history for AI prompt."""
        formatted = []
        for msg in chat_history:
            role = "Patient" if msg["type"] == "user" else "Doctor"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def _parse_ai_response(self, response: str) -> Dict:
        """Parse AI response ensuring it's valid JSON."""
        try:
            # Clean and format the response text
            cleaned_response = response.strip()
            # Look for JSON content between curly braces if present
            start_idx = cleaned_response.find('{')
            end_idx = cleaned_response.rfind('}')
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = cleaned_response[start_idx:end_idx + 1]
                return json.loads(json_str)
            
            # If no JSON found, create a structured response
            return {
                "symptoms": [],
                "progression": "Unable to determine",
                "risk_level": "unknown",
                "urgency": "unknown",
                "confidence_score": 0
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed, creating structured response: {str(e)}")
            return {
                "symptoms": [],
                "progression": "Unable to determine",
                "risk_level": "unknown",
                "urgency": "unknown",
                "confidence_score": 0
            }


    async def get_severity_assessment(self, symptoms: List[Dict]) -> Dict:
        """Get AI-powered severity assessment."""
        severity_prompt = f"""
        Assess the severity of these symptoms:
        {json.dumps(symptoms, indent=2)}

        Consider:
        1. Individual symptom severity
        2. Symptom combinations
        3. Impact on daily life
        4. Risk factors
        5. Emergency indicators

        Provide assessment as JSON with:
        {{
            "overall_severity": 1-10,
            "risk_level": "low|medium|high",
            "requires_emergency": true|false,
            "recommended_timeframe": "when to seek care",
            "reasoning": ["reason1", "reason2"]
        }}
        """

        response = self.ai_config.model.generate_content(severity_prompt)
        return self._parse_ai_response(response.text)
    
    def analyze_symptoms(self, chat_history: List[Dict]) -> List[Dict]:
        try:
                symptoms = []
                for message in chat_history:
                    # Add direct symptom extraction from message content
                    content = message.get('content', '')
                    if content:
                        # Extract symptoms using NER pipeline
                        entities = self.ner_pipeline(content)
                        for entity in entities:
                            if entity['entity'].startswith('B-PROBLEM'):
                                symptoms.append({
                                    'name': entity['word'],
                                    'severity': 5,  # Default severity
                                    'duration': 'Not specified',
                                    'pattern': 'Not specified'
                                })
                return symptoms
        except Exception as e:
            logger.error(f"Error analyzing symptoms: {str(e)}")
            return []


    def calculate_severity_score(self, symptoms: List[Dict]) -> float:
        try:
            if not symptoms:
                return 0.0
                
            severities = []
            for symptom in symptoms:
                severity = symptom.get('severity', 0)
                if severity is not None:
                    severities.append(float(severity))
            
            return sum(severities) / len(severities) if severities else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating severity score: {str(e)}")
            return 0.0

    def determine_risk_level(self, symptoms: List[Dict]) -> str:
        """Determine risk level based on symptoms."""
        severity_score = self.calculate_severity_score(symptoms)
        
        if severity_score >= 8.0:
            return "high"
        elif severity_score >= 5.0:
            return "medium"
        else:
            return "low"

    def recommend_timeframe(self, symptoms: List[Dict]) -> str:
        """Recommend consultation timeframe based on symptoms."""
        risk_level = self.determine_risk_level(symptoms)
        
        if risk_level == "high":
            return "immediate"
        elif risk_level == "medium":
            return "within 24 hours"
        else:
            return "within a week"

    def recommend_specialist(self, symptoms: List[Dict]) -> str:
        """Recommend appropriate medical specialist based on symptoms."""
        try:
            specialist_prompt = f"""
            Based on these symptoms: {json.dumps(symptoms)}
            
            Determine the most appropriate medical specialist considering:
            1. Primary affected body system
            2. Symptom complexity
            3. Specific medical expertise required
            
            Choose ONE specialist from:
            - Cardiologist
            - Dermatologist
            - Gastroenterologist
            - Neurologist
            - Orthopedist
            - Pulmonologist
            - ENT Specialist
            - Endocrinologist
            - Rheumatologist
            - General Practitioner
            
            Format response as JSON:
            {{
                "recommended_specialist": "specialist name",
                "reasoning": ["reason1", "reason2"]
            }}
            """
            
            response = self.ai_config.model.generate_content(specialist_prompt)
            result = self._parse_ai_response(response.text)
            
            return result.get("recommended_specialist", "General Practitioner")
            
        except Exception as e:
            logger.error(f"Error determining specialist: {str(e)}")
            return "General Practitioner"

    
    def needs_conclusion(self, context: list) -> bool:
        symptoms = self.analyze_symptoms(context)
        severity_score = self.calculate_severity_score(symptoms)
        
        return any([
            len(symptoms) >= 3,  # Enough symptoms gathered
            severity_score >= 7,  # High severity detected
            len(context) >= 10,  # Conversation length threshold
            any(self._contains_emergency_indicators(symptom['name']) for symptom in symptoms)
        ])
    
    async def get_treatment_recommendations(self, symptoms: List[Dict]) -> Dict:
        """Generate treatment recommendations based on symptoms."""
        prompt = f"""
        Based on these symptoms: {json.dumps(symptoms)}
        Provide treatment recommendations in this exact format:
        {{
            "medications": ["med1", "med2"],
            "homeRemedies": ["remedy1", "remedy2"]
        }}
        Include 2-3 specific items in each category.
        """
        
        response = self.ai_config.model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON if embedded in other text
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx + 1]
            return json.loads(json_str)
        
        # Return default structure if parsing fails
        return {
            "medications": ["Consult doctor for appropriate medication"],
            "homeRemedies": ["Rest and hydration recommended"]
        }
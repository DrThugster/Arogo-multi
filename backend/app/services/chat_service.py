# backend/app/services/chat_service.py
from app.utils.ai_config import GeminiConfig
from app.utils.symptom_analyzer import SymptomAnalyzer
from app.config.database import redis_client, consultations_collection
from app.utils.speech_processor import MultilingualSpeechProcessor
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.ai_config = GeminiConfig()
        self.symptom_analyzer = SymptomAnalyzer()
        self.conversation_expiry = 3600  # 1 hour
        self.speech_processor = MultilingualSpeechProcessor()
        self.bhashini_service = self.speech_processor.bhashini_service

    async def get_conversation_context(self, consultation_id: str) -> list:
        """Retrieve conversation context from Redis."""
        try:
            context = redis_client.get(f"chat_context_{consultation_id}")
            return json.loads(context) if context else []
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []

    async def store_conversation_context(self, consultation_id: str, context: list):
        """Store conversation context in Redis."""
        try:
            redis_client.setex(
                f"chat_context_{consultation_id}",
                self.conversation_expiry,
                json.dumps(context)
            )
        except Exception as e:
            logger.error(f"Error storing context: {e}")

    async def process_message(self, consultation_id: str, message: str, source_language: str = "en") -> dict:
        try:
            # Get current context
            context = await self.get_conversation_context(consultation_id)
            
            # Translate message to English if needed
            english_message = message
            original_message = message
            if source_language != "en":
                logger.info(f"Translating input from {source_language} to English")
                translation_result = await self.bhashini_service.translate_text(
                    text=message,
                    source_language=source_language,
                    target_language="en"
                )
                english_message = translation_result["text"]
                logger.info(f"Translated text: {english_message}")
            
            # Add user message to context with language info
            user_message = {
                "type": "user",
                "content": english_message,
                "original_content": original_message,
                "language": source_language,
                "timestamp": datetime.utcnow().isoformat()
            }
            context.append(user_message)

            # Get consultation details
            consultation = consultations_collection.find_one({"consultation_id": consultation_id})
            user_details = consultation.get("user_details", {})
            target_language = user_details.get("preferred_language", source_language)

            # Generate AI response with context (in English)
            response = await self._generate_ai_response(english_message, context, user_details)

            # Analyze symptoms from conversation
            symptom_analysis = await self.symptom_analyzer.analyze_conversation(context)
            
            # Get treatment recommendations
            treatment_recommendations = await self.symptom_analyzer.get_treatment_recommendations(
                symptom_analysis.get("symptoms", [])
            )
            
            # Validate response
            validation_result = await self.symptom_analyzer.validate_medical_response(
                response,
                context
            )

            # Translate response if needed
            final_response = response
            if target_language != "en":
                logger.info(f"Translating response to {target_language}")
                translation_result = await self.bhashini_service.translate_text(
                    text=response,
                    source_language="en",
                    target_language=target_language
                )
                final_response = translation_result["text"]

            # Generate audio in target language
            audio_result = await self.speech_processor.process_text_to_speech(
                text=final_response,
                target_language=target_language
            )

            # Process final response with treatment recommendations
            processed_response = await self._process_response(
                final_response,
                symptom_analysis,
                validation_result,
                treatment_recommendations,
                target_language,
                audio_result.get("audio_data")
            )

            # Add bot message to context with language info
            bot_message = {
                "type": "bot",
                "content": processed_response["response"],
                "original_content": response,  # English version
                "language": target_language,
                "timestamp": datetime.utcnow().isoformat(),
                "symptom_analysis": symptom_analysis,
                "validation": validation_result
            }
            context.append(bot_message)

            # Store updated context
            await self.store_conversation_context(consultation_id, context)
            
            # Update MongoDB
            await self.update_chat_history(consultation_id, [user_message, bot_message])

            return processed_response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def _generate_ai_response(self, message: str, context: list, user_details: dict) -> str:
        """Generate AI response using Gemini (keeping original functionality)."""
        question_count = sum(1 for msg in context if msg['type'] == 'bot' and '?' in msg['content'])
        symptoms = self.symptom_analyzer.analyze_symptoms(context)
        severity_score = self.symptom_analyzer.calculate_severity_score(symptoms)
        
        prompt = f"""
        You are a medical AI assistant. Your task is to either:
        1. Ask exactly ONE specific question about symptoms
        OR
        2. Provide a final assessment if criteria are met

        Patient Details:
        Age: {user_details.get('age')}
        Gender: {user_details.get('gender')}
        Language: {user_details.get('preferred_language', 'en')}

        Conversation History:
        {self._format_context(context)}

        Current Message: {message}
        Questions Asked: {question_count}/5
        Symptoms Identified: {json.dumps(symptoms)}
        Current Severity: {severity_score}

        STRICT RESPONSE FORMAT:
        {"[ASSESSMENT]\nSymptom Summary:\nLikely Condition:\nNext Steps:\nUrgency Level:" if question_count >= 4 or severity_score >= 7 
        else "[QUESTION]\nAsk exactly ONE specific question about: (most concerning symptom or important missing information)"}

        RULES:
        - ONE question only, no follow-ups in same response
        - Question must be specific and focused
        - Response under 50 words
        - No treatment advice during questioning
        - Maximum 6 questions total
        - Keep medical terms in English even after translation

        {f"Provide final assessment now." if question_count >= 4 or severity_score >= 7 
        else "Provide single most important question."}
        """

        response = self.ai_config.model.generate_content(prompt)
        cleaned_response = response.text.replace('[QUESTION]', '').replace('[ASSESSMENT]', '').strip()
        return cleaned_response

    async def _process_response(
        self, 
        response: str, 
        symptom_analysis: dict, 
        validation: dict, 
        treatment_recommendations: dict,
        language: str = "en",
        audio_data: str = None
    ) -> dict:
        """Process and enhance the AI response with language support."""
        processed = {
            "response": response,
            "symptoms": symptom_analysis.get("symptoms", []),
            "risk_level": symptom_analysis.get("risk_level", "unknown"),
            "urgency": symptom_analysis.get("urgency", "unknown"),
            "requires_emergency": validation.get("emergency_level") == "high",
            "recommendations": {
                    "medications": treatment_recommendations.get("medications", []),
                    "homeRemedies": treatment_recommendations.get("homeRemedies", []),
                    "urgency": symptom_analysis.get("urgency", "unknown"),
                    "safety_concerns": validation.get("safety_concerns", []),
                    "suggested_improvements": validation.get("suggested_improvements", [])
            },
            "language": {
                "code": language,
                "name": self.speech_processor.language_metadata.get(language, {}).get("name", "Unknown")
            },
            "audio": audio_data,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add emergency warning if needed (with translation if necessary)
        if processed["requires_emergency"]:
            emergency_prefix = "⚠️ URGENT: This requires immediate medical attention!\n\n"
            if language != "en":
                translated_prefix = await self.bhashini_service.translate_text(
                    text=emergency_prefix,
                    source_language="en",
                    target_language=language
                )
                emergency_prefix = translated_prefix["text"]
            processed["response"] = emergency_prefix + processed["response"]

        return processed

    def _format_context(self, context: list) -> str:
        """Format conversation context for AI prompt."""
        return "\n".join([
            f"{'Patient' if msg['type'] == 'user' else 'Assistant'}: {msg.get('content', '')}"
            for msg in context[-5:]  # Last 5 messages for context
        ])

    async def update_chat_history(self, consultation_id: str, messages: list):
        """Update chat history in MongoDB."""
        try:
            for message in messages:
                consultations_collection.update_one(
                    {"consultation_id": consultation_id},
                    {
                        "$push": {
                            "chat_history": message
                        },
                        "$set": {
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Error updating chat history: {e}")
            raise
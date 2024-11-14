# backend/app/routes/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from app.utils.response_validator import AIResponseValidator
from app.utils.symptom_analyzer import SymptomAnalyzer
from app.config.database import redis_client, consultations_collection
from app.services.chat_service import ChatService
from app.utils.speech_processor import MultilingualSpeechProcessor
import json
from datetime import datetime
from typing import Dict, Optional
import logging
import asyncio
from fastapi import APIRouter

router = APIRouter()


logger = logging.getLogger(__name__)

class MultilingualConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chat_service = ChatService()
        self.speech_processor = MultilingualSpeechProcessor()
        self.response_validator = AIResponseValidator()
        self.symptom_analyzer = SymptomAnalyzer()
        self.reconnect_attempts: Dict[str, int] = {}
        self.max_reconnect_attempts = 3

    async def connect(self, websocket: WebSocket, consultation_id: str):
        """Establish WebSocket connection with language support."""
        try:
            await websocket.accept()
            self.active_connections[consultation_id] = websocket
            logger.info(f"WebSocket connected: {consultation_id}")

            # Get user's language preference
            consultation = await consultations_collection.find_one(
                {"consultation_id": consultation_id}
            )
            language_prefs = consultation.get("language_preferences", {})
            preferred_language = language_prefs.get("preferred", "en")
            
            # Send welcome message in preferred language
            await self._send_welcome_message(consultation_id, consultation, preferred_language)

        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            raise

    async def _send_welcome_message(
        self,
        consultation_id: str,
        consultation: dict,
        language: str
    ):
        """Send welcome message in user's preferred language."""
        try:
            context = await self.chat_service.get_conversation_context(consultation_id)
            user_details = consultation.get("user_details", {})

            if context:
                # Welcome back message
                prompt = f"""
                Generate a brief welcome back message for:
                Name: {user_details.get('firstName')}
                Previous conversation available: Yes
                Language: {language}
                Keep it professional and friendly.
                """
            else:
                # Initial welcome
                prompt = f"""
                Generate a welcome message for new patient:
                Name: {user_details.get('firstName')}
                Age: {user_details.get('age')}
                Gender: {user_details.get('gender')}
                Language: {language}
                Ask about their symptoms professionally.
                """

            # Generate welcome message
            response =  self.chat_service.ai_config.model.generate_content(prompt)
            welcome_text = response.text if hasattr(response, 'text') else str(response)
            welcome_text = welcome_text.strip()

            # Translate if needed
            if language != "en":
                translated = await self.speech_processor.bhashini_service.translate_text(
                    text=welcome_text,
                    source_language="en",
                    target_language=language
                )
                welcome_text = translated["text"]

            # Generate audio if needed
            audio_data = None
            if consultation.get("user_details", {}).get("enable_audio", True):
                audio_result = await self.speech_processor.process_text_to_speech(
                    text=welcome_text,
                    target_language=language
                )
                audio_data = audio_result.get("audio_data")

            welcome_message = {
                "type": "welcome",
                "content": welcome_text,
                "language": language,
                "audio": audio_data,
                "timestamp": datetime.utcnow().isoformat()
            }

            await self.active_connections[consultation_id].send_json(welcome_message)
            logger.info(f"Welcome message sent for {consultation_id} in {language}")

        except Exception as e:
            logger.error(f"Error sending welcome message: {str(e)}")

    async def process_message(
        self, 
        message: str, 
        consultation_id: str,
        source_language: Optional[str] = None
    ) -> dict:
        """Process message with multilingual support."""
        try:
            consultation = await consultations_collection.find_one(
                {"consultation_id": consultation_id}
            )
            target_language = consultation.get("language_preferences", {}).get("preferred", "en")
            
            # Process through chat service
            response = await self.chat_service.process_message(
                consultation_id=consultation_id,
                message=message,
                source_language=source_language or target_language,
                target_language=target_language
            )
            
            # Validate response
            is_valid, error_msg, processed_response = await self.response_validator.validate_response(
                response["response"],
                source_language=target_language
            )
            
            if not is_valid:
                error_message = "I need to rephrase. Please repeat your message."
                if target_language != "en":
                    translated_error = await self.speech_processor.bhashini_service.translate_text(
                        text=error_message,
                        source_language="en",
                        target_language=target_language
                    )
                    error_message = translated_error["text"]
                return {
                    "status": "error",
                    "message": error_message,
                    "error": error_msg,
                    "language": target_language
                }

            # Generate audio for response
            audio_data = None
            if consultation.get("user_details", {}).get("enable_audio", True):
                audio_result = await self.speech_processor.process_text_to_speech(
                    text=response["response"],
                    target_language=target_language
                )
                audio_data = audio_result.get("audio_data")

            return {
                "status": "success",
                "message": response["response"],
                "original_message": response.get("original_response"),
                "confidence_scores": processed_response['confidence_scores'],
                "requires_emergency": processed_response['requires_emergency'],
                "language": {
                    "source": source_language or target_language,
                    "target": target_language,
                    "detected": response.get("detected_language")
                },
                "audio": audio_data,
                "symptoms": response.get("symptoms", []),
                "recommendations": response.get("recommendations", {}),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "status": "error",
                "message": "Processing error. Please try again.",
                "error": str(e),
                "language": target_language
            }

    async def disconnect(self, consultation_id: str):
        """Handle disconnection cleanup."""
        if consultation_id in self.active_connections:
            del self.active_connections[consultation_id]
            if consultation_id in self.reconnect_attempts:
                del self.reconnect_attempts[consultation_id]
            logger.info(f"WebSocket disconnected: {consultation_id}")

    async def handle_connection_error(self, consultation_id: str):
        """Handle connection errors with reconnection logic."""
        try:
            if consultation_id in self.reconnect_attempts:
                self.reconnect_attempts[consultation_id] += 1
                
                if self.reconnect_attempts[consultation_id] <= self.max_reconnect_attempts:
                    wait_time = 2 ** self.reconnect_attempts[consultation_id]
                    logger.info(f"Waiting {wait_time}s before reconnection attempt")
                    await asyncio.sleep(wait_time)
                else:
                    logger.warning(f"Max reconnection attempts reached: {consultation_id}")
                    await self._save_disconnection_state(consultation_id)
                    await self.disconnect(consultation_id)
        except Exception as e:
            logger.error(f"Error handling connection error: {str(e)}")
            await self.disconnect(consultation_id)

    async def _save_disconnection_state(self, consultation_id: str):
        """Save conversation state on disconnection."""
        try:
            await consultations_collection.update_one(
                {"consultation_id": consultation_id},
                {
                    "$set": {
                        "connection_state": "disconnected",
                        "disconnected_at": datetime.utcnow(),
                        "reconnect_attempts": self.reconnect_attempts.get(consultation_id, 0)
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error saving disconnection state: {str(e)}")

# Global manager instance
manager = MultilingualConnectionManager()

def initialize_manager():
    """Initialize the WebSocket connection manager."""
    global manager
    manager = MultilingualConnectionManager()


# Create WebSocket endpoint
@router.websocket("/ws/{consultation_id}")
async def websocket_endpoint(websocket: WebSocket, consultation_id: str):
    """WebSocket endpoint for multilingual chat."""
    manager = MultilingualConnectionManager()
    try:
        await manager.connect(websocket, consultation_id)
        
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                source_language = message_data.get('language')
                
                # Process message
                response = await manager.process_message(
                    message=message_data.get('content', ''),
                    consultation_id=consultation_id,
                    source_language=source_language
                )
                
                # Update consultation analysis
                await manager.chat_service.update_chat_history(
                    consultation_id=consultation_id,
                    messages=[{
                        "type": "user",
                        "content": message_data.get('content', ''),
                        "language": source_language,
                        "timestamp": datetime.utcnow().isoformat()
                    }, {
                        "type": "bot",
                        "content": response["message"],
                        "language": response["language"]["target"],
                        "timestamp": datetime.utcnow().isoformat(),
                        "analysis": {
                            "symptoms": response.get("symptoms", []),
                            "recommendations": response.get("recommendations", {}),
                            "confidence": response.get("confidence_scores", {}),
                            "requires_emergency": response.get("requires_emergency", False)
                        }
                    }]
                )
                
                await websocket.send_json(response)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message format"
                })
            except Exception as e:
                logger.error(f"Message processing error: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Error processing message",
                    "error": str(e)
                })
                
    except WebSocketDisconnect:
        await manager.disconnect(consultation_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await manager.disconnect(consultation_id)
        try:
            await websocket.close()
        except:
            pass
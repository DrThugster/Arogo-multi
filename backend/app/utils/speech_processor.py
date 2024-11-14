# backend/app/utils/speech_processor.py
import io
import tempfile
import os
import base64
import logging
import uuid
from pydub import AudioSegment
from app.services.bhashini_service import BhashiniService
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class MultilingualSpeechProcessor:
    def __init__(self):
        self.bhashini_service = BhashiniService()
        self.default_language = "en"
        
        # Enhanced language metadata
        self.language_metadata = {
            "en": {
                "name": "English",
                "variants": ["eng", "en-IN", "en-US"],
                "common_phrases": ["hello", "hi", "thank you"]
            },
            "hi": {
                "name": "Hindi",
                "variants": ["hin", "hi-IN"],
                "common_phrases": ["नमस्ते", "धन्यवाद"]
            },
            "ta": {
                "name": "Tamil",
                "variants": ["tam", "ta-IN"],
                "common_phrases": ["வணக்கம்", "நன்றி"]
            },
            "te": {
                "name": "Telugu",
                "variants": ["tel", "te-IN"],
                "common_phrases": ["నమస్కారం", "ధన్యవాదాలు"]
            },
            "ml": {
                "name": "Malayalam",
                "variants": ["mal", "ml-IN"],
                "common_phrases": ["നമസ്കാരം", "നന്ദി"]
            },
            "kn": {
                "name": "Kannada",
                "variants": ["kan", "kn-IN"],
                "common_phrases": ["ನಮಸ್ಕಾರ", "ಧನ್ಯವಾದಗಳು"]
            },
            "bn": {
                "name": "Bengali",
                "variants": ["ben", "bn-IN"],
                "common_phrases": ["নমস্কার", "ধন্যবাদ"]
            }
        }

    async def verify_language_support(self, language_code: str) -> bool:
        """Verify if a language is supported by Bhashini."""
        try:
            supported_langs = await self.bhashini_service.get_supported_languages()
            return language_code in supported_langs
        except Exception as e:
            logger.error(f"Error verifying language support: {str(e)}")
            return language_code in self.language_metadata

    async def convert_to_wav(self, audio_data: bytes) -> bytes:
        """Convert audio data to WAV format."""
        try:
            # Save incoming audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_webm:
                temp_webm.write(audio_data)
                temp_webm_path = temp_webm.name

            try:
                # Convert to WAV
                audio = AudioSegment.from_file(temp_webm_path, format="webm")
                wav_path = temp_webm_path + ".wav"
                audio.export(wav_path, format="wav")

                # Read the WAV file
                with open(wav_path, 'rb') as wav_file:
                    wav_data = wav_file.read()

                return wav_data

            finally:
                # Cleanup temporary files
                for path in [temp_webm_path, wav_path]:
                    if os.path.exists(path):
                        os.remove(path)

        except Exception as e:
            logger.error(f"Error converting audio format: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error converting audio: {str(e)}")

    async def detect_language_from_audio(self, audio_data: bytes) -> Dict[str, any]:
        """Automatically detect language from audio using Bhashini."""
        try:
            wav_data = await self.convert_to_wav(audio_data)
            
            # Use Bhashini's language detection
            detection_result = await self.bhashini_service.detect_language(wav_data)
            
            detected_lang = detection_result.get("detected_language", self.default_language)
            confidence = detection_result.get("confidence", 0.0)
            
            # Get additional language metadata
            lang_meta = self.language_metadata.get(detected_lang, {})
            
            return {
                "language_code": detected_lang,
                "language_name": lang_meta.get("name", "Unknown"),
                "confidence": confidence,
                "is_supported": await self.verify_language_support(detected_lang),
                "metadata": lang_meta
            }
        except Exception as e:
            logger.error(f"Error in language detection: {str(e)}")
            return {
                "language_code": self.default_language,
                "language_name": "English (Default)",
                "confidence": 0.0,
                "is_supported": True,
                "error": str(e)
            }

    async def process_speech_to_text(
        self, 
        audio_data: bytes,
        preferred_language: Optional[str] = None,
        enable_auto_detect: bool = True
    ) -> Dict[str, any]:
        """
        Process speech to text with smart language handling.
        """
        try:
            detected_info = None
            if enable_auto_detect:
                detected_info = await self.detect_language_from_audio(audio_data)
                logger.info(f"Detected language: {detected_info['language_name']}")

            # Determine final language choice
            final_language = preferred_language
            if not final_language and detected_info and detected_info['is_supported']:
                final_language = detected_info['language_code']
            
            if not final_language:
                final_language = self.default_language

            # Convert to WAV for processing
            wav_data = await self.convert_to_wav(audio_data)

            # Process with Bhashini
            result = await self.bhashini_service.speech_to_text(
                audio_data=wav_data,
                language=final_language
            )

            return {
                "text": result["text"],
                "language": {
                    "code": final_language,
                    "name": self.language_metadata.get(final_language, {}).get("name", "Unknown"),
                    "detected": detected_info if detected_info else None,
                    "was_auto_detected": bool(detected_info and final_language == detected_info['language_code']),
                    "user_preferred": preferred_language is not None
                },
                "confidence": result.get("confidence", 1.0),
                "timestamp": str(uuid.uuid4())
            }

        except Exception as e:
            logger.error(f"Error processing speech to text: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing speech: {str(e)}")

    async def process_text_to_speech(
        self, 
        text: str, 
        target_language: Optional[str] = None,
        voice_gender: str = "female",
        voice_style: Optional[str] = None
    ) -> Dict[str, str]:
        """Convert text to speech with multiple language support."""
        temp_path = None
        try:
            if not target_language:
                target_language = self.default_language

            if not await self.verify_language_support(target_language):
                raise ValueError(f"Language {target_language} not supported")

            temp_path = os.path.join(tempfile.gettempdir(), f'speech_{uuid.uuid4()}.mp3')

            # Generate speech using Bhashini
            audio_content = await self.bhashini_service.text_to_speech(
                text=text,
                target_language=target_language,
                gender=voice_gender,
                style=voice_style
            )

            # Save and encode audio
            with open(temp_path, 'wb') as audio_file:
                audio_file.write(audio_content)

            with open(temp_path, 'rb') as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode()

            return {
                "audio_data": audio_data,
                "language": target_language,
                "language_name": self.language_metadata.get(target_language, {}).get("name", "Unknown"),
                "voice_gender": voice_gender,
                "voice_style": voice_style
            }

        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating speech: {str(e)}")

        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    async def translate_speech(
        self,
        audio_data: bytes,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        auto_detect: bool = True,
        voice_gender: str = "female"
    ) -> Dict[str, any]:
        """Complete speech-to-speech translation."""
        try:
            # First get speech to text with language detection
            stt_result = await self.process_speech_to_text(
                audio_data=audio_data,
                preferred_language=source_language,
                enable_auto_detect=auto_detect
            )

            source_language = stt_result["language"]["code"]
            target_language = target_language or self.default_language

            # Verify target language
            if not await self.verify_language_support(target_language):
                raise ValueError(f"Target language {target_language} not supported")

            # Translate the text
            translation_result = await self.bhashini_service.translate_text(
                text=stt_result["text"],
                source_language=source_language,
                target_language=target_language
            )

            # Generate speech for translated text
            tts_result = await self.process_text_to_speech(
                text=translation_result["text"],
                target_language=target_language,
                voice_gender=voice_gender
            )

            return {
                "original": {
                    "text": stt_result["text"],
                    "language": source_language,
                    "language_name": self.language_metadata.get(source_language, {}).get("name", "Unknown"),
                    "confidence": stt_result["confidence"]
                },
                "translation": {
                    "text": translation_result["text"],
                    "language": target_language,
                    "language_name": self.language_metadata.get(target_language, {}).get("name", "Unknown"),
                    "audio": tts_result["audio_data"]
                },
                "metadata": {
                    "translation_confidence": translation_result.get("confidence", 1.0),
                    "voice_gender": voice_gender,
                    "was_auto_detected": stt_result["language"]["was_auto_detected"],
                    "timestamp": str(uuid.uuid4())
                }
            }

        except Exception as e:
            logger.error(f"Error in speech translation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error in speech translation: {str(e)}")

    async def get_supported_languages(self) -> Dict[str, any]:
        """Get information about supported languages and capabilities."""
        try:
            bhashini_langs = await self.bhashini_service.get_supported_languages()
            
            return {
                "supported_languages": self.language_metadata,
                "active_languages": bhashini_langs,
                "default_language": self.default_language,
                "capabilities": {
                    "speech_to_text": bhashini_langs.get("stt", []),
                    "text_to_speech": bhashini_langs.get("tts", []),
                    "translation": bhashini_langs.get("translation", [])
                }
            }
        except Exception as e:
            logger.error(f"Error getting language information: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching language information: {str(e)}")

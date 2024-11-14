# backend/app/routes/speech.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from app.utils.speech_processor import MultilingualSpeechProcessor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/speech-to-text")
async def speech_to_text(
    audio: UploadFile = File(...),
    source_language: Optional[str] = None,
    enable_auto_detect: bool = True
):
    """Convert speech audio to text with multilingual support."""
    try:
        logger.info("Receiving audio file for speech-to-text conversion")
        logger.info(f"Source language: {source_language}, Auto-detect: {enable_auto_detect}")
        
        contents = await audio.read()
        
        if not contents:
            raise ValueError("Empty audio file received")
            
        logger.info(f"Received audio file of size: {len(contents)} bytes")
        logger.info(f"Audio content type: {audio.content_type}")
        
        # Initialize multilingual speech processor
        speech_processor = MultilingualSpeechProcessor()
        
        # Process speech to text with language handling
        result = await speech_processor.process_speech_to_text(
            audio_data=contents,
            preferred_language=source_language,
            enable_auto_detect=enable_auto_detect
        )
        
        if not result.get("text"):
            raise ValueError("No text was transcribed from the audio")
            
        logger.info(f"Successfully transcribed text: {result['text']}")
        logger.info(f"Detected language: {result.get('language', {}).get('name', 'Unknown')}")
        
        return JSONResponse(
            content={
                "status": "success",
                "text": result["text"],
                "language": {
                    "detected": result.get("language", {}).get("detected"),
                    "code": result.get("language", {}).get("code", source_language or "en"),
                    "name": result.get("language", {}).get("name", "English"),
                    "confidence": result.get("language", {}).get("confidence", 1.0),
                },
                "confidence": result.get("confidence", 1.0),
                "timestamp": result.get("timestamp"),
                "was_auto_detected": result.get("language", {}).get("was_auto_detected", False)
            }
        )
    except ValueError as ve:
        logger.error(f"Validation error in speech-to-text: {str(ve)}")
        raise HTTPException(
            status_code=400, 
            detail={
                "error": str(ve),
                "type": "validation_error"
            }
        )
    except RuntimeError as re:
        logger.error(f"Runtime error in speech-to-text: {str(re)}")
        raise HTTPException(
            status_code=503, 
            detail={
                "error": str(re),
                "type": "service_error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in speech-to-text: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": "system_error"
            }
        )

@router.post("/text-to-speech")
async def text_to_speech(
    text: str,
    target_language: str,
    voice_gender: Optional[str] = "female",
    voice_style: Optional[str] = None
):
    """Convert text to speech in specified language."""
    try:
        logger.info("Receiving text-to-speech request")
        logger.info(f"Target language: {target_language}, Voice gender: {voice_gender}")
        
        if not text.strip():
            raise ValueError("Empty text received")
        
        # Initialize speech processor
        speech_processor = MultilingualSpeechProcessor()
        
        # Process text to speech
        result = await speech_processor.process_text_to_speech(
            text=text,
            target_language=target_language,
            voice_gender=voice_gender,
            voice_style=voice_style
        )
        
        if not result.get("audio_data"):
            raise ValueError("No audio was generated from the text")
            
        logger.info("Successfully generated speech audio")
        logger.info(f"Target language: {result.get('language_name', 'Unknown')}")
        
        return JSONResponse(
            content={
                "status": "success",
                "audio_data": result["audio_data"],
                "language": {
                    "code": result["language"],
                    "name": result["language_name"]
                },
                "voice": {
                    "gender": voice_gender,
                    "style": voice_style
                },
                "metadata": {
                    "text_length": len(text),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    except ValueError as ve:
        logger.error(f"Validation error in text-to-speech: {str(ve)}")
        raise HTTPException(
            status_code=400, 
            detail={
                "error": str(ve),
                "type": "validation_error"
            }
        )
    except RuntimeError as re:
        logger.error(f"Runtime error in text-to-speech: {str(re)}")
        raise HTTPException(
            status_code=503, 
            detail={
                "error": str(re),
                "type": "service_error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in text-to-speech: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": "system_error"
            }
        )

@router.post("/translate-speech")
async def translate_speech(
    audio: UploadFile = File(...),
    target_language: str = Query(..., description="Target language for translation"),
    source_language: Optional[str] = None,
    auto_detect: bool = True,
    voice_gender: str = "female"
):


    """Translate speech from one language to another with audio output."""
    try:
        logger.info("Receiving speech translation request")
        logger.info(f"Source language: {source_language}, Target language: {target_language}")
        
        contents = await audio.read()
        
        if not contents:
            raise ValueError("Empty audio file received")
            
        logger.info(f"Received audio file of size: {len(contents)} bytes")
        logger.info(f"Audio content type: {audio.content_type}")
        
        # Initialize speech processor
        speech_processor = MultilingualSpeechProcessor()
        
        # Process speech translation
        result = await speech_processor.translate_speech(
            audio_data=contents,
            source_language=source_language,
            target_language=target_language,
            auto_detect=auto_detect,
            voice_gender=voice_gender
        )
        
        if not result.get("translation", {}).get("text"):
            raise ValueError("No translation was generated")
            
        logger.info(f"Successfully translated speech")
        logger.info(f"Source language: {result['original']['language_name']}")
        logger.info(f"Target language: {result['translation']['language_name']}")
        
        return JSONResponse(
            content={
                "status": "success",
                "original": {
                    "text": result["original"]["text"],
                    "language": {
                        "code": result["original"]["language"],
                        "name": result["original"]["language_name"],
                        "confidence": result["original"]["confidence"]
                    }
                },
                "translation": {
                    "text": result["translation"]["text"],
                    "audio": result["translation"]["audio"],
                    "language": {
                        "code": result["translation"]["language"],
                        "name": result["translation"]["language_name"]
                    }
                },
                "metadata": {
                    "was_auto_detected": auto_detect and source_language is None,
                    "voice_gender": voice_gender,
                    "timestamp": datetime.utcnow().isoformat(),
                    "audio_format": audio.content_type
                }
            }
        )
    except ValueError as ve:
        logger.error(f"Validation error in speech translation: {str(ve)}")
        raise HTTPException(
            status_code=400, 
            detail={
                "error": str(ve),
                "type": "validation_error"
            }
        )
    except RuntimeError as re:
        logger.error(f"Runtime error in speech translation: {str(re)}")
        raise HTTPException(
            status_code=503, 
            detail={
                "error": str(re),
                "type": "service_error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in speech translation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": "system_error"
            }
        )
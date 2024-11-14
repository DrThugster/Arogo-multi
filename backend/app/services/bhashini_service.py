# backend/app/utils/bhashini_service.py
from typing import Dict, Optional
import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

class BhashiniService:
    def __init__(self):
        self.api_key = os.getenv("BHASHINI_API_KEY")
        self.base_url = "https://bhashini.gov.in/api/v1"
        self.supported_languages = {
            "hi": "Hindi",
            "en": "English",
            "ta": "Tamil",
            "te": "Telugu",
            "kn": "Kannada",
            "bn": "Bengali",
            "ml": "Malayalam",
            "mr": "Marathi",
            "gu": "Gujarati",
            "pa": "Punjabi",
            "as": "Assamese",
            "bo": "Bodo",
            "mni": "Manipuri",
            "or": "Odia",
            "raj": "Rajasthani",
            "ur": "Urdu"
        }

    async def get_auth_token(self) -> str:
        """Get Bhashini authentication token."""
        async with aiohttp.ClientSession() as session:
            auth_url = f"{self.base_url}/auth"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            async with session.post(auth_url, headers=headers) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        return data["access_token"]
                    except aiohttp.ContentTypeError:
                        text = await response.text()
                        raise Exception(f"Invalid response format: {text}")
                raise Exception(f"Auth failed with status {response.status}")


    async def get_supported_languages(self) -> Dict:
        """Get supported languages from Bhashini API."""
        token = await self.get_auth_token()
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/languages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                return {"stt": [], "tts": [], "translation": []}
    
    
    async def speech_to_text(self, audio_data: bytes, source_language: str) -> str:
        """Convert speech to text using Bhashini API."""
        token = await self.get_auth_token()
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/speech/recognize"
            
            # Prepare request payload
            payload = {
                "audioContent": audio_data.decode('utf-8'),
                "config": {
                    "languageCode": source_language,
                    "audioEncoding": "WEBM_OPUS"
                }
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["transcript"]
                raise Exception(f"Speech to text failed: {response.status}")

    async def text_to_speech(self, text: str, target_language: str, gender: str = "FEMALE", style: Optional[str] = None) -> bytes:
        """Convert text to speech using Bhashini API."""
        token = await self.get_auth_token()
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/speech/synthesize"
            
            payload = {
                "input": text,
                "config": {
                    "languageCode": target_language,
                    "gender": gender.upper()
                }
            }
            if style:
                payload["config"]["style"] = style
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["audioContent"].encode('utf-8')
                raise Exception(f"Text to speech failed: {response.status}")

    async def translate_text(
        self, 
        text: str, 
        source_language: str, 
        target_language: str
    ) -> str:
        """Translate text between languages."""
        token = await self.get_auth_token()
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/translate"
            
            payload = {
                "input": text,
                "sourceLanguage": source_language,
                "targetLanguage": target_language
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["translation"]
                raise Exception(f"Translation failed: {response.status}")
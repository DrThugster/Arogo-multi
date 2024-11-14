# backend/app/utils/response_validator.py
from typing import Dict, List, Optional, Tuple
import re
from app.utils.translation_cache import TranslationCache
import logging

logger = logging.getLogger(__name__)

class AIResponseValidator:
    def __init__(self):
        self.translation_cache = TranslationCache()
        self.required_patterns = {
            'symptom_mention': r'symptom|pain|discomfort|feeling|condition',
            'confidence_score': r'\[Confidence:\s*(\d+)%\]',
            'recommendation': r'\[Recommendation:.*?\]',
            'emergency_keywords': r'emergency|immediate|urgent|serious|severe',
        }
        
        # Medical terms that should not be translated
        self.preserve_terms = [
            'COVID-19', 'diabetes', 'hypertension', 'ECG', 'MRI', 'CT scan',
            # Add more medical terms that should stay in English
        ]

    async def validate_response(
        self, 
        response: str, 
        source_language: str = "en",
        target_language: Optional[str] = None
    ) -> Tuple[bool, str, Dict]:
        """Validate and clean response with language support."""
        try:
            # Extract confidence scores and other metadata
            confidence_matches = re.finditer(self.required_patterns['confidence_score'], response)
            confidence_scores = [int(match.group(1)) for match in confidence_matches]

            # Check for emergency keywords
            has_emergency = any(re.search(self.required_patterns['emergency_keywords'], response, re.IGNORECASE))

            # Extract recommendations
            recommendations = re.findall(r'\[Recommendation:(.*?)\]', response)

            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

            # Structure the response
            processed_response = {
                'main_response': re.sub(r'\[.*?\]', '', response).strip(),
                'confidence_scores': confidence_scores,
                'recommendations': [rec.strip() for rec in recommendations],
                'requires_emergency': has_emergency,
                'average_confidence': avg_confidence
            }

            # Handle translations if needed
            if target_language and target_language != source_language:
                processed_response = await self._handle_translation(
                    processed_response,
                    source_language,
                    target_language
                )

            return True, "", processed_response

        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            return False, str(e), {}

    async def _handle_translation(
        self,
        response_dict: Dict,
        source_language: str,
        target_language: str
    ) -> Dict:
        """Handle translations while preserving medical terms."""
        try:
            main_text = response_dict['main_response']

            # Preserve medical terms
            preserved_terms = {}
            for term in self.preserve_terms:
                if term.lower() in main_text.lower():
                    placeholder = f"__MEDICAL_TERM_{len(preserved_terms)}__"
                    preserved_terms[placeholder] = term
                    main_text = main_text.replace(term, placeholder)

            # Check cache first
            cached_translation = await self.translation_cache.get_cached_translation(
                main_text,
                source_language,
                target_language
            )

            if cached_translation:
                translated_text = cached_translation
            else:
                # Translate and cache
                translated_text = await self._translate_and_cache(
                    main_text,
                    source_language,
                    target_language
                )

            # Restore preserved terms
            for placeholder, term in preserved_terms.items():
                translated_text = translated_text.replace(placeholder, term)

            response_dict['main_response'] = translated_text
            response_dict['translation_info'] = {
                'source_language': source_language,
                'target_language': target_language,
                'preserved_terms': list(preserved_terms.values()),
                'was_cached': bool(cached_translation)
            }

            return response_dict

        except Exception as e:
            logger.error(f"Error handling translation: {str(e)}")
            return response_dict

    async def _translate_and_cache(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str:
        """Translate text and cache the result."""
        try:
            # Translation would be handled by Bhashini service
            translated_text = text  # Replace with actual translation call

            # Cache the translation
            await self.translation_cache.cache_translation(
                text,
                translated_text,
                source_language,
                target_language
            )

            return translated_text
        except Exception as e:
            logger.error(f"Error in translation: {str(e)}")
            return text

    def enhance_response(self, response: Dict) -> str:
        """Enhance the response with proper formatting and additional context."""
        enhanced = response['main_response']

        # Add confidence context if scores are low
        if response['average_confidence'] < 70:
            enhanced += "\n\nPlease note: This assessment is based on limited information. A medical professional can provide a more accurate evaluation."

        # Add emergency warning if detected
        if response['requires_emergency']:
            enhanced = "⚠️ IMPORTANT: Based on your symptoms, immediate medical attention may be required.\n\n" + enhanced

        # Add recommendations
        if response['recommendations']:
            enhanced += "\n\nRecommendations:\n" + "\n".join(f"• {rec}" for rec in response['recommendations'])

        return enhanced
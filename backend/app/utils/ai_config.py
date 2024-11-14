# backend/app/utils/ai_config.py
import google.generativeai as genai
from typing import Dict, List
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class GeminiConfig:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.initialize_model()
        
    def initialize_model(self):
        """Initialize and configure the Gemini model"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name='gemini-pro',
                generation_config={
                    'temperature': 0.3,  # Lower temperature for more focused medical responses
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 256,
                }
            )
            logger.info("Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise

    def validate(self) -> bool:
        """Validate the model configuration"""
        try:
            # Test generation with a simple prompt
            response = self.model.generate_content("Test connection")
            return True
        except Exception as e:
            logger.error(f"Model validation failed: {str(e)}")
            return False

    def get_safety_config(self) -> List[Dict]:
        """Get safety configuration for the model"""
        return [
            {
                "category": "HARM_CATEGORY_MEDICAL",
                "threshold": "BLOCK_NONE"  # Allow medical content
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS",
                "threshold": "BLOCK_HIGH"  # Block dangerous content
            }
        ]

class MedicalPromptManager:
    @staticmethod
    def get_consultation_prompt(user_details: Dict) -> str:
        """Generate the initial consultation prompt"""
        return f"""
        You are a medical pre-diagnosis assistant analyzing symptoms for a {user_details['age']}-year-old {user_details['gender']}.
        
        Key responsibilities:
        1. Ask focused follow-up questions about symptoms
        2. Maintain symptom severity tracking
        3. Calculate confidence scores for each reported symptom
        4. Suggest preliminary guidance based on symptoms
        5. Recommend appropriate medical attention timing

        Rules:
        - Be professional and empathetic
        - Ask one question at a time
        - Don't make definitive diagnoses
        - If symptoms are severe, immediately recommend emergency care
        - Include confidence scores (0-100%) for symptom assessments
        - Always emphasize this is preliminary guidance only

        Format responses as:
        1. Response to patient
        2. [Confidence Score] for each mentioned symptom
        3. [Action Recommendation] if needed
        4. [Emergency: YES/NO] if applicable
        """

    @staticmethod
    def get_refinement_prompt(symptoms: List[Dict]) -> str:
        """Generate the symptom refinement prompt"""
        symptoms_text = "\n".join([f"- {s['name']}: Intensity {s['intensity']}/10" for s in symptoms])
        return f"""
        Analyze the following symptoms and provide:
        1. Confidence score for each symptom (0-100%)
        2. Possible related conditions (without making definitive diagnoses)
        3. Recommended follow-up questions

        Symptoms:
        {symptoms_text}

        Format the response in a clear, structured manner.
        Include [Emergency: YES] if immediate medical attention is recommended.
        """
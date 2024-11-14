# backend/app/utils/chatbot.py
import google.generativeai as genai
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')

class MedicalChatbot:
    def __init__(self):
        self.context = []
        self.initial_prompt = """
        You are a medical pre-diagnosis assistant. Your role is to:
        1. Ask relevant follow-up questions about symptoms
        2. Gather comprehensive information about the patient's condition
        3. Provide preliminary guidance and suggestions
        4. Recommend when to seek professional medical help
        
        Important rules:
        - Always maintain a professional and empathetic tone
        - Ask one question at a time
        - Don't make definitive diagnoses
        - Emphasize the importance of professional medical consultation
        - If symptoms are severe, immediately recommend seeking emergency care
        """

    async def process_message(self, message: str, user_details: Dict) -> str:
                self.context.append({"role": "user", "content": message})
                context_text = self._prepare_context(user_details)
                
                prompt = f"""
                You are a medical assistant having a focused conversation. 
                
                Key rules:
                1. Ask only ONE question at a time
                2. Wait for the patient's response before proceeding
                3. Keep responses concise and focused
                4. If multiple questions are needed, ask the most important one first
                
                Previous context:
                {context_text}
                
                Current message: {message}
                
                Provide a single, focused response or question.
                """
                
                response = model.generate_content(prompt)
                formatted_response = self._format_response(response.text)
                self.context.append({"role": "assistant", "content": formatted_response})
                
                return formatted_response



    def _prepare_context(self, user_details: Dict) -> str:
        """
        Prepare context for Gemini API including user details and conversation history.
        """
        context = self.initial_prompt + "\n\nPatient Details:\n"
        context += f"Age: {user_details['age']}\n"
        context += f"Gender: {user_details['gender']}\n"
        context += f"Previous conversation:\n"

        # Add last 5 exchanges for context
        for msg in self.context[-10:]:
            role = "Patient" if msg["role"] == "user" else "Assistant"
            context += f"{role}: {msg['content']}\n"

        return context

    def _format_response(self, response: str) -> str:
        """
        Format and clean the AI response.
        """
        # Remove any AI role-playing prefixes
        response = response.replace("Assistant:", "").replace("AI:", "").strip()

        # Ensure response doesn't make definitive diagnoses
        disclaimers = [
            "Based on the information provided, it seems",
            "Your symptoms might indicate",
            "It would be advisable to",
        ]

        for disclaimer in disclaimers:
            if disclaimer.lower() in response.lower():
                break
        else:
            response = "Based on the information provided, " + response

        return response

    def get_chat_summary(self) -> List[Dict]:
        """
        Return the chat history for summary generation.
        """
        return self.context

import google.generativeai as genai
import json
from config import config

def check_code_intent(prompt: str) -> dict:
    try:
        genai.configure(api_key=config['default'].GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        meta_prompt = (
            "You are a specialized AI intent classifier. "
            "Determine if the given user request is related to software/code generation. "
            "Return ONLY valid JSON in the following format: "
            '{"is_code_related": true/false, "reason": "Short explanation"}'
            f"\nUser request: {prompt}"
        )
        
        response = model.generate_content(meta_prompt)
        response_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(response_text)
    
    except Exception as e:
        return {
            "is_code_related": False,
            "reason": f"Error processing intent: {str(e)}"
        }
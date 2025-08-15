
import google.generativeai as genai
import json
from config import config

def improve_prompt(prompt: str) -> dict:
    try:
        genai.configure(api_key=config['default'].GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        meta_prompt = (
            "You are a senior AI prompt engineer. "
            "Rewrite the following user request into a rigorous, step-by-step software development execution plan that instructs a coding model to produce CODE ONLY. "
            "No explanations, no markdown, no commentary, and absolutely no text outside JSON. "
            "Output ONLY valid JSON in the exact format below (no extra text, no code fences): "
            '{"improved_prompt": "Detailed rewritten prompt focused only on writing code", '
            '"steps": [{"step_number": 1, "title": "Short title", "details": "Full technical step description", "deliverables": "Expected code deliverables"}]}'
            "\nStrict requirements:\n"
            "- Language: English only.\n"
            "- Choose the number of steps based on project complexity. If feasible in one pass, use ONE step that generates MULTIPLE folders and files with their full code. If the project is larger, split into multiple steps; in EVERY step, permit and instruct generating MULTIPLE folders and files with complete code.\n"
            "- Fill missing requirements with sensible, industry-standard assumptions and state them succinctly in 'details'.\n"
            "- JSON must be a single object with exactly the keys shown; 'step_number' starts at 1 and increments by 1; no trailing commas; no extra keys; no null/empty values.\n"
            "- If the request is ambiguous, make pragmatic choices and proceed—do not ask questions.\n"
            "- For step_number > 1, in 'details', explicitly state that all code from previous steps is already generated and must not be re-emitted. "
            "Include a concise summary of what was completed in all previous steps before describing the new work for this step.\n"
            "- Ensure that each subsequent step builds only on what remains pending, continuing seamlessly from the last generated code."
            f"\nUser request: {prompt}"
        )

        response = model.generate_content(meta_prompt)
        response_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(response_text)
    
    except Exception as e:
        return {
            "improved_prompt": prompt,
            "steps": [{
                "step_number": 1,
                "title": "Error Handling",
                "details": f"Failed to improve prompt: {str(e)}",
                "deliverables": "None"
            }]
        }
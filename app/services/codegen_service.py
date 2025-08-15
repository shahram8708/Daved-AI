import google.generativeai as genai
import json
import os
import re
from time import sleep
from datetime import datetime
from config import config
from app import db
from app.models import ProjectStep, CodeFile



def _strip_code_fences(s: str) -> str:
    if not s:
        return s
    s = s.strip()
    if s.startswith("```"):
        s = s.lstrip("`")
        first_brace = s.find("{")
        if first_brace != -1:
            s = s[first_brace:]
        s = s.rstrip("`").strip()
    if s.lower().startswith("json"):
        s = s[4:].lstrip("\n").lstrip()
    return s

def _sanitize_json_string(s: str) -> str:
    if not s:
        return s
    s = s.replace("\x00", "")
    def escape_in_string(m):
        content = m.group(0)
        content = re.sub(r'(?<!\\)\\(?![btnfr"\\/])', r'\\\\', content)
        content = content.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        return content
    return re.sub(r'".*?(?<!\\)"', escape_in_string, s, flags=re.S)

def _extract_text_from_gemini(response):
    try:
        if getattr(response, "text", None):
            return response.text
        if hasattr(response, "candidates") and response.candidates:
            parts = []
            for c in response.candidates:
                if getattr(c, "content", None) and getattr(c.content, "parts", None):
                    for p in c.content.parts:
                        t = getattr(p, "text", None)
                        if t:
                            parts.append(t)
            if parts:
                return "\n".join(parts)
    except Exception as e:
        print(f"[ERROR] _extract_text_from_gemini failed: {e}")
    return ""

def _make_model():
    genai.configure(api_key=config['default'].GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
        )
    except TypeError:
        
        model = genai.GenerativeModel("gemini-2.5-flash")
    return model

def _call_gemini_json(model, prompt_text, use_schema=False):
    try:
        resp = model.generate_content(prompt_text)
        
        try:
            if hasattr(resp, "candidates") and resp.candidates:
                fr = getattr(resp.candidates[0], "finish_reason", None)
                if str(fr).upper() == "SAFETY":
                    raise RuntimeError("Gemini blocked by safety.")
        except Exception:
            pass
        txt = _extract_text_from_gemini(resp)
        return txt or ""
    except Exception as e:
        print(f"[WARN] _call_gemini_json failed (schema={use_schema}): {e}")
        return ""



def _filter_relevant_context(step_text, code_context_dict, max_files=10, max_lines_per_file=500):
    if not code_context_dict:
        return None

    step_lower = step_text.lower()
    relevant_files = []

    
    for path in code_context_dict.keys():
        if os.path.basename(path).lower() in step_lower or os.path.dirname(path).lower() in step_lower:
            relevant_files.append(path)

    
    if not relevant_files:
        relevant_files = list(code_context_dict.keys())[-max_files:]

    
    reduced_parts = []
    for path in relevant_files:
        code = code_context_dict[path]
        lines = code.splitlines()
        if len(lines) > max_lines_per_file:
            head = "\n".join(lines[:max_lines_per_file//2])
            tail = "\n".join(lines[-max_lines_per_file//2:])
            code = head + "\n... [FILE_TRUNCATED] ...\n" + tail
        reduced_parts.append(f"// FILE: {path}\n{code}")

    return "\n\n".join(reduced_parts)

def generate_step(project_id, step_id, step_details):
    step = None
    try:
        model = _make_model()

        
        step = ProjectStep.query.get(step_id)
        if not step:
            return {"success": False, "message": "Step not found"}

        
        step.status = 'in-progress'
        if hasattr(step, "updated_at"):
            step.updated_at = datetime.utcnow()
        db.session.commit()

        
        step_text = (step_details or "").strip()
        if not step_text:
            fallback_bits = []
            if (step.details or "").strip():
                fallback_bits.append(step.details.strip())
            if (step.title or "").strip():
                fallback_bits.append(f"Title: {step.title.strip()}")
            if getattr(step, "deliverables", None) and (step.deliverables or "").strip():
                fallback_bits.append(f"Deliverables: {step.deliverables.strip()}")
            step_text = "\n".join(fallback_bits).strip() or f"Implement step #{step.step_number}"

        prompt_parts = [
            "You are a senior AI coding assistant. Your task is to generate code based on the provided step details.",
            "Implement ONLY the step described in STEP DETAILS as code. Do not summarize or explain.",
            "Return ONLY valid minified JSON on a single line (no markdown, no code fences, no comments, no trailing commas).",
            'Schema: {"files":[{"folder":"path/to/folder","file":"filename.ext","code":"<file contents>"}],'
            '"instructions":["Instruction 1","Instruction 2"]}',
            "Multi-file policy: generate MULTIPLE folders and MULTIPLE files in THIS SINGLE RESPONSE as required by STEP DETAILS. Every file must be fully implemented—do not skip or stub. Paths must be coherent and consistent across the project.",
            "Emit only new or modified files whose code is final and future-proof (no further edits required), never re-emit unchanged files, and ensure each emitted file is fully complete, compilable, and integrated end-to-end.",
            "",
            f"STEP DETAILS:\n{step_text}"
            ]
        
        prompt_parts += [
            "",
            "CONTINUATION RULES:",
            "Code for all previous steps has already been generated.",
            "Now, you must only write the code that comes after the point where the existing code ends.",
            "You must automatically determine which parts are already complete and which parts are still pending.",
            "Emit only: (1) brand-new folders/files, and (2) full-file replacements only where changes are required by STEP DETAILS.",
            "When updating a file, output the entire updated file (not a diff) with all imports/types; keep APIs/contracts stable unless STEP DETAILS requires changes—then update all impacted call sites.",
            "Return ONLY valid minified JSON as per the Schema."
        ]

        prompt = "\n".join(prompt_parts)

        print(f"[DEBUG] Prompt -> step {step.step_number} chars={len(prompt)}")

        
        attempts = [
            {"schema": False},
            {"schema": False},
            {"schema": True},
        ]

        response_text = ""
        for i, cfg in enumerate(attempts, start=1):
            print(f"[DEBUG] Gemini call attempt {i} (schema={cfg['schema']}) for step {step.step_number}")
            response_text = _call_gemini_json(model, prompt, use_schema=cfg["schema"])
            if response_text and _try_quick_json_ok(response_text):
                break
            sleep(1.2 * i)  

        if not response_text or not response_text.strip():
            raise ValueError("Model returned empty output after retries/repair.")

        
        cleaned = _strip_code_fences(response_text)
        sanitized = _sanitize_json_string(cleaned)

        code_data = None
        try:
            code_data = json.loads(sanitized)
        except json.JSONDecodeError:
            first = sanitized.find("{")
            last = sanitized.rfind("}")
            if first != -1 and last != -1 and last > first:
                substring = _sanitize_json_string(sanitized[first:last + 1])
                code_data = json.loads(substring)
            else:
                
                print(f"[WARN] JSON parse fail, saving raw for step {step.step_number}")
                raw_code = response_text.strip()
                temp_dir = os.path.join(config['default'].TEMP_PROJECTS_DIR, f"project_{project_id}")
                os.makedirs(temp_dir, exist_ok=True)
                file_path = os.path.join(temp_dir, f"step_{step.step_number}_raw.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(raw_code)
                new_file = CodeFile(
                    project_id=project_id,
                    step_id=step_id,
                    folder_path="",
                    file_name=f"step_{step.step_number}_raw.txt",
                    file_content=raw_code
                )
                db.session.add(new_file)
                step.status = 'completed'
                if hasattr(step, "updated_at"):
                    step.updated_at = datetime.utcnow()
                db.session.commit()
                return {"success": True, "data": {"files": [], "raw": raw_code}}

        if not isinstance(code_data, dict):
            raise ValueError("Parsed response is not a JSON object.")

        
        files = code_data.get("files", [])
        if files and not isinstance(files, list):
            files = [files]
            code_data["files"] = files

        if not files or not any((fi.get("file") or "").strip() for fi in files):
            raise ValueError("Model JSON did not include any files.")

        
        temp_dir = os.path.join(config['default'].TEMP_PROJECTS_DIR, f"project_{project_id}")
        os.makedirs(temp_dir, exist_ok=True)

        for file_info in files:
            folder = (file_info.get('folder') or "").strip().strip("/\\")
            filename = (file_info.get('file') or "").strip()
            code = file_info.get('code') or ""
            if not filename:
                continue

            
            full_dir = os.path.join(temp_dir, folder) if folder else temp_dir
            os.makedirs(full_dir, exist_ok=True)
            file_path = os.path.join(full_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            
            existing = CodeFile.query.filter_by(
                project_id=project_id,
                folder_path=folder,
                file_name=filename
            ).first()

            if existing:
                
                merged_code = (existing.file_content or "") + "\n" + code
                existing.file_content = merged_code
                existing.step_id = step_id
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(merged_code)
            else:
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                db.session.add(CodeFile(
                    project_id=project_id,
                    step_id=step_id,
                    folder_path=folder,
                    file_name=filename,
                    file_content=code
                ))

        step.status = 'completed'
        if hasattr(step, "updated_at"):
            step.updated_at = datetime.utcnow()
        db.session.commit()

        return {"success": True, "data": code_data}

    except Exception as e:
        print(f"[ERROR] generate_step failed: {e}")
        try:
            if step:
                step.status = 'failed'
                if hasattr(step, "updated_at"):
                    step.updated_at = datetime.utcnow()
                db.session.commit()
        except Exception as _e2:
            print(f"[ERROR] Could not mark step failed: {_e2}")
        return {"success": False, "message": str(e)}



def _try_quick_json_ok(s: str) -> bool:
    try:
        cleaned = _strip_code_fences(s or "")
        sanitized = _sanitize_json_string(cleaned)
        obj = json.loads(sanitized)
        if not isinstance(obj, dict):
            return False
        files = obj.get("files", [])
        if files and not isinstance(files, list):
            return True  
        return bool(files)
    except Exception:
        return False

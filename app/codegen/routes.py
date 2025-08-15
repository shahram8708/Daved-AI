from flask import render_template, request, jsonify, url_for, current_app, send_from_directory
import os
from flask_login import login_required, current_user
from app import db
from app.models import Project, ProjectStep
from app.utils.intent_utils import check_code_intent
from app.utils.prompt_improver import improve_prompt
from app.services.codegen_service import generate_step
from app.services.zip_service import create_project_zip, recreate_project_from_db
from datetime import datetime
import threading
from app.codegen import codegen
from flask import after_this_request
import shutil
import json

@codegen.route('/')
@login_required
def index():
    return render_template('codegen/index.html')


def _normalize_deliverables(value):
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    
    if not isinstance(value, str):
        return str(value)
    return value

@codegen.route('/generate', methods=['POST'])
@login_required
def generate_code():
    print("[DEBUG] Received /generate POST request")

    data = request.get_json(silent=True) or {}
    print(f"[DEBUG] Raw request data: {data}")

    prompt = (data.get('prompt') or '').strip()
    print(f"[DEBUG] Extracted prompt: '{prompt}'")

    if not prompt:
        print("[DEBUG] No prompt provided, returning 400")
        return jsonify({"success": False, "message": "Prompt is required"}), 400

    
    print("[DEBUG] Checking if prompt is code-related")
    intent_result = check_code_intent(prompt)
    print(f"[DEBUG] Intent check result: {intent_result}")

    if not intent_result.get('is_code_related', False):
        print("[DEBUG] Prompt not code-related, returning 400")
        return jsonify({
            "success": False,
            "message": "⚠️ This section only generates code.",
            "reason": intent_result.get('reason', 'Not code-related')
        }), 400

    
    print("[DEBUG] Improving prompt")
    improved_data = improve_prompt(prompt)
    print(f"[DEBUG] Improved prompt data: {improved_data}")

    project = Project(
        user_id=current_user.id,
        title=f"Project {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        original_prompt=prompt,
        improved_prompt=improved_data.get('improved_prompt', ''),
        status='in-progress'
    )
    db.session.add(project)
    db.session.commit()
    print(f"[DEBUG] Project created with ID: {project.id}")

    
    steps = improved_data.get('steps', [])
    print(f"[DEBUG] Creating {len(steps)} project steps")
    for step_data in steps:
        deliverables_value = _normalize_deliverables(step_data.get('deliverables'))

        step = ProjectStep(
            project_id=project.id,
            step_number=step_data.get('step_number', 1),
            title=step_data.get('title', 'Untitled Step'),
            details=step_data.get('details', ''),
            deliverables=deliverables_value,   
            status='pending'
        )
        db.session.add(step)
        print(f"[DEBUG] Added step: {step.title} (Step number {step.step_number}) | deliverables type: {type(deliverables_value).__name__}")

    db.session.commit()
    print("[DEBUG] All steps committed to the database")

    def background_generation(app, project_id):
        with app.app_context():
            print(f"[DEBUG] Starting background generation for project ID: {project_id}")
            project = Project.query.get(project_id)
            if not project:
                print(f"[DEBUG] Project {project_id} not found")
                return

            
            steps_local = ProjectStep.query.filter_by(project_id=project.id).order_by(ProjectStep.step_number.asc()).all()
            print(f"[DEBUG] Number of steps to process: {len(steps_local)}")

            any_failed = False

            for idx, step_row in enumerate(steps_local, start=1):
                try:
                    
                    step = ProjectStep.query.get(step_row.id)
                    if not step:
                        print(f"[WARN] Step id {step_row.id} disappeared; skipping")
                        any_failed = True
                        continue

                    print(f"[DEBUG] === PIPELINE STEP {step.step_number} / {len(steps_local)}: {step.title} ===")

                    
                    step_text = (step.details or "").strip()
                    if not step_text:
                        fallback_bits = []
                        if step.title:
                            fallback_bits.append(f"Title: {step.title}")
                        if getattr(step, "deliverables", None):
                            fallback_bits.append(f"Deliverables: {step.deliverables}")
                        step_text = "\n".join(fallback_bits).strip() or f"Implement step #{step.step_number}"

                    print(f"[DEBUG] Step {step.step_number} details length: {len(step_text)}")

                    
                    result = generate_step(
                        project_id=project.id,
                        step_id=step.id,
                        step_details=step_text
                    )

                    if not result.get("success"):
                        any_failed = True
                        print(f"[ERROR] Step {step.step_number} failed: {result.get('message')}")
                        
                        continue

                    
                    for file_info in result["data"].get("files", []):
                        folder = (file_info.get("folder") or "").strip().strip("/\\")
                        filename = (file_info.get("file") or "").strip()
                        file_code = file_info.get("code", "")
                        if not filename:
                            continue
                        full_path = os.path.join(folder, filename) if folder else filename

                    print(f"[DEBUG] Step {step.step_number} completed; files aggregated: {len(result['data'].get('files', []))}")

                except Exception as e:
                    any_failed = True
                    print(f"[ERROR] Unexpected error in step {step_row.step_number}: {e}")
                    
                    try:
                        step = ProjectStep.query.get(step_row.id)
                        if step:
                            step.status = "failed"
                            if hasattr(step, "updated_at"):
                                step.updated_at = datetime.utcnow()
                            db.session.commit()
                    except Exception as _e2:
                        print(f"[ERROR] Failed to mark step as failed: {_e2}")

            
            project = Project.query.get(project_id)
            if project:
                project.status = "failed" if any_failed else "completed"
                db.session.commit()
                print(f"[DEBUG] Project marked as {project.status}")

                if project.status == "completed":
                    try:
                        print("[DEBUG] Creating project ZIP")
                        create_project_zip(project.id)
                        print("[DEBUG] Project ZIP created")
                    except Exception as zip_e:
                        print(f"[WARN] ZIP creation failed: {zip_e}")

            
            try:
                db.session.remove()
            except Exception:
                pass

    app_obj = current_app._get_current_object()
    threading.Thread(
        target=background_generation,
        args=(app_obj, project.id),
        daemon=True
    ).start()
    print("[DEBUG] Background generation thread started")

    response = {
        "success": True,
        "project_id": project.id,
        "progress_url": url_for('codegen.progress', project_id=project.id),
        "steps": [{
            "id": s.id,
            "step_number": s.step_number,
            "title": s.title,
            "status": s.status
        } for s in sorted(project.steps, key=lambda x: x.step_number)]
    }
    print(f"[DEBUG] Response prepared: {response}")

    return jsonify(response)


@codegen.route('/status/<int:project_id>', methods=['GET'])
@login_required
def generate_status(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    steps = [{
        "id": s.id,
        "step_number": s.step_number,
        "title": s.title,
        "status": s.status
    } for s in sorted(project.steps, key=lambda x: x.step_number)]

    zip_dir = current_app.config.get('ZIP_DIR')
    zip_url = None

    if zip_dir and os.path.isdir(zip_dir):
        zip_files = [f for f in os.listdir(zip_dir) if f.startswith(f"project_{project_id}_")]
        if zip_files:
            zip_url = url_for('codegen.download_project', project_id=project_id)

    return jsonify({
        "project_id": project.id,
        "status": project.status,
        "steps": steps,
        "zip_url": zip_url
    })


@codegen.route('/download/<int:project_id>')
@login_required
def download_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        return "Unauthorized", 403

    zip_dir = current_app.config['ZIP_DIR']
    zip_files = [f for f in os.listdir(zip_dir) if f.startswith(f"project_{project_id}_")]

    if not zip_files:
        result = recreate_project_from_db(project_id)
        if not result.get('success'):
            return "Project files not available", 404

        zip_result = create_project_zip(project_id)
        if not zip_result.get('success'):
            return "Failed to create project package", 500

        zip_filename = os.path.basename(zip_result['zip_path'])
    else:
        zip_files.sort(key=lambda x: os.path.getmtime(os.path.join(zip_dir, x)))
        zip_filename = zip_files[-1]

    project_dir = os.path.join(current_app.config['TEMP_PROJECTS_DIR'], f"project_{project_id}")

    @after_this_request
    def _cleanup_project_dir(response):
        try:
            
            
            shutil.rmtree(project_dir, ignore_errors=True)
        except Exception as _cleanup_err:
            current_app.logger.warning(f"Post-download cleanup failed for {project_dir}: {_cleanup_err}")
        return response

    
    try:
        return send_from_directory(
            directory=zip_dir,
            path=zip_filename,
            as_attachment=True,
            download_name=f"{project.title.replace(' ', '_')}.zip"
        )
    except TypeError:
        return send_from_directory(
            directory=zip_dir,
            filename=zip_filename,
            as_attachment=True,
            download_name=f"{project.title.replace(' ', '_')}.zip"
        )


@codegen.route('/progress')
def progress():
    project_id = request.args.get('project_id')
    return render_template('codegen/progress.html', project_id=project_id)

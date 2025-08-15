
import os
import zipfile
import shutil
from datetime import datetime
from config import config
from app import db
from app.models import Project, CodeFile
import tempfile


def create_project_zip(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "message": "Project not found"}

        
        source_dir = os.path.join(config['default'].TEMP_PROJECTS_DIR, f"project_{project_id}")
        if not os.path.isdir(source_dir):
            return {"success": False, "message": f"Source directory not found: {source_dir}"}

        
        zip_dir = config['default'].ZIP_DIR
        os.makedirs(zip_dir, exist_ok=True)

        
        zip_filename = f"project_{project_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.zip"
        zip_path = os.path.join(zip_dir, zip_filename)

        
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)

        
        project.updated_at = datetime.utcnow()
        db.session.commit()

        return {
            "success": True,
            "zip_path": zip_path,
            "zip_filename": zip_filename
        }

    except Exception as e:
        return {"success": False, "message": str(e)}


def recreate_project_from_db(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            return {"success": False, "message": "Project not found"}

        
        temp_dir = os.path.join(config['default'].TEMP_PROJECTS_DIR, f"project_{project_id}")
        os.makedirs(temp_dir, exist_ok=True)

        
        files = CodeFile.query.filter_by(project_id=project_id).all()

        for file in files:
            
            folder_path = file.folder_path or ""
            full_folder = os.path.join(temp_dir, folder_path)
            os.makedirs(full_folder, exist_ok=True)

            
            target_path = os.path.join(full_folder, file.file_name)
            
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(file.file_content or "")

        return {"success": True, "temp_dir": temp_dir}

    except Exception as e:
        return {"success": False, "message": str(e)}

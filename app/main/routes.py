from flask import render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, Project
from app.auth.forms import ProfileForm
from datetime import datetime
import os
import zipfile
import shutil
import tempfile
from config import config
import json
from . import main

@main.route('/')
def index():
    return render_template('index.html')

@main.context_processor
def inject_global_vars():
    return {
        'now': datetime.utcnow()
    }

@main.route('/dashboard')
@login_required
def dashboard(): 
    project_count = Project.query.filter_by(user_id=current_user.id).count()

    
    recent_projects = Project.query.filter_by(user_id=current_user.id)\
        .order_by(Project.created_at.desc())\
        .limit(5).all()

    return render_template(
        'dashboard.html',
        title='Dashboard',
        project_count=project_count,
        projects=recent_projects
    )

@main.route('/projects')
@login_required
def projects():
    projects = Project.query.filter_by(user_id=current_user.id)\
        .order_by(Project.created_at.desc()).all()
    return render_template('projects.html', title='My Projects', projects=projects)

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(
        original_username=current_user.username,
        original_email=current_user.email
    )
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.theme = form.theme.data
        current_user.language = form.language.data
        
        
        if form.new_password.data:
            if current_user.check_password(form.current_password.data):
                current_user.set_password(form.new_password.data)
                flash('Your password has been updated.', 'success')
            else:
                flash('Current password is incorrect.', 'danger')
                return render_template('profile.html', title='Profile', form=form)
        
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('main.profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.theme.data = current_user.theme
        form.language.data = current_user.language
    
    return render_template('profile.html', title='Profile', form=form)

@main.route('/export-data', methods=['POST'])
@login_required
def export_data():
    
    export_dir = tempfile.mkdtemp()
    
    try:
        
        user_data = {
            'username': current_user.username,
            'email': current_user.email,
            'created_at': current_user.created_at.isoformat(),
            'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
            'theme': current_user.theme,
            'language': current_user.language
        }
        with open(os.path.join(export_dir, 'user.json'), 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)
        
        
        projects_dir = os.path.join(export_dir, 'projects')
        os.makedirs(projects_dir, exist_ok=True)
        projects = Project.query.filter_by(user_id=current_user.id).all()
        
        for project in projects:
            project_dir = os.path.join(projects_dir, f"project_{project.id}")
            os.makedirs(project_dir, exist_ok=True)
            
            
            project_data = {
                'title': project.title,
                'original_prompt': project.original_prompt,
                'improved_prompt': project.improved_prompt,
                'status': project.status,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat()
            }
            
            with open(os.path.join(project_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
                        
            
            files_dir = os.path.join(project_dir, 'files')
            os.makedirs(files_dir, exist_ok=True)
            for code_file in project.files:
                file_path = os.path.join(files_dir, code_file.folder_path, code_file.file_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code_file.file_content)
        
        
        media_dir = os.path.join(export_dir, 'media')
        os.makedirs(media_dir, exist_ok=True)
        
        
        zip_filename = f"user_{current_user.id}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(current_app.config['ZIP_DIR'], zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(export_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, export_dir)
                    zipf.write(file_path, arcname)
        
        
        shutil.rmtree(export_dir)
        
        return jsonify({
            'success': True,
            'download_url': url_for('main.download_zip', filename=zip_filename)
        })
    
    except Exception as e:
        
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir)
        
        current_app.logger.error(f"Data export failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to export data. Please try again.'
        }), 500
    
from flask import send_from_directory

@main.route('/download-zip/<path:filename>')
@login_required
def download_zip(filename):
    return send_from_directory(current_app.config['ZIP_DIR'], filename, as_attachment=True)


@main.route('/update-theme', methods=['POST'])
@login_required
def update_theme():
    data = request.get_json()
    theme = data.get('theme', 'light')
    
    if theme not in ['light', 'dark']:
        return jsonify({'success': False}), 400
    
    current_user.theme = theme
    db.session.commit()
    return jsonify({'success': True})
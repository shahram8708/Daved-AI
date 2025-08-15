
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import User, Project, AdminActivity, CodeFile, FeatureFlag, ProjectStep
from app.utils.feature_flags import set_feature_flag
from app.utils.decorators import admin_required, log_activity
from datetime import datetime, timedelta
import json
import csv
from io import StringIO
from . import admin
from sqlalchemy import func

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    
    total_users = User.query.count()
    active_users = User.query.filter(User.last_login >= datetime.utcnow() - timedelta(days=1)).count()
    new_users = User.query.filter(User.created_at >= datetime.utcnow() - timedelta(days=7)).count()
    
    
    total_projects = Project.query.count()
    completed_projects = Project.query.filter_by(status='completed').count()
    
    
    recent_activities = AdminActivity.query.order_by(AdminActivity.timestamp.desc()).limit(10).all()
    
    
    usage_query = Project.query.with_entities(
        Project.status, func.count(Project.id)
    ).group_by(Project.status).all()
    
    usage_data = {status: count for status, count in usage_query}
    
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        active_users=active_users,
        new_users=new_users,
        total_projects=total_projects,
        completed_projects=completed_projects,
        recent_activities=recent_activities,
        usage_data=json.dumps(usage_data),  
        now=datetime.utcnow()
    )

@admin.route('/users')
@login_required
@admin_required
def user_management():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('admin/users.html', users=users)

@admin.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
@log_activity('Toggle admin status', 'user')
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'danger')
        return redirect(url_for('admin.user_management'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    action = 'promoted to admin' if user.is_admin else 'demoted from admin'
    flash(f'User {user.username} has been {action}.', 'success')
    return redirect(url_for('admin.user_management'))

@admin.route('/user/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
@log_activity('Toggle active status', 'user')
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.user_management'))

    user.active = not user.active  
    db.session.commit()

    action = 'activated' if user.active else 'deactivated'
    flash(f'User {user.username} has been {action}.', 'success')
    return redirect(url_for('admin.user_management'))

@admin.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
@log_activity('Delete user', 'user')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.user_management'))
    
    
    Project.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.username} has been deleted.', 'success')
    return redirect(url_for('admin.user_management'))

@admin.route('/projects')
@login_required
@admin_required
def project_management():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    projects = Project.query.order_by(Project.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('admin/projects.html', projects=projects)

@admin.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
@admin_required
@log_activity('Delete project', 'project')
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    
    CodeFile.query.filter_by(project_id=project_id).delete()
    
    
    db.session.delete(project)
    db.session.commit()
    
    flash(f'Project "{project.title}" has been deleted.', 'success')
    return redirect(url_for('admin.project_management'))

@admin.route('/activities')
@login_required
@admin_required
def admin_activities():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    activities = AdminActivity.query.order_by(AdminActivity.timestamp.desc()).paginate(page=page, per_page=per_page)
    return render_template('admin/activities.html', activities=activities)

@admin.route('/feature-flags')
@login_required
@admin_required
def feature_flags():
    flags = FeatureFlag.query.order_by(FeatureFlag.name.asc()).all()
    return render_template('admin/feature_flags.html', flags=flags)

@admin.route('/feature-flag/<int:flag_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_feature_flag(flag_id):
    flag = FeatureFlag.query.get_or_404(flag_id)
    flag.is_enabled = not flag.is_enabled
    db.session.commit()
    flash(f'Feature flag "{flag.name}" has been {"enabled" if flag.is_enabled else "disabled"}', 'success')
    return redirect(url_for('admin.feature_flags', flag=flag))

@admin.route('/feature-flag/create', methods=['POST'])
@login_required
@admin_required
def create_feature_flag():
    name = request.form.get('name')
    description = request.form.get('description')
    new_flag = FeatureFlag(name=name, description=description, is_enabled=False)
    db.session.add(new_flag)
    db.session.commit()
    flash(f'Feature flag "{new_flag.name}" created successfully.', 'success')
    return redirect(url_for('admin.feature_flags'))

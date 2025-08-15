
from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user
from app.models import AdminActivity
from app import db

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def log_activity(action, target_type=None, target_id=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            if current_user.is_authenticated and current_user.is_admin:
                activity = AdminActivity(
                    admin_id=current_user.id,
                    action=action,
                    target_type=target_type,
                    target_id=target_id
                )
                db.session.add(activity)
                db.session.commit()
            return result
        return decorated_function
    return decorator
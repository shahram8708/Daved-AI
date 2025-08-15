
from datetime import datetime
from flask import Flask, render_template
from .utils.monitoring import init_request_monitoring, start_metrics_server
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from config import config
import os
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    csrf.init_app(app)
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from app.cache import cache
    cache.init_app(app)

    from .codegen import codegen as codegen_blueprint
    app.register_blueprint(codegen_blueprint, url_prefix='/codegen')

    from app.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    from app.utils.monitoring import init_request_monitoring
    init_request_monitoring(app)

    
    if app.config.get('ENABLE_METRICS'):
        start_metrics_server()
    
    
    @app.template_filter('time_ago')
    def time_ago_filter(dt):
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 365:
            return f'{diff.days // 365} years ago'
        if diff.days > 30:
            return f'{diff.days // 30} months ago'
        if diff.days > 0:
            return f'{diff.days} days ago'
        if diff.seconds > 3600:
            return f'{diff.seconds // 3600} hours ago'
        if diff.seconds > 60:
            return f'{diff.seconds // 60} minutes ago'
        return 'just now'
    
    @app.route('/')
    def index():
        return "Welcome to the Daved AI!"

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        
        return render_template('errors/500.html'), 500
    
    @app.context_processor
    def inject_theme():
        theme = 'light'
        if current_user.is_authenticated:
            theme = current_user.theme
        return dict(current_theme=theme)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User  
        return User.query.get(int(user_id))
    
    return app

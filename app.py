import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import extensions and models
from extensions import mail, csrf, migrate, db
from models import User

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    from config import config
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')

    # Create database tables
    with app.app_context():
        db.create_all()

        # Create default admin user if not exists
        admin = User.query.filter_by(email='admin@cbt.com').first()
        if not admin:
            admin = User(
                email='admin@cbt.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created: admin@cbt.com / admin123")

    # Context processors
    @app.context_processor
    def inject_config():
        return {
            'app_name': app.config['APP_NAME'],
            'institution_name': app.config['INSTITUTION_NAME']
        }

    # Root route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'student':
                return redirect(url_for('student.dashboard'))
        return redirect(url_for('auth.login'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

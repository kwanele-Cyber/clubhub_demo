from flask import Flask, redirect, url_for
from flask_migrate import Migrate
from flask_mail import Mail
from dotenv import load_dotenv
import os

from app.extensions import db, login_manager, migrate, mail

# Load environment variables from .env file
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuration from environment variables
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///club_management.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Mail configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    
    # Optional: Add debug output to verify configuration (remove in production)
    print("=== App Configuration ===")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Mail Server: {app.config['MAIL_SERVER']}")
    print(f"Mail Username: {app.config['MAIL_USERNAME']}")
    print("=========================")
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Import models after db is initialized to avoid circular imports
    from app.models.user import User
    from app.models.club import Club, Membership
    from app.models.event import Event, EventAttendance
    from app.models.announcement import Announcement
    from app.models.gamification import Contribution, Badge, UserBadge, Leaderboard
    
    # Register blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.clubs import bp as clubs_bp
    from app.routes.events import bp as events_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.dashboard import bp as dashboard_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth') #kwanele
    app.register_blueprint(clubs_bp, url_prefix='/clubs') #user2
    app.register_blueprint(events_bp, url_prefix='/events') #member3
    app.register_blueprint(admin_bp, url_prefix='/admin') #member4
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard') #member5
    
    # Root route
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app
import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from config import Config
from models import db, User

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.tourist_routes import tourist_bp
    from routes.authority_routes import authority_bp
    from routes.public_routes import public_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tourist_bp)
    app.register_blueprint(authority_bp)
    app.register_blueprint(public_bp)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_authority:
                return redirect(url_for('authority.dashboard'))
            return redirect(url_for('tourist.home'))
        return redirect(url_for('auth.login'))

    @app.context_processor
    def inject_context():
        return {
            'now_year': 2026,
            'app_name': 'SafeTrail'
        }

    # Automatically create tables if they don't exist
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    # Default port 5000, debug mode for development
    app.run(host='0.0.0.0', port=5000, debug=True)

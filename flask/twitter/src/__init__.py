import os
from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
from datetime import datetime, timezone

# https://flask.palletsprojects.com/en/2.0.x/patterns/appfactories/


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'postgresql://postgres@localhost:5432/twitter'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=os.environ.get('FLASK_ENV') == 'development',

        # JWT Configuration
        JWT_SECRET_KEY=os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production'),
        JWT_ACCESS_TOKEN_EXPIRES=3600,  # 1 hour
        JWT_REFRESH_TOKEN_EXPIRES=30 * 24 * 3600,  # 30 days

        # Rate Limiting
        RATELIMIT_STORAGE_URL=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),

        # File Upload
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', '/tmp/twitter_uploads'),

        # CORS
        CORS_ORIGINS=os.environ.get('CORS_ORIGINS', '*').split(',')
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions
    from .models import db
    db.init_app(app)
    migrate = Migrate(app, db)

    # Configure CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from .api import users, tweets, notifications, feed
    from .auth import routes as auth_routes

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(tweets.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(feed.bp)

    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }), 503

    # API info endpoint
    @app.route('/api')
    def api_info():
        return jsonify({
            'name': 'Twitter API Clone',
            'version': '2.0.0',
            'description': 'A comprehensive Twitter-like social media API',
            'endpoints': {
                'authentication': '/auth/*',
                'users': '/api/users/*',
                'tweets': '/api/tweets/*',
                'notifications': '/api/notifications/*',
                'feed': '/api/feed/*'
            },
            'documentation': 'See README.md for detailed API documentation'
        })

    return app

from flask import Flask
from flask_login import LoginManager
from models import db, bcrypt, User
from config import Config

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.roadmap import roadmap_bp
    from routes.ide import ide_bp
    from routes.quiz import quiz_bp
    from routes.interview import interview_bp
    from routes.progress import progress_bp
    from routes.course import course_bp
    from routes.chatbot import chatbot_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(roadmap_bp)
    app.register_blueprint(ide_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(course_bp)
    app.register_blueprint(chatbot_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

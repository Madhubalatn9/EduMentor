from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    skill = db.Column(db.String(100), nullable=True)
    level = db.Column(db.String(50), nullable=True, default='Beginner')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    roadmaps = db.relationship('Roadmap', backref='user', lazy=True, cascade='all, delete-orphan')
    coding_sessions = db.relationship('CodingSession', backref='user', lazy=True, cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', backref='user', lazy=True, cascade='all, delete-orphan')
    interview_sessions = db.relationship('InterviewSession', backref='user', lazy=True, cascade='all, delete-orphan')
    courses = db.relationship('Course', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Roadmap(db.Model):
    __tablename__ = 'roadmaps'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class CodingSession(db.Model):
    __tablename__ = 'coding_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    problem_title = db.Column(db.String(200), nullable=False)
    problem_content = db.Column(db.Text, nullable=False)
    user_code = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(50), nullable=True)
    result = db.Column(db.String(50), nullable=True)
    ai_feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    questions = db.Column(db.Text, nullable=False)
    user_answers = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, nullable=True)
    total = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class InterviewSession(db.Model):
    __tablename__ = 'interview_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    questions = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    skill = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    structure = db.Column(db.Text, nullable=False)
    completed_lessons = db.Column(db.Text, default='[]')
    total_lessons = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    lesson_contents = db.relationship('LessonContent', backref='course', lazy=True, cascade='all, delete-orphan')


class LessonContent(db.Model):
    __tablename__ = 'lesson_contents'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    module_id = db.Column(db.Integer, nullable=False)
    lesson_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

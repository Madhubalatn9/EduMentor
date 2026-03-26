from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import Roadmap, CodingSession, Quiz, InterviewSession, Course

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    roadmap_count = Roadmap.query.filter_by(user_id=current_user.id).count()
    coding_count = CodingSession.query.filter_by(user_id=current_user.id).count()
    quiz_count = Quiz.query.filter_by(user_id=current_user.id).count()
    interview_count = InterviewSession.query.filter_by(user_id=current_user.id).count()
    course_count = Course.query.filter_by(user_id=current_user.id).count()

    recent_quizzes = Quiz.query.filter_by(user_id=current_user.id).order_by(Quiz.created_at.desc()).limit(5).all()
    quizzes_with_score = Quiz.query.filter_by(user_id=current_user.id).filter(Quiz.score.isnot(None)).all()
    avg_score = (
        sum(q.score / max(q.total, 1) * 100 for q in quizzes_with_score) / len(quizzes_with_score)
        if quizzes_with_score else 0
    )

    passed_quizzes = sum(1 for q in quizzes_with_score if (q.total and q.score / q.total >= 0.7))

    passed = CodingSession.query.filter_by(user_id=current_user.id, result='passed').count()
    
    all_courses = Course.query.filter_by(user_id=current_user.id).all()
    completed_courses = 0
    import json
    for c in all_courses:
        if c.total_lessons > 0 and c.completed_lessons:
            try:
                comp_list = json.loads(c.completed_lessons)
                if len(comp_list) >= c.total_lessons:
                    completed_courses += 1
            except:
                pass

    stats = {
        'roadmaps': roadmap_count,
        'coding': coding_count,
        'quizzes': quiz_count,
        'interviews': interview_count,
        'courses': course_count,
        'avg_score': round(avg_score, 1),
        'passed': passed,
    }
    return render_template('dashboard.html', stats=stats, recent_quizzes=recent_quizzes, completed_courses=completed_courses, passed_quizzes=passed_quizzes)

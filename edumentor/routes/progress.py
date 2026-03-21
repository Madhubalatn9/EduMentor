from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from models import Roadmap, CodingSession, Quiz, InterviewSession, Course
from datetime import datetime, timedelta
import json

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/progress')
@login_required
def progress():
    return render_template('progress.html')


@progress_bp.route('/api/progress/stats')
@login_required
def get_stats():
    uid = current_user.id
    roadmap_count = Roadmap.query.filter_by(user_id=uid).count()
    coding_count = CodingSession.query.filter_by(user_id=uid).count()
    coding_passed = CodingSession.query.filter_by(user_id=uid, result='passed').count()
    quiz_count = Quiz.query.filter_by(user_id=uid).count()
    interview_count = InterviewSession.query.filter_by(user_id=uid).count()
    course_count = Course.query.filter_by(user_id=uid).count()

    scored_quizzes = Quiz.query.filter_by(user_id=uid).filter(Quiz.score.isnot(None)).all()
    avg_score = (
        sum(q.score / max(q.total, 1) * 100 for q in scored_quizzes) / len(scored_quizzes)
        if scored_quizzes else 0
    )

    # Weekly quiz scores (last 8 weeks)
    weekly_scores = []
    for i in range(7, -1, -1):
        week_start = datetime.utcnow() - timedelta(weeks=i+1)
        week_end = datetime.utcnow() - timedelta(weeks=i)
        week_quizzes = [q for q in scored_quizzes if week_start <= q.created_at <= week_end]
        ws = (
            sum(q.score / max(q.total, 1) * 100 for q in week_quizzes) / len(week_quizzes)
            if week_quizzes else 0
        )
        label = (datetime.utcnow() - timedelta(weeks=i)).strftime('Week %m/%d')
        weekly_scores.append({'label': label, 'score': round(ws, 1)})

    # Activity breakdown
    activity = [
        {'label': 'Roadmaps', 'value': roadmap_count, 'color': '#6366f1'},
        {'label': 'Coding Sessions', 'value': coding_count, 'color': '#8b5cf6'},
        {'label': 'Quizzes', 'value': quiz_count, 'color': '#0ea5e9'},
        {'label': 'Interviews', 'value': interview_count, 'color': '#10b981'},
        {'label': 'Courses', 'value': course_count, 'color': '#06b6d4'},
    ]

    return jsonify({
        'stats': {
            'roadmaps': roadmap_count,
            'coding': coding_count,
            'coding_passed': coding_passed,
            'quizzes': quiz_count,
            'interviews': interview_count,
            'courses': course_count,
            'avg_score': round(avg_score, 1),
        },
        'weekly_scores': weekly_scores,
        'activity': activity
    })

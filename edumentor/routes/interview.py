from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, InterviewSession
from config import Config
from utils import get_groq_client, clean_json, sanitize_input
import json

interview_bp = Blueprint('interview', __name__)


@interview_bp.route('/interview')
@login_required
def interview():
    sessions = InterviewSession.query.filter_by(user_id=current_user.id).order_by(InterviewSession.created_at.desc()).limit(10).all()
    return render_template('interview.html', sessions=sessions)


@interview_bp.route('/api/interview/generate', methods=['POST'])
@login_required
def generate_questions():
    data = request.json
    skill = sanitize_input(data.get('skill', current_user.skill or 'Python'), max_length=100)
    level = sanitize_input(data.get('level', current_user.level or 'Beginner'), max_length=50)
    itype = sanitize_input(data.get('type', 'Technical'), max_length=50)
    count = min(int(data.get('count', 10)), 15)
    prompt = (
        f"Generate {count} {itype} interview questions for {skill} at {level} level. "
        'Return ONLY valid JSON array: '
        '[{"id":1,"question":"...","type":"Technical","difficulty":"Medium",'
        '"answer":"comprehensive model answer","key_points":["..."],"follow_up":"..."}]'
    )
    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer. Return valid JSON array only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=3000
        )
        content = clean_json(resp.choices[0].message.content)
        questions = json.loads(content)
        session_obj = InterviewSession(
            user_id=current_user.id, skill=skill,
            level=level, questions=json.dumps(questions)
        )
        db.session.add(session_obj)
        db.session.commit()
        return jsonify({'success': True, 'questions': questions, 'session_id': session_obj.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@interview_bp.route('/api/interview/evaluate-answer', methods=['POST'])
@login_required
def evaluate_answer():
    data = request.json
    question = data.get('question', '')
    user_answer = data.get('answer', '')
    model_answer = data.get('model_answer', '')
    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": 'You are an expert interviewer. Return JSON only: {"score":0-10,"feedback":"...","strengths":["..."],"improvements":["..."],"grade":"Excellent/Good/Fair/Poor"}'},
                {"role": "user", "content": f"Question: {question}\nModel Answer: {model_answer}\nCandidate Answer: {user_answer}\nEvaluate."}
            ],
            temperature=0.3, max_tokens=800
        )
        content = clean_json(resp.choices[0].message.content)
        return jsonify({'success': True, 'evaluation': json.loads(content)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

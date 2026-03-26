from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Quiz
from config import Config
from utils import get_groq_client, clean_json, sanitize_input
import json

quiz_bp = Blueprint('quiz', __name__)


@quiz_bp.route('/quiz')
@login_required
def quiz():
    history = Quiz.query.filter_by(user_id=current_user.id).order_by(Quiz.created_at.desc()).limit(10).all()
    return render_template('quiz.html', quiz_history=history)


@quiz_bp.route('/api/quiz/generate', methods=['POST'])
@login_required
def generate_quiz():
    data = request.json
    skill = sanitize_input(data.get('skill', current_user.skill or 'Python'), max_length=100)
    level = sanitize_input(data.get('level', current_user.level or 'Beginner'), max_length=50)
    topic = sanitize_input(data.get('topic', ''), max_length=200)
    count = min(int(data.get('count', 10)), 20)
    topic_str = f" focused on {topic}" if topic else ""
    prompt = (
        f"Generate {count} multiple-choice questions{topic_str} for {skill} at {level} level. "
        'Return ONLY a valid JSON array: '
        '[{"id":1,"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],'
        '"correct_answer":"A","explanation":"..."}]'
    )
    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert educator. Return valid JSON array only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=2500
        )
        content = clean_json(resp.choices[0].message.content)
        questions = json.loads(content)
        quiz_obj = Quiz(
            user_id=current_user.id, skill=skill, level=level,
            questions=json.dumps(questions), total=len(questions)
        )
        db.session.add(quiz_obj)
        db.session.commit()
        return jsonify({'success': True, 'questions': questions, 'quiz_id': quiz_obj.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@quiz_bp.route('/api/quiz/submit', methods=['POST'])
@login_required
def submit_quiz():
    data = request.json
    quiz_id = data.get('quiz_id')
    answers = data.get('answers', {})
    quiz_obj = Quiz.query.filter_by(id=quiz_id, user_id=current_user.id).first()
    if not quiz_obj:
        return jsonify({'error': 'Quiz not found'}), 404
    questions = json.loads(quiz_obj.questions)
    score = 0
    results = []
    for q in questions:
        qid = str(q['id'])
        ua = answers.get(qid, '')
        correct = q['correct_answer']
        is_correct = ua.strip().upper().startswith(correct.upper())
        if is_correct:
            score += 1
        results.append({
            'id': q['id'], 'question': q['question'],
            'user_answer': ua, 'correct_answer': correct,
            'correct': is_correct, 'explanation': q['explanation']
        })
    quiz_obj.user_answers = json.dumps(answers)
    quiz_obj.score = score
    db.session.commit()
    return jsonify({
        'success': True, 'score': score,
        'total': len(questions),
        'percentage': round(score / max(len(questions), 1) * 100, 1),
        'results': results
    })


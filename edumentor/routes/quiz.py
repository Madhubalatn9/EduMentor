from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Quiz
from config import Config
from groq import Groq
import json

quiz_bp = Blueprint('quiz', __name__)
client = Groq(api_key=Config.GROQ_API_KEY)


def _clean_json(content):
    """Clean AI response to extract valid JSON."""
    content = content.strip()
    if content.startswith('```'):
        parts = content.split('```')
        if len(parts) >= 3:
            content = parts[1]
        else:
            content = parts[1] if len(parts) > 1 else content
        if content.startswith('json'):
            content = content[4:]
        content = content.strip()
    
    first_brace = content.find('[') if content.strip().startswith('[') else content.find('{')
    last_brace = content.rfind(']') if content.strip().startswith('[') else content.rfind('}')
    
    if first_brace != -1 and last_brace != -1:
        content = content[first_brace:last_brace + 1]
    return content


@quiz_bp.route('/quiz')
@login_required
def quiz():
    history = Quiz.query.filter_by(user_id=current_user.id).order_by(Quiz.created_at.desc()).limit(10).all()
    return render_template('quiz.html', quiz_history=history)


@quiz_bp.route('/api/quiz/generate', methods=['POST'])
@login_required
def generate_quiz():
    data = request.json
    skill = data.get('skill', current_user.skill or 'Python')
    level = data.get('level', current_user.level or 'Beginner')
    topic = data.get('topic', '')
    count = min(int(data.get('count', 10)), 20)
    topic_str = f" focused on {topic}" if topic else ""
    prompt = (
        f"Generate {count} multiple-choice questions{topic_str} for {skill} at {level} level. "
        'Return ONLY a valid JSON array: '
        '[{"id":1,"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],'
        '"correct_answer":"A","explanation":"..."}]'
    )
    try:
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert educator. Return valid JSON array only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=2500
        )
        content = _clean_json(resp.choices[0].message.content)
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

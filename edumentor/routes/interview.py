from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, InterviewSession
from config import Config
from groq import Groq
import json

interview_bp = Blueprint('interview', __name__)
client = Groq(api_key=Config.GROQ_API_KEY)


def _clean_json(content):
    """Clean AI response to extract valid JSON."""
    content = content.strip()
    
    # Handle markdown code blocks
    if content.startswith('```'):
        # Find the first closing ```
        first_closing_fence = content.find('```', 3)
        if first_closing_fence != -1:
            # Extract content between the first opening and closing fences
            extracted_content = content[3:first_closing_fence].strip()
            # If it starts with 'json', remove it
            if extracted_content.lower().startswith('json'):
                content = extracted_content[4:].strip()
            else:
                content = extracted_content
        else:
            # If no closing fence, assume the rest is the content
            content = content[3:].strip()
    
    # Find the first opening brace (either { or [)
    first_brace_curly = content.find('{')
    first_brace_square = content.find('[')
    
    first_brace = -1
    if first_brace_curly != -1 and first_brace_square != -1:
        first_brace = min(first_brace_curly, first_brace_square)
    elif first_brace_curly != -1:
        first_brace = first_brace_curly
    elif first_brace_square != -1:
        first_brace = first_brace_square

    # Find the last closing brace (either } or ])
    last_brace_curly = content.rfind('}')
    last_brace_square = content.rfind(']')

    last_brace = -1
    if last_brace_curly != -1 and last_brace_square != -1:
        last_brace = max(last_brace_curly, last_brace_square)
    elif last_brace_curly != -1:
        last_brace = last_brace_curly
    elif last_brace_square != -1:
        last_brace = last_brace_square
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        content = content[first_brace:last_brace + 1]
    
    return content


@interview_bp.route('/interview')
@login_required
def interview():
    sessions = InterviewSession.query.filter_by(user_id=current_user.id).order_by(InterviewSession.created_at.desc()).limit(10).all()
    return render_template('interview.html', sessions=sessions)


@interview_bp.route('/api/interview/generate', methods=['POST'])
@login_required
def generate_questions():
    data = request.json
    skill = data.get('skill', current_user.skill or 'Python')
    level = data.get('level', current_user.level or 'Beginner')
    itype = data.get('type', 'Technical')
    count = min(int(data.get('count', 10)), 15)
    prompt = (
        f"Generate {count} {itype} interview questions for {skill} at {level} level. "
        'Return ONLY valid JSON array: '
        '[{"id":1,"question":"...","type":"Technical","difficulty":"Medium",'
        '"answer":"comprehensive model answer","key_points":["..."],"follow_up":"..."}]'
    )
    try:
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer. Return valid JSON array only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=3000
        )
        content = _clean_json(resp.choices[0].message.content)
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
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": 'You are an expert interviewer. Return JSON only: {"score":0-10,"feedback":"...","strengths":["..."],"improvements":["..."],"grade":"Excellent/Good/Fair/Poor"}'},
                {"role": "user", "content": f"Question: {question}\nModel Answer: {model_answer}\nCandidate Answer: {user_answer}\nEvaluate."}
            ],
            temperature=0.3, max_tokens=800
        )
        content = _clean_json(resp.choices[0].message.content)
        return jsonify({'success': True, 'evaluation': json.loads(content)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

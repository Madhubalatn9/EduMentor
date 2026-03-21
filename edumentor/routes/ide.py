from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, CodingSession
from config import Config
from groq import Groq
import json
import requests
import base64

ide_bp = Blueprint('ide', __name__)
client = Groq(api_key=Config.GROQ_API_KEY)

LANG_IDS = {
    'python': 71, 'javascript': 63, 'java': 62,
    'cpp': 54, 'c': 50, 'go': 60, 'rust': 73, 'typescript': 74
}

PISTON_LANGS = {
    'python':     ('python',     '3.10.0'),
    'javascript': ('javascript', '18.15.0'),
    'java':       ('java',       '15.0.2'),
    'cpp':        ('c++',        '10.2.0'),
    'c':          ('c',          '10.2.0'),
    'go':         ('go',         '1.16.2'),
    'rust':       ('rust',       '1.50.0'),
    'typescript': ('typescript', '5.0.3'),
}


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


@ide_bp.route('/ide')
@login_required
def ide():
    recent = CodingSession.query.filter_by(user_id=current_user.id).order_by(CodingSession.created_at.desc()).limit(10).all()
    return render_template('ide.html', recent_sessions=recent)


@ide_bp.route('/api/ide/generate-problem', methods=['POST'])
@login_required
def generate_problem():
    data = request.json
    skill = data.get('skill', current_user.skill or 'Python')
    level = data.get('level', current_user.level or 'Beginner')
    topic = data.get('topic', '')
    topic_str = f" on {topic}" if topic else ""
    prompt = (
        f"Generate a coding problem{topic_str} for {skill} at {level} level. "
        'Return ONLY valid JSON: { "title": "...", "difficulty": "...", "description": "...", '
        '"examples": [{"input": "...", "output": "...", "explanation": "..."}], '
        '"constraints": ["..."], "hints": ["..."], '
        '"starter_code": {"python": "def solution():\\n    pass", '
        '"javascript": "function solution() {\\n    // your code\\n}", '
        '"java": "public class Solution {\\n    public static void main(String[] args) {\\n    }\\n}"} }'
    )
    try:
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert programming instructor. Return valid JSON only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8, max_tokens=1500
        )
        content = _clean_json(resp.choices[0].message.content)
        return jsonify({'success': True, 'problem': json.loads(content)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ide_bp.route('/api/ide/execute', methods=['POST'])
@login_required
def execute_code():
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python').lower()
    if not code:
        return jsonify({'error': 'No code provided'}), 400

    # 1. Try Piston API — completely FREE, no key needed
    try:
        lang, version = PISTON_LANGS.get(language, ('python', '3.10.0'))
        ext_map = {'python': 'py', 'javascript': 'js', 'java': 'java',
                   'c++': 'cpp', 'c': 'c', 'go': 'go', 'rust': 'rs', 'typescript': 'ts'}
        ext = ext_map.get(lang, 'txt')
        payload = {
            'language': lang, 'version': version,
            'files': [{'name': f'main.{ext}', 'content': code}],
            'stdin': '', 'args': [], 'compile_timeout': 10, 'run_timeout': 5
        }
        r = requests.post('https://emkc.org/api/v2/piston/execute',
                          json=payload, timeout=15)
        if r.status_code == 200:
            result = r.json()
            run = result.get('run', {})
            stdout = run.get('stdout', '')
            stderr = run.get('stderr', '')
            output = stdout or stderr or 'No output'
            return jsonify({'success': True, 'output': output,
                            'error': stderr if not stdout else '',
                            'status': 'Accepted' if not stderr else 'Runtime Error'})
    except Exception:
        pass

    # 2. RapidAPI Judge0 (if key provided)
    if Config.JUDGE0_API_KEY:
        try:
            headers = {
                'X-RapidAPI-Key': Config.JUDGE0_API_KEY,
                'X-RapidAPI-Host': 'judge0-ce.p.rapidapi.com',
                'Content-Type': 'application/json'
            }
            payload = {
                'language_id': LANG_IDS.get(language, 71),
                'source_code': base64.b64encode(code.encode()).decode(),
                'stdin': '', 'base64_encoded': True
            }
            r = requests.post(f'{Config.JUDGE0_URL}/submissions', headers=headers,
                              json=payload, params={'base64_encoded': 'true', 'wait': 'true'}, timeout=10)
            result = r.json()
            stdout = base64.b64decode(result.get('stdout') or b'').decode('utf-8', errors='replace')
            stderr = base64.b64decode(result.get('stderr') or b'').decode('utf-8', errors='replace')
            compile_out = base64.b64decode(result.get('compile_output') or b'').decode('utf-8', errors='replace')
            return jsonify({'success': True, 'output': stdout,
                            'error': stderr or compile_out,
                            'status': result.get('status', {}).get('description', 'Unknown')})
        except Exception:
            pass

    # 3. Fallback: Groq AI-simulated execution
    try:
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": 'Execute the code mentally and provide the exact output. Return JSON only: {"output": "...", "error": "..."}'},
                {"role": "user", "content": f"Language: {language}\n\nCode:\n{code}"}
            ],
            temperature=0, max_tokens=500
        )
        content = _clean_json(resp.choices[0].message.content)
        result = json.loads(content)
        return jsonify({'success': True, 'output': result.get('output', ''),
                        'error': result.get('error', ''), 'status': 'AI Simulated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ide_bp.route('/api/ide/evaluate', methods=['POST'])
@login_required
def evaluate_solution():
    data = request.json
    code = data.get('code', '')
    problem = data.get('problem', '')
    language = data.get('language', 'python')
    try:
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": 'You are an expert code reviewer. Return JSON only: {"score": 0-100, "correct": true/false, "feedback": "...", "improvements": ["..."], "time_complexity": "...", "space_complexity": "..."}'},
                {"role": "user", "content": f"Problem:\n{problem}\n\nSolution ({language}):\n{code}\n\nEvaluate this solution."}
            ],
            temperature=0.3, max_tokens=1000
        )
        content = _clean_json(resp.choices[0].message.content)
        evaluation = json.loads(content)
        session = CodingSession(
            user_id=current_user.id,
            problem_title=problem[:200],
            problem_content=problem,
            user_code=code,
            language=language,
            result='passed' if evaluation.get('correct') else 'failed',
            ai_feedback=evaluation.get('feedback', '')
        )
        db.session.add(session)
        db.session.commit()
        return jsonify({'success': True, 'evaluation': evaluation})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

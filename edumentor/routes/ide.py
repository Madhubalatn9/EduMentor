from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, CodingSession
from config import Config
from utils import get_groq_client, clean_json, sanitize_input
import json
import requests
import base64
import subprocess
import tempfile
import os
import sys

ide_bp = Blueprint('ide', __name__)

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


@ide_bp.route('/ide')
@login_required
def ide():
    recent = CodingSession.query.filter_by(user_id=current_user.id).order_by(CodingSession.created_at.desc()).limit(10).all()
    return render_template('ide.html', recent_sessions=recent)


@ide_bp.route('/api/ide/generate-problem', methods=['POST'])
@login_required
def generate_problem():
    data = request.json
    skill = sanitize_input(data.get('skill', current_user.skill or 'Python'), max_length=100)
    level = sanitize_input(data.get('level', current_user.level or 'Beginner'), max_length=50)
    topic = sanitize_input(data.get('topic', ''), max_length=200)
    topic_str = f" on {topic}" if topic else ""
    prompt = (
        f"Generate a coding problem{topic_str} for {skill} at {level} level. "
        'Return ONLY valid JSON with these fields: '
        '{ "title": "...", "difficulty": "Easy/Medium/Hard", "description": "clear problem statement", '
        '"examples": [{"input": "...", "output": "...", "explanation": "..."}], '
        '"constraints": ["..."], "hints": ["general approach hints, NOT solution code"], '
        '"starter_code": {"python": "...", "javascript": "...", "java": "..."} }\n\n'
        'CRITICAL RULES for starter_code:\n'
        '- ONLY provide an EMPTY function skeleton with the correct signature\n'
        '- Python: "def function_name(params):\\n    # Write your solution here\\n    pass"\n'
        '- JavaScript: "function functionName(params) {\\n    // Write your solution here\\n}"\n'
        '- Java: "public class Solution {\\n    public static returnType methodName(params) {\\n        // Write your solution here\\n    }\\n}"\n'
        '- NEVER include ANY solution logic, algorithms, or working code\n'
        '- NEVER include loops, conditionals, or calculations in starter_code\n'
        '- The starter_code must ONLY have the function signature + a pass/return placeholder\n\n'
        'CRITICAL RULES for hints:\n'
        '- Give conceptual hints like "Think about using a loop" or "Consider edge cases"\n'
        '- NEVER include actual code, pseudocode, or the solution approach in hints'
    )
    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are an expert programming instructor who creates coding challenges. "
                    "You MUST return valid JSON only, no markdown. "
                    "NEVER include the solution in starter_code. Starter code must ONLY have "
                    "empty function stubs with 'pass' or placeholder return values."
                )},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8, max_tokens=1500
        )
        content = clean_json(resp.choices[0].message.content)
        problem = json.loads(content)
        # Sanitize starter_code to ensure no solution is leaked
        problem['starter_code'] = _sanitize_starter_code(problem.get('starter_code', {}))
        return jsonify({'success': True, 'problem': problem})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _sanitize_starter_code(starter_code):
    """Remove any solution logic from starter_code, keeping only function signatures."""
    if not isinstance(starter_code, dict):
        return {}

    defaults = {
        'python': 'def solution():\n    # Write your solution here\n    pass',
        'javascript': 'function solution() {\n    // Write your solution here\n}',
        'java': 'public class Solution {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}',
        'cpp': '#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}'
    }

    # Suspicious patterns that indicate solution code was included
    solution_patterns = [
        'for ', 'while ', 'if ', 'elif ', 'else:',  # control flow
        '.append(', '.push(', '.add(',               # data structure ops
        'sum(', 'len(', 'max(', 'min(',              # built-in functions used in logic
        'result =', 'result +=', 'count =', 'total =', # variables holding results
        'print(', 'console.log(',                     # output in starter code
        'System.out',                                  # Java output
    ]

    sanitized = {}
    for lang, code in starter_code.items():
        if not isinstance(code, str):
            sanitized[lang] = defaults.get(lang, '')
            continue

        # Check if the code contains solution logic
        code_lines = code.replace('\\n', '\n').split('\n')
        has_solution = False
        logic_lines = 0

        for line in code_lines:
            stripped = line.strip()
            # Skip blank lines, comments, function signatures, pass, return
            if (not stripped or stripped.startswith('#') or stripped.startswith('//')
                    or stripped.startswith('/*') or stripped == 'pass'
                    or stripped.startswith('def ') or stripped.startswith('function ')
                    or stripped.startswith('public ') or stripped.startswith('class ')
                    or stripped.startswith('import ') or stripped.startswith('#include')
                    or stripped.startswith('using ') or stripped in ('{', '}', '};')
                    or stripped.startswith('return') and len(stripped) < 15):
                continue
            # Check for solution patterns
            for pattern in solution_patterns:
                if pattern in stripped:
                    has_solution = True
                    break
            logic_lines += 1

        # If more than 3 meaningful lines or solution patterns found, replace with default
        if has_solution or logic_lines > 3:
            # Try to preserve the function signature at least
            sig_line = ''
            for line in code_lines:
                stripped = line.strip()
                if (stripped.startswith('def ') or stripped.startswith('function ')
                        or 'static' in stripped and '(' in stripped):
                    sig_line = stripped
                    break

            if sig_line and lang == 'python':
                sanitized[lang] = f"{sig_line}\n    # Write your solution here\n    pass"
            elif sig_line and lang == 'javascript':
                sanitized[lang] = f"{sig_line}\n    // Write your solution here\n}}"
            else:
                sanitized[lang] = defaults.get(lang, code)
        else:
            sanitized[lang] = code

    return sanitized


def _run_remotely(code, language):
    """Execute code using Piston API, Judge0 API, or Groq AI fallback. Returns (stdout, stderr, status)."""
    last_error = None

    # 1. Try Piston API — completely FREE, no key needed
    try:
        lang, version = PISTON_LANGS.get(language, ('python', '3.10.0'))
        piston_ext_map = {'python': 'py', 'javascript': 'js', 'java': 'java',
                          'c++': 'cpp', 'c': 'c', 'go': 'go', 'rust': 'rs', 'typescript': 'ts'}
        ext = piston_ext_map.get(lang, 'txt')
        payload = {
            'language': lang, 'version': version,
            'files': [{'name': f'main.{ext}', 'content': code}],
            'stdin': '', 'args': [], 'compile_timeout': 10, 'run_timeout': 5
        }
        r = requests.post('https://emkc.org/api/v2/piston/execute', json=payload, timeout=15)
        if r.status_code == 200 and r.text.strip():
            result = r.json()
            run = result.get('run', {})
            stdout = run.get('stdout', '')
            stderr = run.get('stderr', '')
            status = 'Accepted' if not stderr else 'Runtime Error'
            return stdout, stderr, status
        else:
            last_error = f'Piston API returned status {r.status_code}'
    except Exception as e:
        last_error = f'Piston API error: {str(e)}'

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
            if r.status_code == 200 and r.text.strip():
                result = r.json()
                stdout = base64.b64decode(result.get('stdout') or b'').decode('utf-8', errors='replace')
                stderr = base64.b64decode(result.get('stderr') or b'').decode('utf-8', errors='replace')
                compile_out = base64.b64decode(result.get('compile_output') or b'').decode('utf-8', errors='replace')
                return stdout, stderr or compile_out, result.get('status', {}).get('description', 'Unknown')
            else:
                last_error = f'Judge0 returned status {r.status_code}'
        except Exception as e:
            last_error = f'Judge0 error: {str(e)}'

    # 3. Fallback: Groq AI-simulated execution
    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a code execution simulator. Your ONLY job is to predict the EXACT output "
                    "that would appear if this code were compiled and run. "
                    "RULES:\n"
                    "- Run the code EXACTLY as given. Do NOT fix, modify, complete, or improve the code.\n"
                    "- If the code has a function with 'pass' or no implementation, it produces NO output.\n"
                    "- If the code has syntax errors, report them as errors.\n"
                    "- If the code doesn't print anything, output is empty string.\n"
                    "- NEVER write your own solution. NEVER add code that wasn't there.\n"
                    "- Return JSON only: {\"output\": \"exact output or empty string\", \"error\": \"error message or empty string\"}"
                )},
                {"role": "user", "content": f"Language: {language}\n\nCode:\n```\n{code}\n```\n\nSimulate running this EXACT code. What is the output?"}
            ],
            temperature=0, max_tokens=500
        )
        raw_content = resp.choices[0].message.content or ''
        content = clean_json(raw_content)
        if not content.strip():
            return raw_content or 'No output', '', 'AI Simulated'
        try:
            result = json.loads(content)
            return result.get('output', '') or 'No output', result.get('error', ''), 'AI Simulated'
        except json.JSONDecodeError:
            return raw_content, '', 'AI Simulated'
    except Exception as e:
        raise Exception(f'All execution methods failed. Last error: {last_error or str(e)}')


@ide_bp.route('/api/ide/run-tests', methods=['POST'])
@login_required
def run_tests():
    """Run the student's code against the problem's example test cases."""
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python').lower()
    problem_title = data.get('problem_title', '')
    problem_desc = data.get('problem_desc', '')
    examples = data.get('examples', [])

    if not code.strip():
        return jsonify({'error': 'Write your solution first!'}), 400
    if not examples:
        return jsonify({'error': 'No test cases available. Generate a problem first!'}), 400

    # Use AI to generate test wrapper code
    examples_str = json.dumps(examples, indent=2)
    prompt = (
        f"Problem: {problem_title}\n{problem_desc}\n\n"
        f"Student's {language} code:\n```\n{code}\n```\n\n"
        f"Example test cases:\n{examples_str}\n\n"
        f"Generate a COMPLETE {language} test runner script that:\n"
        f"1. Includes the student's code EXACTLY as written (copy it verbatim)\n"
        f"2. Calls the student's function with each example input\n"
        f"3. Compares the result with expected output\n"
        f"4. Prints EXACTLY this format for each test:\n"
        f'   TEST_RESULT|<test_number>|<PASS or FAIL>|<expected>|<actual>\n'
        f"5. At the end prints: TEST_SUMMARY|<passed_count>|<total_count>\n\n"
        f"RULES:\n"
        f"- Parse the input strings to proper {language} types (lists, numbers, strings, etc.)\n"
        f"- Convert results to strings for comparison\n"
        f"- Handle exceptions gracefully — print TEST_RESULT|N|ERROR|expected|error_message\n"
        f"- Return ONLY the raw code, no markdown fences, no explanations\n"
        f"- The code must be directly executable"
    )

    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a test code generator. Output ONLY executable code, no markdown, "
                    "no explanations, no code fences. The code must run directly."
                )},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, max_tokens=2000
        )
        test_code = resp.choices[0].message.content or ''
        # Strip markdown fences if AI included them
        test_code = test_code.strip()
        if test_code.startswith('```'):
            lines = test_code.split('\n')
            test_code = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])

        # Run the test code remotely
        try:
            stdout, stderr, _ = _run_remotely(test_code, language)
        except Exception as e:
            return jsonify({'error': f'Execution error: {str(e)}'}), 500

        # Parse the structured output
        output = stdout or stderr or ''
        results = []
        summary = {'passed': 0, 'total': len(examples), 'status': 'completed'}

        for line in output.strip().split('\n'):
            line = line.strip()
            if line.startswith('TEST_RESULT|'):
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    test_num = parts[1]
                    status = parts[2]
                    expected = parts[3]
                    actual = parts[4]
                    results.append({
                        'test': int(test_num) if test_num.isdigit() else len(results) + 1,
                        'status': status,
                        'expected': expected,
                        'actual': actual
                    })
            elif line.startswith('TEST_SUMMARY|'):
                parts = line.split('|')
                if len(parts) >= 3:
                    summary['passed'] = int(parts[1]) if parts[1].isdigit() else 0
                    summary['total'] = int(parts[2]) if parts[2].isdigit() else len(examples)

        # If no structured output, it might have errored
        if not results and output:
            summary['status'] = 'error'
            summary['message'] = stderr or stdout or 'Could not parse test results'

        summary['all_passed'] = summary['passed'] == summary['total'] and summary['passed'] > 0

        return jsonify({'success': True, 'results': results, 'summary': summary})

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

    last_error = None

    try:
        stdout, stderr, status = _run_remotely(code, language)
        output = stdout or stderr or 'No output'
        has_error = bool(stderr and not stdout)
        # Or just use the returned status if it's there
        final_status = status if status else ('Accepted' if not has_error else 'Runtime Error')
        return jsonify({
            'success': True,
            'output': output,
            'error': stderr if has_error else '',
            'status': final_status
        })
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
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": 'You are an expert code reviewer. Return JSON only: {"score": 0-100, "correct": true/false, "feedback": "...", "improvements": ["..."], "time_complexity": "...", "space_complexity": "..."}'},
                {"role": "user", "content": f"Problem:\n{problem}\n\nSolution ({language}):\n{code}\n\nEvaluate this solution."}
            ],
            temperature=0.3, max_tokens=1000
        )
        content = clean_json(resp.choices[0].message.content)
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


@ide_bp.route('/api/ide/get-hint', methods=['POST'])
@login_required
def get_hint():
    """Generate a progressive hint for the current problem without revealing the solution."""
    data = request.json
    problem = data.get('problem', '')
    code = data.get('code', '')
    language = data.get('language', 'python')
    hint_level = int(data.get('hint_level', 1))  # 1-5, increasingly specific

    if not problem:
        return jsonify({'error': 'Generate a problem first!'}), 400

    hint_instructions = {
        1: (
            "Give a HIGH-LEVEL APPROACH hint. Describe the general strategy or algorithm "
            "concept needed (e.g., 'Think about using a hash map' or 'Consider a two-pointer approach'). "
            "Do NOT give any code. Do NOT reveal the solution. Just point the student in the right direction."
        ),
        2: (
            "Give a STEP-BY-STEP BREAKDOWN hint. Break the problem into 3-4 smaller sub-steps "
            "the student should follow. Use bullet points. Do NOT give any code or the solution. "
            "Guide them on WHAT to do, not HOW to code it."
        ),
        3: (
            "Give a PSEUDOCODE hint. Provide pseudocode (not real code) that outlines the logic. "
            "Use plain English in the pseudocode. Do NOT write actual working code in any language."
        ),
        4: (
            "Give a CODE STRUCTURE hint. Show the skeleton/structure of the solution in the specified "
            "programming language with placeholder comments where the key logic should go. "
            "Include function signatures and control flow but leave the actual logic as comments like "
            "'// TODO: implement the comparison logic here'. Do NOT fill in the actual solution logic."
        ),
        5: (
            "Give a DETAILED NUDGE hint. Look at the student's current code and point out exactly "
            "what is wrong or missing. If they haven't started, describe the first 2-3 lines they need "
            "to write. If they have code, point out bugs or the next step. Still do NOT give the complete solution."
        ),
    }

    instruction = hint_instructions.get(min(hint_level, 5), hint_instructions[5])

    user_code_section = ""
    if code and code.strip() and code.strip() != starterCode_check(language):
        user_code_section = f"\n\nThe student's current code ({language}):\n```\n{code}\n```\nAnalyze their code and tailor the hint to help them progress from where they are."
    else:
        user_code_section = "\n\nThe student has not written any code yet."

    prompt = (
        f"Problem:\n{problem}\n"
        f"{user_code_section}\n\n"
        f"Hint Level: {hint_level}/5 (1=vague, 5=specific)\n\n"
        f"Instructions: {instruction}\n\n"
        f'Return ONLY valid JSON: {{"hint": "your hint text here", "hint_level": {hint_level}, '
        f'"encouragement": "a short encouraging message"}}'
    )

    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a patient coding tutor. Your goal is to GUIDE students to solve problems themselves. "
                    "NEVER reveal the complete solution. Use emojis sparingly. Format hints with bullet points and "
                    "clear structure. Return valid JSON only, no markdown fences."
                )},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6, max_tokens=800
        )
        content = clean_json(resp.choices[0].message.content)
        hint_data = json.loads(content)
        return jsonify({'success': True, 'hint': hint_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def starterCode_check(language):
    """Return default starter code for comparison."""
    starters = {
        'python': '# Write your solution here\ndef solution():\n    pass\n',
        'javascript': '// Write your solution here\nfunction solution() {\n    \n}\n',
        'java': 'public class Solution {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}\n',
        'cpp': '#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}\n'
    }
    return starters.get(language, '')

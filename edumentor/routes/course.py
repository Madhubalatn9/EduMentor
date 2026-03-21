from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Course, LessonContent
from config import Config
from groq import Groq
import json
import re

course_bp = Blueprint('course', __name__)
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


def _safe_json_loads(content):
    """Parse JSON with fallback for control characters."""
    content = _clean_json(content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try with strict=False to allow control characters in strings
        try:
            return json.loads(content, strict=False)
        except json.JSONDecodeError:
            # Last resort: escape problematic control characters inside string values
            # Replace unescaped control chars (except already escaped ones)
            cleaned = re.sub(r'[\x00-\x1f]', lambda m: {
                '\n': '\\n', '\t': '\\t', '\r': '\\r'
            }.get(m.group(), ''), content)
            return json.loads(cleaned, strict=False)


@course_bp.route('/course')
@login_required
def course():
    saved = Course.query.filter_by(user_id=current_user.id).order_by(Course.created_at.desc()).all()
    return render_template('course.html', saved_courses=saved)


@course_bp.route('/api/course/generate', methods=['POST'])
@login_required
def generate_course():
    data = request.json
    skill = data.get('skill', '').strip()
    level = data.get('level', 'Beginner')
    modules_count = min(int(data.get('modules', 5)), 10)

    if not skill:
        return jsonify({'error': 'Skill is required'}), 400

    prompt = (
        f"Create a comprehensive course on {skill} for {level} level learners. "
        f"Include relevant emojis in the course title and all module/lesson titles to make it engaging. "
        f"The course must have exactly {modules_count} modules. "
        f"Each module should have 3 to 5 lessons. "
        f"Return ONLY valid JSON with this exact structure: "
        f'{{"title": "🚀 Course Title with Emoji", "description": "2-3 sentence course overview", '
        f'"skill": "{skill}", "level": "{level}", '
        f'"total_modules": {modules_count}, '
        f'"modules": ['
        f'{{"id": 1, "title": "📂 Module Title with Emoji", "description": "What this module covers", '
        f'"lessons": [{{"id": 1, "title": "📖 Lesson Title with Emoji", "duration": "15 min", "type": "theory"}}]'
        f'}}]}}'
        f'\n\nLesson types must be one of: "theory", "practice", or "project". '
        f'Make each module progressively more advanced. Use realistic durations.'
    )
    try:
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer. Create detailed, well-structured course outlines with realistic progression. Return valid JSON only, no markdown fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=3000
        )
        course_data = _safe_json_loads(resp.choices[0].message.content)

        total = sum(len(m.get('lessons', [])) for m in course_data.get('modules', []))
        course_data['total_lessons'] = total

        return jsonify({'success': True, 'course': course_data})
    except json.JSONDecodeError as e:
        return jsonify({'error': 'Failed to parse AI response. Please try again.', 'details': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@course_bp.route('/api/course/generate-lesson', methods=['POST'])
@login_required
def generate_lesson():
    """Generate lesson content dynamically when a user clicks on a lesson."""
    data = request.json
    course_title = data.get('course_title', '')
    skill = data.get('skill', '')
    level = data.get('level', 'Beginner')
    module_title = data.get('module_title', '')
    lesson_title = data.get('lesson_title', '')
    lesson_type = data.get('lesson_type', 'theory')
    course_id = data.get('course_id')
    module_id = data.get('module_id')
    lesson_id = data.get('lesson_id')

    # Check cache first (if course is saved)
    if course_id:
        cached = LessonContent.query.filter_by(
            course_id=course_id, module_id=module_id, lesson_id=lesson_id
        ).first()
        if cached:
            return jsonify({'success': True, 'lesson': json.loads(cached.content), 'cached': True})

    type_instruction = {
        'theory': 'Focus on explaining concepts clearly with real-world analogies and examples. Include detailed explanations.',
        'practice': 'Include multiple hands-on coding exercises with step-by-step solutions and clear explanations.',
        'project': 'Provide a mini-project with clear requirements, starter code, implementation steps, and solution guidance.'
    }.get(lesson_type, '')

    prompt = (
        f"Generate comprehensive lesson content for:\n"
        f"Course: {course_title}\nModule: {module_title}\n"
        f"Lesson: {lesson_title}\nSkill: {skill}, Level: {level}\n"
        f"Lesson Type: {lesson_type}. {type_instruction}\n\n"
        f"Use relevant emojis throughout the lesson title and content. "
        f"For the content, use structured bullet points (using • or -) for key concepts and steps to make it highly readable. "
        f'Return ONLY valid JSON with this structure: {{'
        f'"title": "✨ Lesson title with Emoji", '
        f'"content": "Detailed lesson content. Use emojis and structured bullet points. Explain concepts thoroughly.", '
        f'"code_examples": [{{"title": "💻 Example name with Emoji", "language": "python", "code": "actual working code", "explanation": "what this code does"}}], '
        f'"key_takeaways": ["✅ takeaway 1", "✅ takeaway 2"], '
        f'"exercises": [{{"question": "📝 exercise description with Emoji", "hint": "💡 helpful hint", "solution": "solution code or explanation"}}], '
        f'"summary": "📌 2-3 sentence lesson summary with Emoji"'
        f'}}'
    )
    try:
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert educator. Generate comprehensive, engaging lesson content with practical examples and exercises. Return valid JSON only, no markdown fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=4000
        )
        lesson_data = _safe_json_loads(resp.choices[0].message.content)

        # Cache the content if course is saved
        if course_id:
            lc = LessonContent(
                course_id=course_id,
                module_id=module_id,
                lesson_id=lesson_id,
                content=json.dumps(lesson_data)
            )
            db.session.add(lc)
            db.session.commit()

        return jsonify({'success': True, 'lesson': lesson_data, 'cached': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@course_bp.route('/api/course/save', methods=['POST'])
@login_required
def save_course():
    data = request.json
    course_data = data.get('course', {})
    c = Course(
        user_id=current_user.id,
        title=course_data.get('title', 'Untitled Course'),
        skill=course_data.get('skill', ''),
        level=course_data.get('level', ''),
        structure=json.dumps(course_data),
        total_lessons=course_data.get('total_lessons', 0)
    )
    db.session.add(c)
    db.session.commit()
    return jsonify({'success': True, 'id': c.id})


@course_bp.route('/api/course/<int:cid>', methods=['GET'])
@login_required
def get_course(cid):
    c = Course.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    completed = json.loads(c.completed_lessons or '[]')
    return jsonify({
        'success': True, 'course': json.loads(c.structure),
        'completed_lessons': completed, 'id': c.id
    })


@course_bp.route('/api/course/<int:cid>/complete-lesson', methods=['POST'])
@login_required
def complete_lesson(cid):
    c = Course.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    data = request.json
    lesson_key = data.get('lesson_key', '')

    completed = json.loads(c.completed_lessons or '[]')
    if lesson_key in completed:
        completed.remove(lesson_key)
    else:
        completed.append(lesson_key)

    c.completed_lessons = json.dumps(completed)
    db.session.commit()

    return jsonify({
        'success': True, 'completed': completed,
        'progress': round(len(completed) / max(c.total_lessons, 1) * 100, 1)
    })


@course_bp.route('/api/course/<int:cid>', methods=['DELETE'])
@login_required
def delete_course(cid):
    c = Course.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    LessonContent.query.filter_by(course_id=cid).delete()
    db.session.delete(c)
    db.session.commit()
    return jsonify({'success': True})

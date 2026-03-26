from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Course, LessonContent
from config import Config
from utils import get_groq_client, safe_json_loads, sanitize_input
import json

course_bp = Blueprint('course', __name__)


@course_bp.route('/course')
@login_required
def course():
    saved = Course.query.filter_by(user_id=current_user.id).order_by(Course.created_at.desc()).all()
    return render_template('course.html', saved_courses=saved)


@course_bp.route('/api/course/generate', methods=['POST'])
@login_required
def generate_course():
    data = request.json
    skill = sanitize_input(data.get('skill', ''), max_length=100)
    level = sanitize_input(data.get('level', 'Beginner'), max_length=50)
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
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer. Create detailed, well-structured course outlines with realistic progression. Return valid JSON only, no markdown fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=3000
        )
        course_data = safe_json_loads(resp.choices[0].message.content)

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
    course_title = sanitize_input(data.get('course_title', ''), max_length=200)
    skill = sanitize_input(data.get('skill', ''), max_length=100)
    level = sanitize_input(data.get('level', 'Beginner'), max_length=50)
    module_title = sanitize_input(data.get('module_title', ''), max_length=200)
    lesson_title = sanitize_input(data.get('lesson_title', ''), max_length=200)
    lesson_type = sanitize_input(data.get('lesson_type', 'theory'), max_length=20)
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
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert educator. Generate comprehensive, engaging lesson content with practical examples and exercises. Return valid JSON only, no markdown fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=4000
        )
        lesson_data = safe_json_loads(resp.choices[0].message.content)

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
    comp = data.get('completed_lessons', [])
    c = Course(
        user_id=current_user.id,
        title=course_data.get('title', 'Untitled Course'),
        skill=course_data.get('skill', ''),
        level=course_data.get('level', ''),
        structure=json.dumps(course_data),
        completed_lessons=json.dumps(comp),
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

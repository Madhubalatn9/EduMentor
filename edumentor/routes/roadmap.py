from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import db, Roadmap
from config import Config
from groq import Groq
import json

roadmap_bp = Blueprint('roadmap', __name__)
client = Groq(api_key=Config.GROQ_API_KEY)


@roadmap_bp.route('/roadmap')
@login_required
def roadmap():
    saved = Roadmap.query.filter_by(user_id=current_user.id).order_by(Roadmap.created_at.desc()).all()
    return render_template('roadmap.html', saved_roadmaps=saved)


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


@roadmap_bp.route('/api/roadmap/generate', methods=['POST'])
@login_required
def generate_roadmap():
    data = request.json
    skill = data.get('skill', '').strip()
    level = data.get('level', 'Beginner')
    duration = data.get('duration', 8)
    if not skill:
        return jsonify({'error': 'Skill is required'}), 400

    prompt = (
        f"Create a {duration}-week learning roadmap for {skill} at {level} level. "
        f'Return ONLY valid JSON with this structure: '
        f'{{ "title": "...", "skill": "{skill}", "level": "{level}", "total_weeks": {duration}, '
        f'"overview": "...", "weeks": [ {{ "week": 1, "title": "...", "focus": "...", '
        f'"topics": ["..."], "resources": ["..."], "project": "...", "goals": ["..."] }} ] }}'
    )
    try:
        resp = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert curriculum designer. Return valid JSON only, no markdown fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, max_tokens=3000
        )
        content = _clean_json(resp.choices[0].message.content)
        roadmap_data = json.loads(content)
        return jsonify({'success': True, 'roadmap': roadmap_data})
    except json.JSONDecodeError as e:
        return jsonify({'error': 'Failed to parse AI response', 'details': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@roadmap_bp.route('/api/roadmap/save', methods=['POST'])
@login_required
def save_roadmap():
    data = request.json
    r = Roadmap(
        user_id=current_user.id,
        skill=data.get('skill', ''),
        level=data.get('level', ''),
        content=json.dumps(data.get('content', {}))
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({'success': True, 'id': r.id})


@roadmap_bp.route('/api/roadmap/<int:rid>', methods=['GET'])
@login_required
def get_roadmap(rid):
    r = Roadmap.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    return jsonify({'success': True, 'roadmap': json.loads(r.content), 'skill': r.skill, 'level': r.level})


@roadmap_bp.route('/api/roadmap/<int:rid>', methods=['DELETE'])
@login_required
def delete_roadmap(rid):
    r = Roadmap.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    db.session.delete(r)
    db.session.commit()
    return jsonify({'success': True})

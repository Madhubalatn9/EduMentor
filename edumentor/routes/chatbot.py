from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import groq
from config import Config
from utils import sanitize_input

chatbot_bp = Blueprint('chatbot', __name__)


@chatbot_bp.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')


@chatbot_bp.route('/chatbot/ask', methods=['POST'])
@login_required
def chatbot_ask():
    data = request.get_json()
    user_message = sanitize_input(data.get('message', ''), max_length=2000)
    history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Please type a question.'}), 400

    if not Config.GROQ_API_KEY:
        return jsonify({
            'error': '⚠️ GROQ_API_KEY is not set. Create a .env file with your key from https://console.groq.com/keys'
        }), 500

    try:
        client = groq.Groq(api_key=Config.GROQ_API_KEY)
        user_skill = current_user.skill or 'General'
        user_level = current_user.level or 'Beginner'

        system_prompt = f"""You are EduBot, a friendly and expert AI tutor on the EduMentor learning platform.
The student's primary skill is {user_skill} and their level is {user_level}.

Rules:
- Answer doubts clearly and concisely.
- Use simple language appropriate for the student's level.
- Include code examples when relevant, wrapped in markdown code blocks.
- Use emojis sparingly to keep the tone engaging.
- If the student asks something off-topic, gently redirect them to learning topics.
- Structure longer answers with bullet points or numbered steps.
- Always encourage the student at the end."""

        # Build messages from chat history (keep last 10 messages for context)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        messages.append({"role": "user", "content": user_message})

        completion = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        reply = completion.choices[0].message.content
        return jsonify({'reply': reply})

    except groq.AuthenticationError:
        return jsonify({'error': '❌ Invalid API key. Check your .env file.'}), 401
    except groq.APIConnectionError:
        return jsonify({'error': '❌ Cannot connect to AI service. Check your internet.'}), 503
    except Exception as e:
        return jsonify({'error': f'Something went wrong: {str(e)}'}), 500

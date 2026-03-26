"""Shared utilities for EduMentor."""

import json
import re
from groq import Groq
from config import Config


def get_groq_client():
    """Get a Groq client instance. Raises a clear error if key is missing."""
    if not Config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file. Get a key from https://console.groq.com/keys"
        )
    return Groq(api_key=Config.GROQ_API_KEY)


def clean_json(content):
    """Clean AI response to extract valid JSON."""
    content = content.strip()

    # Handle markdown code blocks
    if content.startswith('```'):
        first_closing_fence = content.find('```', 3)
        if first_closing_fence != -1:
            extracted_content = content[3:first_closing_fence].strip()
            if extracted_content.lower().startswith('json'):
                content = extracted_content[4:].strip()
            else:
                content = extracted_content
        else:
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


def safe_json_loads(content):
    """Parse JSON with fallback for control characters."""
    content = clean_json(content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            return json.loads(content, strict=False)
        except json.JSONDecodeError:
            cleaned = re.sub(r'[\x00-\x1f]', lambda m: {
                '\n': '\\n', '\t': '\\t', '\r': '\\r'
            }.get(m.group(), ''), content)
            return json.loads(cleaned, strict=False)


def sanitize_input(text, max_length=500):
    """Sanitize user input to prevent prompt injection and limit length."""
    if not text:
        return ''
    text = str(text).strip()
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]
    return text

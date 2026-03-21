# 🚀 EduMentor - AI-Driven Personalized Learning Platform

EduMentor is an advanced AI-powered learning system designed to help users learn anything efficiently. It features dynamic course generation, roadmapping, an interactive coding IDE, quizzes, and interview preparation.

## ✨ Features
- **🗺️ Course Roadmap**: Generate an 8-week learning path for any skill with topics, goals, and resources.
- **📚 Dynamic Courses**: personalized courses with dynamic lesson content generation on-demand.
- **💻 Coding IDE**: Interactive code editor with line numbers, multi-language support, and AI evaluation.
- **📝 Intelligent Quizzes**: Test your knowledge with AI-generated quizzes for any level.
- **💼 Interview Preparation**: Practice technical interviews with AI-driven feedback.
- **📊 Progress Tracking**: Keep track of your learning journey and stats.

## 🛠️ Technology Stack
- **Backend**: Python, Flask, SQLAlchemy
- **AI Engine**: Groq (Llama models)
- **Database**: SQLite (Development)
- **Frontend**: HTML5, Vanilla CSS, JavaScript
- **Design**: Premium glassmorphism UI with responsive sidebar

## 🚦 Getting Started

### Prerequisites
- Python 3.8+
- Groq API Key

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/edumentor.git
   cd edumentor
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Mac/Linux
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Create a `.env` file and add:
   ```env
   SECRET_KEY=your_secret_key
   GROQ_API_KEY=your_groq_api_key
   DATABASE_URL=sqlite:///edumentor.db
   ```

5. **Run the Application**:
   ```bash
   python app.py
   ```
   Access at `http://localhost:5000`

## 📄 License
This project is for educational purposes.

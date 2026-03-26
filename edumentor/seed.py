from app import create_app
from models import db, User, Course, Roadmap, Quiz
import json

def seed_data():
    app = create_app()
    with app.app_context():
        # Check if users already exist
        if User.query.filter_by(username='demo').first():
            print("Database already has data.")
            return

        # Create Demo User
        demo_user = User(username='demo', email='demo@example.com')
        demo_user.set_password('demo123')
        demo_user.skill = 'Python'
        demo_user.level = 'Beginner'
        db.session.add(demo_user)
        db.session.commit()

        # Create a Sample Roadmap
        roadmap = Roadmap(
            user_id=demo_user.id,
            skill='Python',
            level='Beginner',
            content="### 🗺️ 8-Week Python Roadmap\n1. Week 1: Basics\n2. Week 2: Data Types..."
        )
        db.session.add(roadmap)

        # Create a Sample Course
        course = Course(
            user_id=demo_user.id,
            title='Mastering Python Basics',
            skill='Python',
            level='Beginner',
            structure=json.dumps({"modules": ["Intro", "Variables", "Loops"]})
        )
        db.session.add(course)

        # Create a Sample Quiz
        quiz = Quiz(
            user_id=demo_user.id,
            skill='Python',
            level='Beginner',
            questions=json.dumps([{"q": "What is Python?", "a": ["A language", "A snake"], "c": 0}]),
            score=1,
            total=1
        )
        db.session.add(quiz)

        db.session.commit()
        print("Database seeded successfully! You can login with 'demo' / 'demo123'.")

if __name__ == '__main__':
    seed_data()

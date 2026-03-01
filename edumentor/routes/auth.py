from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Welcome back! Ready to learn? 🚀', 'success')
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('index.html', form_type='login')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        skill = request.form.get('skill', 'Python')
        level = request.form.get('level', 'Beginner')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('index.html', form_type='register')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('index.html', form_type='register')
        user = User(username=username, email=email, skill=skill, level=level)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created! Welcome to EduMentor! 🎓', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('index.html', form_type='register')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

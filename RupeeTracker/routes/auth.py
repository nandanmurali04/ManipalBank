from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from app import db
from models import User, IPHistory

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Landing page"""
    if 'user_id' in session:
        return redirect(url_for('banking.dashboard'))
    return render_template('index.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not name or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
            
        # Check if user exists
        existing_user = User.get_by_email(email)
        if existing_user:
            flash('User already exists with this email', 'danger')
            return render_template('register.html')
            
        # Get phone number if provided
        phone_number = request.form.get('phone_number')
        
        # Create new user
        new_user = User(
            name=name,
            email=email,
            phone_number=phone_number
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Find user
        user = User.get_by_email(email)
        
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'danger')
            return render_template('login.html')
            
        # Set session
        session['user_id'] = user.id
        session['user_name'] = user.name
        
        # Record IP address
        IPHistory.record_ip(user.id, request.remote_addr)
        
        # Update last login time
        user.last_login = db.func.now()
        db.session.commit()
        
        flash('Logged in successfully!', 'success')
        return redirect(url_for('banking.dashboard'))
        
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """User logout"""
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.index'))

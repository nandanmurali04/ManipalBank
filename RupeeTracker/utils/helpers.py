from functools import wraps
from flask import session, redirect, url_for, flash
from models import User

def login_required(f):
    """Decorator to require user login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            flash('Admin access required', 'danger')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def format_currency(amount):
    """Format amount as Indian Rupees"""
    return f"₹{amount:,.2f}"

def get_current_user():
    """Get the current logged in user or None"""
    user_id = session.get('user_id')
    if user_id:
        return User.get_by_id(user_id)
    return None

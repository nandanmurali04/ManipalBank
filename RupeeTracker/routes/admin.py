from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from models import FraudLog, Transaction, User
from utils.helpers import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin credentials - in a real system, this would be in the database
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            flash('Admin login successful', 'success')
            return redirect(url_for('admin.fraud_logs'))
        else:
            flash('Invalid admin credentials', 'danger')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    """Admin logout"""
    session.pop('admin', None)
    flash('Admin logged out', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/fraud-logs')
@admin_required
def fraud_logs():
    """View all fraud logs"""
    # Get all fraud logs with their associated transactions
    fraud_logs = FraudLog.get_all_logs()
    
    # Create a list of enriched fraud logs with transaction and user details
    enriched_logs = []
    for log in fraud_logs:
        transaction = Transaction.query.get(log.transaction_id)
        sender = User.query.get(transaction.user_id)
        recipient = User.query.get(transaction.recipient_id) if transaction.recipient_id else None
        
        enriched_logs.append({
            'log': log,
            'transaction': transaction,
            'sender': sender,
            'recipient': recipient
        })
    
    return render_template('admin/fraud_logs.html', fraud_logs=enriched_logs)

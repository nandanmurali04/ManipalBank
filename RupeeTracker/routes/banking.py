from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from models import User, Transaction, Payee, ScheduledPayment, InternationalTransfer
from utils.fraud import check_fraud
from utils.helpers import login_required, format_currency
import logging
from datetime import datetime

banking_bp = Blueprint('banking', __name__)

@banking_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing balance and recent transactions"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    # Get recent transactions
    transactions = Transaction.get_user_transactions(user_id, limit=5)
    
    return render_template(
        'dashboard.html', 
        user=user, 
        transactions=transactions
    )

@banking_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    """Handle money deposits"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            description = request.form.get('description', 'Deposit')
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'danger')
                return render_template('deposit.html', user=user)
                
            # Create transaction
            transaction_id = Transaction.create(
                user_id=user_id,
                amount=amount,
                transaction_type='deposit',
                ip_address=request.remote_addr,
                description=description
            )
            
            # Update user balance
            user.update_balance(amount)
            
            flash(f'Successfully deposited ₹{amount:.2f}', 'success')
            return redirect(url_for('banking.dashboard'))
            
        except ValueError:
            flash('Invalid amount', 'danger')
    
    return render_template('deposit.html', user=user)

@banking_bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    """Handle money withdrawals"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            description = request.form.get('description', 'Withdrawal')
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'danger')
                return render_template('withdraw.html', user=user)
                
            # Check for sufficient balance
            if user.balance < amount:
                flash('Insufficient balance', 'danger')
                return render_template('withdraw.html', user=user)
                
            # Create transaction
            transaction_id = Transaction.create(
                user_id=user_id,
                amount=amount,
                transaction_type='withdraw',
                ip_address=request.remote_addr,
                description=description
            )
            
            # Update user balance (negative for withdrawal)
            user.update_balance(-amount)
            
            flash(f'Successfully withdrew ₹{amount:.2f}', 'success')
            return redirect(url_for('banking.dashboard'))
            
        except ValueError:
            flash('Invalid amount', 'danger')
    
    return render_template('withdraw.html', user=user)

@banking_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    """Handle money transfers to other users"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            recipient_email = request.form.get('recipient_email', '')
            description = request.form.get('description', 'Transfer')
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'danger')
                return render_template('transfer.html', user=user)
                
            # Check for sufficient balance
            if user.balance < amount:
                flash('Insufficient balance', 'danger')
                return render_template('transfer.html', user=user)
                
            # Find recipient
            recipient = User.get_by_email(recipient_email)
            if not recipient:
                flash('Recipient not found', 'danger')
                return render_template('transfer.html', user=user)
                
            # Can't transfer to self
            if recipient.id == user.id:
                flash('Cannot transfer to yourself', 'danger')
                return render_template('transfer.html', user=user)
                
            # Create transaction
            transaction_id = Transaction.create(
                user_id=user_id,
                recipient_id=recipient.id,
                amount=amount,
                transaction_type='transfer',
                ip_address=request.remote_addr,
                description=description
            )
            
            # Check for fraud
            fraud_reasons = check_fraud(user_id, transaction_id, amount, request.remote_addr)
            
            # Update balances
            user.update_balance(-amount)  # Deduct from sender
            recipient.update_balance(amount)  # Add to recipient
            
            if fraud_reasons:
                # Still allow the transaction but show warning
                warning_message = "Transaction completed but flagged for review: " + ", ".join(fraud_reasons)
                flash(warning_message, 'warning')
                # Log the warning message for debugging
                logging.warning(f"Fraud detected: {warning_message}")
            else:
                flash(f'Successfully transferred ₹{amount:.2f} to {recipient.name}', 'success')
                
            return redirect(url_for('banking.dashboard'))
            
        except ValueError:
            flash('Invalid amount', 'danger')
    
    return render_template('transfer.html', user=user)

@banking_bp.route('/transactions')
@login_required
def transactions():
    """View transaction history"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    # Get all transactions (no limit)
    transactions = Transaction.get_user_transactions(user_id, limit=100)
    
    return render_template(
        'transactions.html', 
        user=user, 
        transactions=transactions
    )

@banking_bp.route('/transfer-options')
@login_required
def transfer_options():
    """Show various transfer options"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    return render_template(
        'transfer_options.html',
        user=user
    )

@banking_bp.route('/transfer-instant', methods=['GET', 'POST'])
@login_required
def transfer_instant():
    """Handle instant transfers to new beneficiaries"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            recipient_email = request.form.get('recipient_email', '')
            recipient_name = request.form.get('recipient_name', '')
            description = request.form.get('description', 'Instant Transfer')
            save_beneficiary = request.form.get('save_beneficiary') == 'on'
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'danger')
                return render_template('transfer_instant.html', user=user)
                
            # Check for sufficient balance
            if user.balance < amount:
                flash('Insufficient balance', 'danger')
                return render_template('transfer_instant.html', user=user)
                
            # Find recipient
            recipient = User.get_by_email(recipient_email)
            if not recipient:
                flash('Recipient not found', 'danger')
                return render_template('transfer_instant.html', user=user)
                
            # Can't transfer to self
            if recipient.id == user.id:
                flash('Cannot transfer to yourself', 'danger')
                return render_template('transfer_instant.html', user=user)
            
            # Create transaction
            transaction_id = Transaction.create(
                user_id=user_id,
                recipient_id=recipient.id,
                amount=amount,
                transaction_type='transfer',
                ip_address=request.remote_addr,
                description=description
            )
            
            # Save as beneficiary if requested
            if save_beneficiary:
                Payee.create(
                    user_id=user_id,
                    name=recipient_name or recipient.name,
                    account_type='domestic',
                    email=recipient_email,
                    nickname=request.form.get('nickname')
                )
                flash(f'Beneficiary {recipient_name or recipient.name} saved for future transfers', 'success')
            
            # Check for fraud
            fraud_reasons = check_fraud(user_id, transaction_id, amount, request.remote_addr)
            
            # Update balances
            user.update_balance(-amount)  # Deduct from sender
            recipient.update_balance(amount)  # Add to recipient
            
            if fraud_reasons:
                # Still allow the transaction but show warning
                warning_message = "Transaction completed but flagged for review: " + ", ".join(fraud_reasons)
                flash(warning_message, 'warning')
                # Log the warning message for debugging
                logging.warning(f"Fraud detected: {warning_message}")
            else:
                flash(f'Successfully transferred ₹{amount:.2f} to {recipient.name}', 'success')
                
            return redirect(url_for('banking.dashboard'))
            
        except ValueError:
            flash('Invalid amount', 'danger')
    
    return render_template('transfer_instant.html', user=user)

@banking_bp.route('/international-transfer', methods=['GET', 'POST'])
@login_required
def international_transfer():
    """Handle international money transfers"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            recipient_name = request.form.get('recipient_name', '')
            recipient_bank = request.form.get('recipient_bank', '')
            recipient_account = request.form.get('recipient_account', '')
            recipient_address = request.form.get('recipient_address', '')
            swift_code = request.form.get('swift_code', '')
            currency_code = request.form.get('currency_code', 'USD')
            purpose = request.form.get('purpose', '')
            save_beneficiary = request.form.get('save_beneficiary') == 'on'
            
            # Exchange rate (in a real app, this would come from an external API)
            exchange_rates = {
                'USD': 83.0,  # INR to USD
                'EUR': 90.0,  # INR to EUR
                'GBP': 105.0, # INR to GBP
                'AUD': 55.0   # INR to AUD
            }
            
            exchange_rate = exchange_rates.get(currency_code, 83.0)
            
            # Calculate fee (0.5% of transfer amount)
            fee = amount * 0.005
            
            # Total deduction including fee
            total_deduction = amount + fee
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'danger')
                return render_template('international_transfer.html', user=user)
                
            # Check for sufficient balance
            if user.balance < total_deduction:
                flash('Insufficient balance including fees', 'danger')
                return render_template('international_transfer.html', user=user, 
                                        exchange_rates=exchange_rates)
                
            # Create transaction
            transaction_id = Transaction.create(
                user_id=user_id,
                amount=total_deduction,
                transaction_type='international',
                ip_address=request.remote_addr,
                description=f'International transfer to {recipient_name}'
            )
            
            # Create international transfer details
            international_id = InternationalTransfer.create(
                transaction_id=transaction_id,
                recipient_name=recipient_name,
                recipient_bank=recipient_bank,
                recipient_account=recipient_account,
                recipient_address=recipient_address,
                swift_code=swift_code,
                currency_code=currency_code,
                exchange_rate=exchange_rate,
                fees=fee,
                purpose=purpose
            )
            
            # Save as beneficiary if requested
            if save_beneficiary:
                Payee.create(
                    user_id=user_id,
                    name=recipient_name,
                    account_type='international',
                    bank_name=recipient_bank,
                    account_number=recipient_account,
                    swift_code=swift_code
                )
                flash(f'International beneficiary {recipient_name} saved for future transfers', 'success')
            
            # Check for fraud
            fraud_reasons = check_fraud(user_id, transaction_id, amount, request.remote_addr)
            
            # Update user balance (negative for transfer)
            user.update_balance(-total_deduction)
            
            if fraud_reasons:
                # Still allow the transaction but show warning
                warning_message = "International transfer initiated but flagged for review: " + ", ".join(fraud_reasons)
                flash(warning_message, 'warning')
                # Log the warning message for debugging
                logging.warning(f"Fraud detected in international transfer: {warning_message}")
            else:
                flash(f'International transfer of {currency_code} {amount/exchange_rate:.2f} initiated to {recipient_name}', 'success')
                
            return redirect(url_for('banking.dashboard'))
            
        except ValueError:
            flash('Invalid amount', 'danger')
    
    # Exchange rates for display
    exchange_rates = {
        'USD': 83.0,
        'EUR': 90.0,
        'GBP': 105.0,
        'AUD': 55.0
    }
    
    return render_template('international_transfer.html', 
                           user=user, 
                           exchange_rates=exchange_rates)

@banking_bp.route('/pay-to-contact', methods=['GET', 'POST'])
@login_required
def pay_to_contact():
    """Handle payments to contacts via phone number"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            contact_phone = request.form.get('contact_phone', '')
            contact_name = request.form.get('contact_name', '')
            description = request.form.get('description', 'Payment to contact')
            save_contact = request.form.get('save_contact') == 'on'
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'danger')
                return render_template('pay_to_contact.html', user=user)
                
            # Check for sufficient balance
            if user.balance < amount:
                flash('Insufficient balance', 'danger')
                return render_template('pay_to_contact.html', user=user)
            
            # Search for users with this phone number
            # In a real app, this would be more sophisticated and secure
            # For demo purposes, we'll find the first user that matches (for testing)
            # To test, create two users and update their phone_number in the database
            recipient = None
            from sqlalchemy import or_
            all_users = User.query.filter(
                User.id != user_id,  # Exclude the current user
                or_(
                    User.phone_number == contact_phone,
                    User.phone_number == contact_phone.replace(" ", ""),  # Try without spaces
                    User.phone_number == contact_phone.replace("+91", "")  # Try without country code
                )
            ).first()
            
            if all_users:
                recipient = all_users
                
            # Create transaction
            if recipient:
                # Direct transfer if recipient found
                transaction_id = Transaction.create(
                    user_id=user_id,
                    recipient_id=recipient.id,
                    amount=amount,
                    transaction_type='contact_payment',
                    ip_address=request.remote_addr,
                    description=f'Payment to {contact_name or contact_phone}: {description}'
                )
                
                # Update recipient's balance (positive for incoming payment)
                recipient.update_balance(amount)
                success_message = f'Payment of ₹{amount:.2f} sent successfully to {contact_name or contact_phone}'
            else:
                # Create pending transaction if no recipient found
                transaction_id = Transaction.create(
                    user_id=user_id,
                    amount=amount,
                    transaction_type='contact_payment_pending',
                    ip_address=request.remote_addr,
                    description=f'Pending payment to contact: {contact_name or contact_phone}'
                )
                success_message = f'Payment of ₹{amount:.2f} initiated to {contact_name or contact_phone}. The recipient will receive an SMS notification to claim the payment.'
            
            # Save as contact if requested
            if save_contact:
                # Check if this contact already exists
                existing_payee = Payee.query.filter_by(
                    user_id=user_id,
                    phone=contact_phone
                ).first()
                
                if not existing_payee:
                    Payee.create(
                        user_id=user_id,
                        name=contact_name,
                        account_type='contact',
                        phone=contact_phone
                    )
                    flash(f'Contact {contact_name} saved for future transfers', 'success')
            
            # Check for fraud
            fraud_reasons = check_fraud(user_id, transaction_id, amount, request.remote_addr)
            
            # Update user balance (negative for payment)
            user.update_balance(-amount)
            
            if fraud_reasons:
                # Still allow the transaction but show warning
                warning_message = "Payment processed but flagged for review: " + ", ".join(fraud_reasons)
                flash(warning_message, 'warning')
                # Log the warning message for debugging
                logging.warning(f"Fraud detected in contact payment: {warning_message}")
            else:
                flash(success_message, 'success')
                
            return redirect(url_for('banking.dashboard'))
            
        except ValueError:
            flash('Invalid amount', 'danger')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            logging.error(f"Contact payment error: {str(e)}")
    
    return render_template('pay_to_contact.html', user=user)

@banking_bp.route('/manage-payees', methods=['GET', 'POST'])
@login_required
def manage_payees():
    """View, add, edit, delete payees"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    # Handle new payee form submission
    if request.method == 'POST':
        name = request.form.get('name', '')
        account_type = request.form.get('account_type', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        bank_name = request.form.get('bank_name', '')
        account_number = request.form.get('account_number', '')
        ifsc_code = request.form.get('ifsc_code', '')
        swift_code = request.form.get('swift_code', '')
        nickname = request.form.get('nickname', '')
        
        # Basic validation
        if not name:
            flash('Name is required', 'danger')
        elif not account_type:
            flash('Account type is required', 'danger')
        else:
            # Create payee
            Payee.create(
                user_id=user_id,
                name=name,
                account_type=account_type,
                email=email,
                phone=phone,
                bank_name=bank_name,
                account_number=account_number,
                ifsc_code=ifsc_code,
                swift_code=swift_code,
                nickname=nickname
            )
            flash(f'Payee {name} added successfully', 'success')
            return redirect(url_for('banking.manage_payees'))
    
    # Get all payees for user
    domestic_payees = Payee.get_user_payees(user_id, account_type='domestic')
    international_payees = Payee.get_user_payees(user_id, account_type='international')
    contact_payees = Payee.get_user_payees(user_id, account_type='contact')
    
    return render_template(
        'manage_payees.html',
        user=user,
        domestic_payees=domestic_payees,
        international_payees=international_payees,
        contact_payees=contact_payees
    )

@banking_bp.route('/scheduled-payments', methods=['GET', 'POST'])
@login_required
def scheduled_payments():
    """View and schedule payments"""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    
    # Get payees for selection
    payees = Payee.get_user_payees(user_id)
    
    # Handle form submission
    if request.method == 'POST':
        try:
            payee_id = request.form.get('payee_id')
            recipient_email = request.form.get('recipient_email')
            amount = float(request.form.get('amount', 0))
            description = request.form.get('description', '')
            payment_date = request.form.get('payment_date')
            frequency = request.form.get('frequency', 'once')
            
            # Basic validation
            if not payment_date:
                flash('Payment date is required', 'danger')
            elif amount <= 0:
                flash('Amount must be greater than zero', 'danger')
            elif not (payee_id or recipient_email):
                flash('Please select a payee or enter an email address', 'danger')
            else:
                # Parse date string to datetime
                scheduled_date = datetime.strptime(payment_date, '%Y-%m-%d')
                
                # Create scheduled payment
                ScheduledPayment.create(
                    user_id=user_id,
                    payee_id=payee_id if payee_id else None,
                    recipient_email=recipient_email if not payee_id else None,
                    amount=amount,
                    description=description,
                    scheduled_date=scheduled_date,
                    frequency=frequency
                )
                
                flash('Payment scheduled successfully', 'success')
                return redirect(url_for('banking.scheduled_payments'))
                
        except ValueError:
            flash('Invalid amount or date format', 'danger')
    
    # Get all scheduled payments for user
    pending_payments = ScheduledPayment.get_user_scheduled_payments(user_id, status='pending')
    completed_payments = ScheduledPayment.get_user_scheduled_payments(user_id, status='completed')
    
    return render_template(
        'scheduled_payments.html',
        user=user,
        payees=payees,
        pending_payments=pending_payments,
        completed_payments=completed_payments
    )

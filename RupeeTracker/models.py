from datetime import datetime, timedelta
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True, 
                                 foreign_keys='Transaction.user_id')
    received_transfers = db.relationship('Transaction', backref='recipient', lazy=True,
                                    foreign_keys='Transaction.recipient_id')
    payees = db.relationship('Payee', backref='owner', lazy=True)
    scheduled_payments = db.relationship('ScheduledPayment', backref='initiator', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_balance(self, amount):
        """Update user balance with amount (positive for deposit/receipt, negative for withdrawal/transfer)"""
        self.balance += amount
        db.session.commit()
        return True
    
    @classmethod
    def get_by_email(cls, email):
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.get(user_id)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'balance': self.balance,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'phone_number': self.phone_number
        }
        
class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(30), nullable=False)  # deposit, withdraw, transfer, contact_payment
    description = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    ip_address = db.Column(db.String(45), nullable=True)
    
    @classmethod
    def create(cls, user_id, amount, transaction_type, ip_address, description=None, recipient_id=None):
        transaction = cls(
            user_id=user_id,
            recipient_id=recipient_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            ip_address=ip_address
        )
        db.session.add(transaction)
        db.session.commit()
        return transaction.id
    
    @classmethod
    def get_user_transactions(cls, user_id, limit=10):
        """Get user's transactions with optional limit"""
        return cls.query.filter(
            (cls.user_id == user_id) | (cls.recipient_id == user_id)
        ).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def count_recent_transfers(cls, user_id, minutes=5):
        """Count transfers made by user in the last X minutes"""
        time_threshold = datetime.now() - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.user_id == user_id,
            cls.transaction_type == 'transfer',
            cls.timestamp >= time_threshold
        ).count()
        
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'recipient_id': self.recipient_id,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'description': self.description,
            'timestamp': self.timestamp,
            'ip_address': self.ip_address
        }

class FraudLog(db.Model):
    __tablename__ = 'fraud_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    detected_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    transaction = db.relationship('Transaction', backref='fraud_logs', lazy=True)
    
    @classmethod
    def create(cls, transaction_id, reason):
        fraud_log = cls(
            transaction_id=transaction_id,
            reason=reason
        )
        db.session.add(fraud_log)
        db.session.commit()
        return fraud_log.id
    
    @classmethod
    def get_all_logs(cls):
        return cls.query.order_by(cls.detected_at.desc()).all()
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'reason': self.reason,
            'detected_at': self.detected_at
        }

class IPHistory(db.Model):
    __tablename__ = 'ip_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    @classmethod
    def record_ip(cls, user_id, ip_address):
        ip_entry = cls(
            user_id=user_id,
            ip_address=ip_address
        )
        db.session.add(ip_entry)
        db.session.commit()
    
    @classmethod
    def is_new_ip(cls, user_id, ip_address):
        """Check if IP is new (not seen in last 24 hours)"""
        time_threshold = datetime.now() - timedelta(hours=24)
        existing_ip = cls.query.filter(
            cls.user_id == user_id,
            cls.ip_address == ip_address,
            cls.timestamp >= time_threshold
        ).first()
        return existing_ip is None

class Payee(db.Model):
    __tablename__ = 'payees'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # domestic, international, contact
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)  # For domestic transfers
    swift_code = db.Column(db.String(20), nullable=True)  # For international transfers
    nickname = db.Column(db.String(50), nullable=True)
    is_trusted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    @classmethod
    def create(cls, user_id, name, account_type, **kwargs):
        payee = cls(
            user_id=user_id,
            name=name,
            account_type=account_type,
            email=kwargs.get('email'),
            phone=kwargs.get('phone'),
            bank_name=kwargs.get('bank_name'),
            account_number=kwargs.get('account_number'),
            ifsc_code=kwargs.get('ifsc_code'),
            swift_code=kwargs.get('swift_code'),
            nickname=kwargs.get('nickname')
        )
        db.session.add(payee)
        db.session.commit()
        return payee.id
    
    @classmethod
    def get_user_payees(cls, user_id, account_type=None):
        """Get all payees for a user, optionally filtered by account type"""
        if account_type:
            return cls.query.filter_by(user_id=user_id, account_type=account_type).order_by(cls.name).all()
        return cls.query.filter_by(user_id=user_id).order_by(cls.name).all()
    
    @classmethod
    def get_by_id(cls, payee_id, user_id=None):
        """Get payee by ID with optional user_id check for security"""
        if user_id:
            return cls.query.filter_by(id=payee_id, user_id=user_id).first()
        return cls.query.get(payee_id)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'account_type': self.account_type,
            'email': self.email,
            'phone': self.phone,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'ifsc_code': self.ifsc_code,
            'swift_code': self.swift_code,
            'nickname': self.nickname,
            'is_trusted': self.is_trusted,
            'created_at': self.created_at
        }

class ScheduledPayment(db.Model):
    __tablename__ = 'scheduled_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payee_id = db.Column(db.Integer, db.ForeignKey('payees.id'), nullable=True)
    recipient_email = db.Column(db.String(100), nullable=True)  # For non-payee transfers
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # once, daily, weekly, monthly
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, cancelled
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_executed = db.Column(db.DateTime, nullable=True)
    
    # Relationship with payee
    payee = db.relationship('Payee', backref='scheduled_payments', lazy=True)
    
    @classmethod
    def create(cls, user_id, amount, scheduled_date, frequency, **kwargs):
        scheduled_payment = cls(
            user_id=user_id,
            payee_id=kwargs.get('payee_id'),
            recipient_email=kwargs.get('recipient_email'),
            amount=amount,
            description=kwargs.get('description'),
            scheduled_date=scheduled_date,
            frequency=frequency,
            is_recurring=frequency != 'once'
        )
        db.session.add(scheduled_payment)
        db.session.commit()
        return scheduled_payment.id
    
    @classmethod
    def get_user_scheduled_payments(cls, user_id, status=None):
        """Get scheduled payments for a user, optionally filtered by status"""
        if status:
            return cls.query.filter_by(user_id=user_id, status=status).order_by(cls.scheduled_date).all()
        return cls.query.filter_by(user_id=user_id).order_by(cls.scheduled_date).all()
    
    @classmethod
    def get_pending_payments(cls, date=None):
        """Get all pending payments scheduled for the given date (or today if None)"""
        target_date = date or datetime.now().date()
        return cls.query.filter(
            cls.status == 'pending',
            cls.scheduled_date <= datetime.combine(target_date, datetime.max.time())
        ).all()
    
    def execute_payment(self):
        """Execute the scheduled payment"""
        from utils.fraud import check_fraud
        
        try:
            # Find the recipient
            recipient = None
            recipient_id = None
            
            if self.payee_id:
                # Payment to saved payee
                payee = Payee.get_by_id(self.payee_id)
                if payee and payee.account_type == 'domestic':
                    # Find user by email or account number logic would go here
                    # This is simplified for demo purposes
                    if payee.email:
                        recipient = User.get_by_email(payee.email)
                        if recipient:
                            recipient_id = recipient.id
            elif self.recipient_email:
                # Direct email transfer
                recipient = User.get_by_email(self.recipient_email)
                if recipient:
                    recipient_id = recipient.id
            
            # Get the sender
            sender = User.get_by_id(self.user_id)
            
            # Check balance
            if not sender or sender.balance < self.amount:
                self.status = 'failed'
                db.session.commit()
                return False, "Insufficient balance or sender not found"
            
            # Create the transaction
            transaction_id = Transaction.create(
                user_id=self.user_id,
                recipient_id=recipient_id,
                amount=self.amount,
                transaction_type='transfer',
                description=f"Scheduled payment: {self.description or 'No description'}",
                ip_address="0.0.0.0"  # System-generated transaction
            )
            
            # Check for fraud
            fraud_reasons = check_fraud(self.user_id, transaction_id, self.amount, "0.0.0.0")
            
            # Update balances
            sender.update_balance(-self.amount)  # Deduct from sender
            
            if recipient:
                recipient.update_balance(self.amount)  # Add to recipient if in system
            
            # Update the scheduled payment
            self.status = 'completed'
            self.last_executed = datetime.now()
            
            # If recurring, schedule the next payment
            if self.is_recurring:
                next_date = None
                if self.frequency == 'daily':
                    next_date = self.scheduled_date + timedelta(days=1)
                elif self.frequency == 'weekly':
                    next_date = self.scheduled_date + timedelta(weeks=1)
                elif self.frequency == 'monthly':
                    # Add a month logic
                    next_month = self.scheduled_date.month + 1
                    next_year = self.scheduled_date.year
                    if next_month > 12:
                        next_month = 1
                        next_year += 1
                    next_date = self.scheduled_date.replace(year=next_year, month=next_month)
                
                if next_date:
                    self.scheduled_date = next_date
                    self.status = 'pending'
                    
            db.session.commit()
            return True, "Payment executed successfully" + (" but flagged for review" if fraud_reasons else "")
            
        except Exception as e:
            self.status = 'failed'
            db.session.commit()
            return False, str(e)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'payee_id': self.payee_id,
            'recipient_email': self.recipient_email,
            'amount': self.amount,
            'description': self.description,
            'scheduled_date': self.scheduled_date,
            'frequency': self.frequency,
            'status': self.status,
            'is_recurring': self.is_recurring,
            'created_at': self.created_at,
            'last_executed': self.last_executed
        }

class InternationalTransfer(db.Model):
    __tablename__ = 'international_transfers'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    recipient_address = db.Column(db.String(200), nullable=True)
    recipient_bank = db.Column(db.String(100), nullable=False)
    recipient_account = db.Column(db.String(50), nullable=False)
    swift_code = db.Column(db.String(20), nullable=False)
    currency_code = db.Column(db.String(3), default='USD')
    exchange_rate = db.Column(db.Float, nullable=False)
    fees = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    purpose = db.Column(db.String(100), nullable=True)
    
    # Relationship with transaction
    transaction = db.relationship('Transaction', backref='international_details', lazy=True)
    
    @classmethod
    def create(cls, transaction_id, recipient_name, recipient_bank, recipient_account, swift_code, exchange_rate, **kwargs):
        int_transfer = cls(
            transaction_id=transaction_id,
            recipient_name=recipient_name,
            recipient_address=kwargs.get('recipient_address'),
            recipient_bank=recipient_bank,
            recipient_account=recipient_account,
            swift_code=swift_code,
            currency_code=kwargs.get('currency_code', 'USD'),
            exchange_rate=exchange_rate,
            fees=kwargs.get('fees', 0.0),
            purpose=kwargs.get('purpose')
        )
        db.session.add(int_transfer)
        db.session.commit()
        return int_transfer.id
    
    def update_status(self, status):
        """Update the status of the international transfer"""
        self.status = status
        db.session.commit()
        return True
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'recipient_name': self.recipient_name,
            'recipient_address': self.recipient_address,
            'recipient_bank': self.recipient_bank,
            'recipient_account': self.recipient_account,
            'swift_code': self.swift_code,
            'currency_code': self.currency_code,
            'exchange_rate': self.exchange_rate,
            'fees': self.fees,
            'status': self.status,
            'purpose': self.purpose
        }

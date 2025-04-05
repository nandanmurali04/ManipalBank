from models import Transaction, FraudLog, IPHistory
import logging

def check_fraud(user_id, transaction_id, amount, ip_address):
    """
    Check for fraudulent activity based on rules:
    1. Amount over ₹50,000
    2. More than 3 transfers in 5 minutes
    3. New IP address (not seen in last 24 hours)
    
    Returns a list of fraud reasons or empty list if no fraud detected
    """
    fraud_reasons = []
    
    # Rule 1: High amount
    if amount > 50000:
        reason = "Amount exceeds ₹50,000 threshold"
        fraud_reasons.append(reason)
        FraudLog.create(transaction_id, reason)
        logging.warning(f"Fraud detected: {reason}")
    
    # Rule 2: Frequent transfers
    recent_transfers = Transaction.count_recent_transfers(user_id, minutes=5)
    if recent_transfers > 3:
        reason = "More than 3 transfers within 5 minutes"
        fraud_reasons.append(reason)
        FraudLog.create(transaction_id, reason)
        logging.warning(f"Fraud detected: {reason}")
    
    # Rule 3: New IP address
    if IPHistory.is_new_ip(user_id, ip_address):
        reason = "Transaction from new IP address"
        fraud_reasons.append(reason)
        FraudLog.create(transaction_id, reason)
        logging.warning(f"Fraud detected: {reason}")
    
    # Send email alert (in a real system)
    if fraud_reasons:
        send_fraud_alert(user_id, transaction_id, fraud_reasons)
    
    return fraud_reasons

def send_fraud_alert(user_id, transaction_id, reasons):
    """
    Dummy function to simulate sending email alerts for fraud detection
    In a real system, this would use an email service
    """
    logging.info(f"FRAUD ALERT: User {user_id}, Transaction {transaction_id}")
    logging.info(f"Reasons: {', '.join(reasons)}")
    
    # In a production system:
    # send_email(user.email, "Fraud Alert", email_body)

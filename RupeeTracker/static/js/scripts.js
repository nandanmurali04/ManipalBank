// scripts.js - JavaScript for SecureBank Banking Management System

document.addEventListener('DOMContentLoaded', function() {
    // Auto-close flash messages after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Format currency inputs
    const currencyInputs = document.querySelectorAll('input[type="number"]');
    currencyInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value) {
                const value = parseFloat(this.value);
                if (!isNaN(value)) {
                    // Keep the original value but display formatted in a span
                    const formattedValue = new Intl.NumberFormat('en-IN', {
                        style: 'currency',
                        currency: 'INR',
                        maximumFractionDigits: 2
                    }).format(value);
                    
                    // Check if there's a helper span after this input
                    let helperSpan = this.nextElementSibling;
                    if (!helperSpan || !helperSpan.classList.contains('formatted-value')) {
                        helperSpan = document.createElement('span');
                        helperSpan.classList.add('formatted-value', 'text-muted', 'small', 'ms-2');
                        this.parentNode.appendChild(helperSpan);
                    }
                    helperSpan.textContent = formattedValue;
                }
            }
        });
    });
    
    // Add smooth transition effects
    const cards = document.querySelectorAll('.card');
    cards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'transform 0.3s ease';
        });
    });
    
    // Form validation for transfer
    const transferForm = document.querySelector('form[action*="transfer"]');
    if (transferForm) {
        transferForm.addEventListener('submit', function(event) {
            const emailInput = document.getElementById('recipient_email');
            const amountInput = document.getElementById('amount');
            
            // Simple email validation
            const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (emailInput && !emailPattern.test(emailInput.value)) {
                event.preventDefault();
                alert('Please enter a valid email address');
                emailInput.focus();
                return false;
            }
            
            // Amount validation
            if (amountInput && (isNaN(amountInput.value) || parseFloat(amountInput.value) <= 0)) {
                event.preventDefault();
                alert('Please enter a valid amount');
                amountInput.focus();
                return false;
            }
            
            return true;
        });
    }
});

// Add confirmation for withdraw and transfer actions
function confirmAction(message) {
    return confirm(message || 'Are you sure you want to proceed with this action?');
}

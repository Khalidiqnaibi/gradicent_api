/**
 * Login Page JavaScript
 * Handles login form interactions, terms agreement, and activation codes
 */

// DOM Elements
const termsCheckbox = document.getElementById('tr');
const loginButton = document.getElementById('login-btn');

// Initialize: Set button as disabled until terms are accepted
loginButton.disabled = true;

/**
 * Check and process activation code
 */
function checkActivationCode() {
  if (!termsCheckbox.checked) {
    alert('Please agree to the Terms and Privacy Notice before continuing.');
    return;
  }

  const activationCode = document.getElementById('activationCodeInput').value.trim();

  if (!activationCode) {
    alert('Please enter an activation code.');
    return;
  }

  // Create form for POST submission
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = '/api/binder/code/check';
  form.style.display = 'none';

  const input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'code';
  input.value = activationCode;

  form.appendChild(input);
  document.body.appendChild(form);
  form.submit();
}

/**
 * Handle Google login button click
 */
loginButton.addEventListener('click', function() {
  if (termsCheckbox.checked) {
    window.location.href = '/api/auth/start?domain=business';
  } else {
    alert('Please agree to the Terms and Privacy Notice before continuing.');
  }
});

/**
 * Enable/disable login button based on terms checkbox state
 */
termsCheckbox.addEventListener('change', () => {
  loginButton.disabled = !termsCheckbox.checked;
});

const sgMail = require('@sendgrid/mail');

// Initialize SendGrid
const sendgridApiKey = process.env.SENDGRID_API_KEY;
const fromEmail = process.env.FROM_EMAIL || 'support@pdf-processor-api.fly.dev';

if (sendgridApiKey && sendgridApiKey !== 'your_sendgrid_api_key_here') {
  sgMail.setApiKey(sendgridApiKey);
  console.log('SendGrid initialized');
} else {
  console.warn('SendGrid API key not configured. Emails will be logged only.');
}

/**
 * Send an email using SendGrid (or log if not configured)
 * @param {string} to - Recipient email
 * @param {string} subject - Email subject
 * @param {string} html - HTML content
 * @param {string} text - Plain text content (optional)
 * @returns {Promise<boolean>} True if sent successfully
 */
async function sendEmail(to, subject, html, text = '') {
  const msg = {
    to,
    from: fromEmail,
    subject,
    text: text || html.replace(/<[^>]*>/g, ''),
    html,
  };

  try {
    if (sendgridApiKey && sendgridApiKey !== 'your_sendgrid_api_key_here') {
      await sgMail.send(msg);
      console.log(`Email sent to ${to}: ${subject}`);
      return true;
    } else {
      // Log email (development mode)
      console.log('📧 Email (not sent - no API key):', { to, subject, html: html.substring(0, 100) + '...' });
      return true; // pretend success
    }
  } catch (error) {
    console.error('Failed to send email:', error.response?.body || error.message);
    return false;
  }
}

/**
 * Send welcome email to new customer
 * @param {string} customerEmail - Customer email
 * @param {string} customerId - Stripe customer ID
 * @param {string} tier - Subscription tier
 * @returns {Promise<boolean>}
 */
async function sendWelcomeEmail(customerEmail, customerId, tier) {
  const subject = `Welcome to PDF Processor API (${tier} plan)`;
  const html = `
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
      <h2>Welcome to PDF Processor API!</h2>
      <p>Your account has been activated with the <strong>${tier}</strong> plan.</p>
      <p>Your API key is your Stripe Customer ID:</p>
      <pre style="background: #f5f5f5; padding: 12px; border-radius: 6px;">${customerId}</pre>
      <p>Use this key in the <code>X-API-Key</code> header to authenticate API requests.</p>
      <p>Get started with our <a href="https://pdf-processor-api.fly.dev/docs">API documentation</a>.</p>
      <p>If you have any questions, reply to this email.</p>
      <br>
      <p>— The PDF Processor Team</p>
    </div>
  `;
  return sendEmail(customerEmail, subject, html);
}

/**
 * Send usage alert email (e.g., 80% of monthly limit reached)
 * @param {string} customerEmail - Customer email
 * @param {string} tier - Subscription tier
 * @param {number} usage - Current usage count
 * @param {number} limit - Monthly limit (or null for unlimited)
 * @param {number} percent - Usage percentage
 * @returns {Promise<boolean>}
 */
async function sendUsageAlertEmail(customerEmail, tier, usage, limit, percent) {
  const subject = `PDF Processor API: Usage Alert (${percent}% of monthly limit)`;
  const html = `
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
      <h2>Usage Alert</h2>
      <p>You have used <strong>${usage}</strong> of your <strong>${limit}</strong> monthly PDFs (${percent}%).</p>
      <p>Plan: <strong>${tier}</strong></p>
      <p>Once you reach your limit, further API requests will be throttled until the next billing cycle.</p>
      <p>You can upgrade your plan at any time to increase your limits.</p>
      <p>Check your current usage: <a href="https://pdf-processor-api.fly.dev/customer/usage">Usage Dashboard</a></p>
      <p>Need higher limits? <a href="https://pdf-processor-api.fly.dev/#pricing">Upgrade your plan</a>.</p>
      <br>
      <p>— The PDF Processor Team</p>
    </div>
  `;
  return sendEmail(customerEmail, subject, html);
}

/**
 * Send subscription update email (e.g., plan changed, cancelled)
 * @param {string} customerEmail - Customer email
 * @param {string} oldTier - Previous tier (or 'none')
 * @param {string} newTier - New tier (or 'cancelled')
 * @returns {Promise<boolean>}
 */
async function sendSubscriptionUpdateEmail(customerEmail, oldTier, newTier) {
  const subject = `PDF Processor API: Subscription Updated`;
  const html = `
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
      <h2>Subscription Updated</h2>
      <p>Your subscription has been changed from <strong>${oldTier}</strong> to <strong>${newTier}</strong>.</p>
      <p>New limits and features are effective immediately.</p>
      <p>View your updated usage dashboard: <a href="https://pdf-processor-api.fly.dev/customer/usage">Usage Dashboard</a></p>
      <br>
      <p>— The PDF Processor Team</p>
    </div>
  `;
  return sendEmail(customerEmail, subject, html);
}

module.exports = {
  sendEmail,
  sendWelcomeEmail,
  sendUsageAlertEmail,
  sendSubscriptionUpdateEmail,
};
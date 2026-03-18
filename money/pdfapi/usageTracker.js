// Usage tracking with SQLite database
const database = require('./database');

class UsageTracker {
  constructor() {
    // No need to reset on startup; monthly reset should be scheduled separately
    console.log('UsageTracker initialized with SQLite database');
  }

  // Record usage for a customer
  recordUsage(customerId, tier) {
    const newCount = database.recordUsage(customerId, tier);
    
    // Log usage
    console.log(`Usage recorded: customer ${customerId} (${tier}), count: ${newCount}`);
    
    // Check if over limit (for logging only)
    const limit = this.getMonthlyLimit(tier);
    if (limit && newCount > limit) {
      console.warn(`Customer ${customerId} (${tier}) exceeded monthly limit of ${limit}`);
    }
    
    return newCount;
  }

  // Get monthly limit based on tier
  getMonthlyLimit(tier) {
    const limits = {
      free: 100,
      pro: 10000,
      enterprise: null, // unlimited
    };
    return limits[tier] || null;
  }

  // Check if customer has reached monthly limit
  hasReachedLimit(customerId, tier) {
    const record = this.getUsage(customerId);
    const limit = this.getMonthlyLimit(tier);
    if (limit === null) return false; // unlimited
    return record.count >= limit;
  }

  // Get usage for customer
  getUsage(customerId) {
    const dbRecord = database.getUsage(customerId);
    if (dbRecord) {
      return dbRecord;
    }
    // Return default record
    return { count: 0, tier: 'free', lastReset: new Date(), alertSentAtPercent: null };
  }

  // Set alert sent percent for a customer
  setAlertSentPercent(customerId, percent) {
    database.setAlertSentPercent(customerId, percent);
  }

  // Reset monthly usage (call this on a schedule)
  monthlyReset() {
    console.log('Manual monthly usage reset triggered');
    database.monthlyReset();
  }

  // Get all usage (for admin)
  getAllUsage() {
    return database.getAllUsage();
  }
}

// Export singleton instance
module.exports = new UsageTracker();
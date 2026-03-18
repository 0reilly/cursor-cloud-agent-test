const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

// Data directory configurable via env, default to ./data
const dataDir = process.env.DATA_DIR || path.join(__dirname, 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

// Open database
const db = new Database(path.join(dataDir, 'usage.db'));

// Enable WAL mode for better concurrency
db.pragma('journal_mode = WAL');

// Create tables if they don't exist
function initDatabase() {
  // Usage table: tracks monthly usage per customer
  db.exec(`
    CREATE TABLE IF NOT EXISTS usage (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id TEXT NOT NULL,
      tier TEXT NOT NULL DEFAULT 'free',
      count INTEGER NOT NULL DEFAULT 0,
      alert_sent_at_percent INTEGER,
      last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(customer_id)
    )
  `);

  // Monthly reset log (optional, for auditing)
  db.exec(`
    CREATE TABLE IF NOT EXISTS monthly_resets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      reset_month TEXT NOT NULL, -- YYYY-MM
      reset_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
  `);

  // Create indexes
  db.exec('CREATE INDEX IF NOT EXISTS idx_usage_customer_id ON usage(customer_id)');
  db.exec('CREATE INDEX IF NOT EXISTS idx_usage_tier ON usage(tier)');
  db.exec('CREATE INDEX IF NOT EXISTS idx_usage_last_reset ON usage(last_reset)');
}

// Initialize now
initDatabase();

// Prepare statements
const stmt = {
  getUsage: db.prepare('SELECT * FROM usage WHERE customer_id = ?'),
  insertUsage: db.prepare(`
    INSERT INTO usage (customer_id, tier, count, alert_sent_at_percent, last_reset)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(customer_id) DO UPDATE SET
      tier = excluded.tier,
      count = usage.count + excluded.count,
      alert_sent_at_percent = excluded.alert_sent_at_percent,
      updated_at = CURRENT_TIMESTAMP
  `),
  updateUsage: db.prepare(`
    UPDATE usage SET
      count = ?,
      alert_sent_at_percent = ?,
      updated_at = CURRENT_TIMESTAMP
    WHERE customer_id = ?
  `),
  getAllUsage: db.prepare('SELECT * FROM usage ORDER BY tier, count DESC'),
  resetMonthlyUsage: db.prepare('UPDATE usage SET count = 0, alert_sent_at_percent = NULL, last_reset = CURRENT_TIMESTAMP'),
  logMonthlyReset: db.prepare('INSERT INTO monthly_resets (reset_month) VALUES (?)'),
  deleteUsage: db.prepare('DELETE FROM usage WHERE customer_id = ?'),
};

// Database interface
module.exports = {
  /**
   * Get usage record for a customer
   * @param {string} customerId - Stripe customer ID
   * @returns {object | null} Usage record or null if not found
   */
  getUsage(customerId) {
    const row = stmt.getUsage.get(customerId);
    if (!row) return null;
    return {
      count: row.count,
      tier: row.tier,
      lastReset: row.last_reset,
      alertSentAtPercent: row.alert_sent_at_percent,
    };
  },

  /**
   * Increment usage count for a customer
   * @param {string} customerId - Stripe customer ID
   * @param {string} tier - Subscription tier
   * @returns {number} New count
   */
  recordUsage(customerId, tier) {
    // Try to update existing record
    const existing = stmt.getUsage.get(customerId);
    if (existing) {
      const newCount = existing.count + 1;
      stmt.updateUsage.run(newCount, existing.alert_sent_at_percent, customerId);
      return newCount;
    } else {
      // Insert new record with count 1
      stmt.insertUsage.run(customerId, tier, 1, null, new Date().toISOString());
      return 1;
    }
  },

  /**
   * Set alert sent percent for a customer
   * @param {string} customerId - Stripe customer ID
   * @param {number} percent - Percent at which alert was sent
   */
  setAlertSentPercent(customerId, percent) {
    const existing = stmt.getUsage.get(customerId);
    if (existing) {
      stmt.updateUsage.run(existing.count, percent, customerId);
    } else {
      // Should not happen, but create record with count 0
      stmt.insertUsage.run(customerId, 'free', 0, percent, new Date().toISOString());
    }
  },

  /**
   * Get all usage records
   * @returns {Array} Array of [customerId, data] tuples
   */
  getAllUsage() {
    const rows = stmt.getAllUsage.all();
    return rows.map(row => [
      row.customer_id,
      {
        count: row.count,
        tier: row.tier,
        lastReset: row.last_reset,
        alertSentAtPercent: row.alert_sent_at_percent,
      }
    ]);
  },

  /**
   * Reset all monthly usage counters (call at start of each month)
   */
  monthlyReset() {
    const now = new Date();
    const month = now.toISOString().slice(0, 7); // YYYY-MM
    stmt.resetMonthlyUsage.run();
    stmt.logMonthlyReset.run(month);
    console.log(`Monthly usage reset for ${month}`);
  },

  /**
   * Delete usage record (for testing or cleanup)
   */
  deleteUsage(customerId) {
    stmt.deleteUsage.run(customerId);
  },

  // Close database connection (call on shutdown)
  close() {
    db.close();
  },
};
const usageTracker = require('./usageTracker');
const database = require('./database');

async function test() {
  console.log('Testing usageTracker with database...');
  const customerId = 'test_customer_' + Date.now();
  
  // Record usage
  const count1 = usageTracker.recordUsage(customerId, 'free');
  console.log('Recorded usage count:', count1);
  
  // Get usage
  const record = usageTracker.getUsage(customerId);
  console.log('Record:', record);
  
  // Check limit
  const limit = usageTracker.getMonthlyLimit('free');
  console.log('Limit:', limit);
  const reached = usageTracker.hasReachedLimit(customerId, 'free');
  console.log('Has reached limit?', reached);
  
  // Set alert sent percent
  usageTracker.setAlertSentPercent(customerId, 85);
  const updated = usageTracker.getUsage(customerId);
  console.log('After alert percent:', updated.alertSentAtPercent);
  
  // Get all usage
  const all = usageTracker.getAllUsage();
  console.log('Total records:', all.length);
  
  // Clean up
  database.deleteUsage(customerId);
  console.log('Test completed.');
  database.close();
}

test().catch(err => {
  console.error(err);
  process.exit(1);
});
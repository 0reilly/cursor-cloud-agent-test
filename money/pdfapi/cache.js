// Simple in-memory cache with TTL
class Cache {
  constructor(ttlSeconds = 300) { // 5 minutes default
    this.cache = new Map();
    this.ttl = ttlSeconds * 1000;
  }

  set(key, value, ttl = this.ttl) {
    const expires = Date.now() + ttl;
    this.cache.set(key, { value, expires });
    return true;
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() > item.expires) {
      this.cache.delete(key);
      return null;
    }
    
    return item.value;
  }

  delete(key) {
    return this.cache.delete(key);
  }

  clear() {
    this.cache.clear();
  }

  size() {
    return this.cache.size;
  }
}

// Export singleton instance
module.exports = new Cache();